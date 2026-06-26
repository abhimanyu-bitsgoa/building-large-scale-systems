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
| `load_balancer.py`  | Strategies (imported by the gateway, unused — single coordinator) |
| `rate_limiter.py`   | Fixed-window limiter (runs at the gateway edge) |

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
curl -X POST http://localhost:7000/kill/follower-3
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

## This is a demo stage

Stage 10 has **no incident and no grader** — it's the synthesis of everything built in stages 00–09.
Drive it by hand with `make lab STAGE=10`: trace one request through the whole stack
(gateway → coordinator → leader → followers), shed load at the edge, and kill a follower to watch the
cluster self-heal while reads stay fresh.
