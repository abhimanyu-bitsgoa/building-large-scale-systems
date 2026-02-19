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

## Student Mini-Project: CloudCart KV Store

Design and configure a distributed KV store for a fictional e-commerce company!

### Step 1: Read the scenario brief

```bash
# Understand the business requirements
cat labs/distributed-kvstore/scenario_brief.md
```

Or open [scenario_brief.md](scenario_brief.md) — it describes CloudCart's traffic patterns, reliability needs, and budget constraints.

### Step 2: Experiment with the system

After the instructor demos, try things yourself:

```bash
# Check cluster status
curl http://localhost:7000/status

# Write and read data
curl -X POST http://localhost:8000/write -H "Content-Type: application/json" -d '{"key": "test", "value": "hello"}'
curl http://localhost:8000/read/test

# Kill a node and see what happens
curl -X POST http://localhost:7000/kill/follower-1

# Spawn a replacement
curl -X POST http://localhost:7000/spawn
```

### Step 3: Design your configuration

Edit `student_config.json` with your choices:

```bash
# Edit the config file
nano labs/distributed-kvstore/student_config.json
```

| Parameter             | What it controls               | Key question                          |
| --------------------- | ------------------------------ | ------------------------------------- |
| `followers`         | Number of follower nodes       | How many failures can you survive?    |
| `write_quorum` (W)  | Followers that must ack writes | Higher = more durable, slower         |
| `read_quorum` (R)   | Followers queried for reads    | Higher = more consistent, slower      |
| `auto_spawn`        | Auto-replace dead nodes        | Faster recovery vs complexity         |
| `rate_limit_max`    | Max requests per window        | Protection vs rejecting valid traffic |
| `rate_limit_window` | Window size in seconds         | Shorter = faster rate limit recovery  |

**Don't forget** to fill in all 4 justification fields explaining *why* you made each choice!

### Step 4: Run the assessment

```bash
python labs/distributed-kvstore/assessment.py --config labs/distributed-kvstore/student_config.json
```

The assessment tests 5 scenarios (100 points total):

| Scenario         | Points | What it tests                          |
| ---------------- | ------ | -------------------------------------- |
| Basic Operations | 15     | Reads and writes work                  |
| Fault Tolerance  | 25     | Survives node failures                 |
| Consistency      | 25     | No stale reads (W+R > N)               |
| Rate Limiting    | 15     | Gateway rejects burst traffic          |
| Recovery         | 20     | System recovers after node replacement |

### Step 5: Iterate!

Adjust your config and re-run until you're happy with your score.
