# Distributed KV Store Lab

A fault-tolerant distributed key-value store combining concepts learnt in Scalability & Replication module.

## Overview

This lab demonstrates:

- **Gateway with rate limiting**
- **Single-leader replication with quorum**
- **Service discovery with heartbeats**
- **Automatic catchup for new followers**
- **Fault tolerance and recovery**

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│   Gateway   │────▶│  Registry   │
│ (rate limit)│     │ (heartbeat) │
└──────┬──────┘     └──────┬──────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│ Coordinator │◀───▶│    Nodes    │
│  (quorum)   │     │ (leader/    │
└─────────────┘     │  followers) │
                    └─────────────┘
```

## Files

| File                  | Description                             |
| --------------------- | --------------------------------------- |
| `gateway.py`        | Entry point with rate limiting          |
| `coordinator.py`    | Cluster manager with quorum and catchup |
| `registry.py`       | Service discovery with heartbeats       |
| `node.py`           | Leader or follower node                 |
| `catchup.py`        | Data synchronization for new followers  |
| `client.py`         | Interactive client                      |
| `assessment.py`     | Automated assessment script             |
| `scenario_brief.md` | Student mini-project business brief     |

---

## Augmentations from Replication Lab

This lab builds directly upon the Replication Lab, enhancing components for a distributed environment:

### Coordinator (`coordinator.py`)

- **Event-Based Logging**: Uses `EventLogger` for structured, timestamped console output (matching Replication Lab style).
- **Service Discovery Integration**: Integrates with `registry.py` to auto-discover and manage nodes dynamically.
- **Cluster State Management**: Tracks `sync_followers` and `async_followers` based on health and quorum settings.
- **Rich Write Logic**: Orchestrates writes by instructing the leader on which followers are sync vs async.

### Client (`client.py`)

- **Prettified Error Handling**: Enhanced error printing for easier debugging of distributed system failures (e.g. 503 Quorum failures).

### Node (`node.py`)

- **Parallel Replication**: Uses `ThreadPoolExecutor` for parallel sync replication (vs sequential).
- **Service Discovery**: Adds heartbeats, registry integration, and graceful shutdown.
- **Catchup Endpoint**: Supports full state transfer for new followers.

---

## Demo 1: Starting the Full System

### Step 1: Start the registry

```bash
# Terminal 1 - Basic
python labs/distributed-kvstore/registry.py --port 9000

# OR with auto-spawn (automatically respawns dead followers)
python labs/distributed-kvstore/registry.py --port 9000 --auto-spawn --spawn-delay 5
```

### Step 2: Start the coordinator (spawns leader + followers)

```bash
# Terminal 2
python labs/distributed-kvstore/coordinator.py --followers 3 --write-quorum 2 --read-quorum 2 --registry http://localhost:9000
```

### Step 3: Start the gateway with rate limiting

```bash
# Terminal 3
python labs/distributed-kvstore/gateway.py --port 8000 --coordinator http://localhost:7000 --rate-limit --rate-limit-max 10 --rate-limit-window 60
```

### Step 4: Use the client

```bash
# Terminal 4
python labs/distributed-kvstore/client.py --gateway http://localhost:8000
```

---

## Demo 2: Write and Read Operations

### Using the interactive client

```bash
python labs/distributed-kvstore/client.py
>>> write name distributed-systems
>>> read name
>>> status
```

---

## Demo 3: Node Failure and Recovery

### Step 1: Kill a follower

```bash
curl -X POST http://localhost:7000/kill/follower-1
```

### Step 2: Observe the coordinator dashboard

The node shows as 🔴 dead.

### Step 3: Check if writes still work

```bash
>>> write name distributed-systems
>>> read name
```

With W=2 and 2 remaining nodes (leader + 1 follower), writes succeed.

### Step 4: Kill another follower to break quorum

```bash
curl -X POST http://localhost:7000/kill/follower-2
```

### Step 5: Try to write

```bash
>>> write name distributed-systems
>>> read name
```

**Result**: error - Write quorum not available!

---

## Demo 4: Automatic Catchup

### Step 1: Kill a follower node

```bash
curl -X POST http://localhost:7000/kill/follower-4
```

### Step 1: Write some data first

```bash
>>> write name distributed-systems
>>> read name
```

### Step 2: Spawn a new follower

```bash
curl -X POST http://localhost:7000/spawn
```

### Step 3: Verify catchup happened

```bash
>>> read name
```

Observe that the follower-3 has gotten the value.

---

## API Reference

### Gateway (port 8000)

| Method | Endpoint            | Description                  |
| ------ | ------------------- | ---------------------------- |
| POST   | `/write`          | Write data                   |
| GET    | `/read/{key}`     | Read data                    |
| GET    | `/cluster-status` | Cluster status               |
| GET    | `/stats`          | Gateway stats (rate limiter) |

### Coordinator (port 7000)

| Method | Endpoint            | Description        |
| ------ | ------------------- | ------------------ |
| POST   | `/spawn`          | Spawn new follower |
| POST   | `/kill/{node_id}` | Stop a follower    |
| GET    | `/status`         | Detailed status    |

### Registry (port 9000)

| Method | Endpoint   | Description          |
| ------ | ---------- | -------------------- |
| GET    | `/nodes` | All registered nodes |
| GET    | `/alive` | Alive nodes only     |

**Registry CLI Options:**

```bash
--auto-spawn        # Enable automatic respawning of dead followers
--spawn-delay N     # Seconds to wait before respawning (default: 5)
```

---

## Student Mini-Project: CloudCart Incident Investigation

Investigate production incidents in a misconfigured distributed KV store and fix the system!

### Step 1: Read the incident brief

```bash
# Review the 5 open incident tickets
cat labs/distributed-kvstore/scenario_brief.md
```

Or open [scenario_brief.md](scenario_brief.md) — you'll play an SRE who inherited a broken system with 5 production incidents to investigate and fix.

### Step 2: Reproduce the incidents

After the instructor demos, try reproducing each incident:

```bash
# INC-1: Test rate limiting — does burst traffic get blocked?
for i in $(seq 1 30); do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/read/test; done

# INC-4: Kill a single node — do writes still work?
curl -X POST http://localhost:7000/kill/follower-1
curl -X POST http://localhost:8000/write -H "Content-Type: application/json" -d '{"key":"test","value":"hello"}'

# Check cluster status
curl http://localhost:7000/status
```

### Step 3: Diagnose and fix the configuration

The current `student_config.json` contains the bugs. Investigate each incident, find the root cause, and fix it:

```bash
# Edit the config file
nano labs/distributed-kvstore/student_config.json
```

| Parameter             | Incident | What to investigate                          |
| --------------------- | -------- | -------------------------------------------- |
| `rate_limit_window` | INC-1    | Why does the rate limiter never block bursts? |
| `auto_spawn_delay`  | INC-2    | Why do ghost nodes appear after network blips?|
| `read_quorum` (R)   | INC-3    | Why are customers seeing stale cart data?     |
| `write_quorum` (W)  | INC-4    | Why does one node failure kill all writes?    |
| `followers`          | INC-5    | Why is the cluster over budget?               |

**Don't forget** to fill in all 4 justification fields explaining *what was wrong* and *why your fix resolves it*!

### Step 4: Run the assessment

```bash
python labs/distributed-kvstore/assessment.py --config labs/distributed-kvstore/student_config.json
```

The assessment tests 5 scenarios (100 points total):

| Scenario                                 | Points | Validates fix for |
| ---------------------------------------- | ------ | ----------------- |
| INC-0: Basic Operations                  | 15     | System works      |
| INC-1: Gateway Flood (Rate Limiting)     | 15     | INC-1             |
| INC-3: Stale Cart Data (Consistency)     | 25     | INC-3             |
| INC-4: Write Outage (Fault Tolerance)    | 25     | INC-4             |
| INC-2/5: Recovery & Right-Sizing         | 20     | INC-2 + INC-5     |

### Step 5: Iterate!

Adjust your config and re-run until all incidents are resolved.
