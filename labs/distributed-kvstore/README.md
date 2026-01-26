# Distributed KV Store Lab

A fault-tolerant distributed key-value store combining concepts from Lab 1 (Scalability) and Lab 2 (Replication).

## Overview

This lab demonstrates:

- **Gateway with rate limiting** (imported from Lab 1!)
- **Single-leader replication with quorum** (from Lab 2)
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

| File               | Description                                         |
| ------------------ | --------------------------------------------------- |
| `gateway.py`     | Entry point with rate limiting (imports from Lab 1) |
| `coordinator.py` | Cluster manager with quorum and catchup             |
| `registry.py`    | Service discovery with heartbeats                   |
| `node.py`        | Leader or follower node                             |
| `catchup.py`     | Data synchronization for new followers              |
| `client.py`      | Interactive client                                  |

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

### Using curl

```bash
# Write
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '{"key": "hello", "value": "world"}'

# Read
curl http://localhost:8000/read/hello

# Cluster status
curl http://localhost:8000/cluster-status
```

---

## Demo 3: Rate Limiting in Action

### Flood the gateway

```bash
# Quick loop to trigger rate limiting
for i in {1..20}; do
  curl -s http://localhost:8000/read/test | head -c 50
  echo
done
```

After 10 requests (the default limit), you'll see:

```json
{"error": "Too Many Requests", "retry_after": 60}
```

### Check gateway stats

```bash
curl http://localhost:8000/stats
```

Shows rate limiter statistics - imported directly from Lab 1!

---

## Demo 4: Node Failure and Recovery

### Step 1: Kill a follower

```bash
curl -X POST http://localhost:7000/kill/follower-1
```

### Step 2: Observe the coordinator dashboard

The node shows as 🔴 dead.

### Step 3: Check if writes still work

```bash
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '{"key": "test", "value": "123"}'
```

With W=2 and 2 remaining nodes (leader + 1 follower), writes succeed.

### Step 4: Kill another follower to break quorum

```bash
curl -X POST http://localhost:7000/kill/follower-2
```

### Step 5: Try to write

```bash
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '{"key": "test", "value": "456"}'
```

**Result**: 503 error - Write quorum not available!

---

## Demo 5: Automatic Catchup

### Step 1: Write some data first

```bash
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '{"key": "secret", "value": "treasure"}'
```

### Step 2: Spawn a new follower

```bash
curl -X POST http://localhost:7000/spawn
```

### Step 3: Check the registry

```bash
curl http://localhost:9000/nodes
```

The new follower appears!

### Step 4: Verify catchup happened

The registry automatically triggered catchup. The new follower has all the data from the leader.

---

## Demo 6: The Easter Egg 🎓

After completing the workshop:

```bash
curl http://localhost:8000/graduate
```

Or in the client:

```bash
python labs/distributed-kvstore/client.py
>>> graduate
```

🎓 **Congratulations, you're now a distributed systems engineer!**

---

## Code Reuse from Lab 1

The gateway imports directly from Lab 1 (Scalability):

```python
# In gateway.py
from scalability.load_balancer import LoadBalancer, node_stats
from scalability.rate_limiter import RateLimiter, FixedWindowStrategy
```

This proves that the code you wrote in Lab 1 is production-ready!

---

## API Reference

### Gateway (port 8000)

| Method | Endpoint            | Description                  |
| ------ | ------------------- | ---------------------------- |
| POST   | `/write`          | Write data                   |
| GET    | `/read/{key}`     | Read data                    |
| GET    | `/cluster-status` | Cluster status               |
| GET    | `/stats`          | Gateway stats (rate limiter) |
| GET    | `/graduate`       | 🎓 Easter egg                |

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

## Key Takeaways

1. **Code reuse matters**: Gateway imports rate limiting from Lab 1
2. **Layered architecture**: Gateway → Coordinator → Nodes
3. **Service discovery**: Registry tracks all nodes via heartbeats
4. **Automatic recovery**: New followers catch up from leader
5. **Defense in depth**: Rate limiting at gateway protects the cluster

---

## Troubleshooting

**Gateway can't reach coordinator?**

- Ensure coordinator is running on port 7000
- Check the --coordinator flag

**Nodes not appearing in registry?**

- Check registry is running on port 9000
- Verify nodes are sending heartbeats

**Catchup not working?**

- Check leader has `/snapshot` endpoint
- Verify network connectivity between nodes

**Rate limiting too aggressive?**

- Adjust `--rate-limit-max` and `--rate-limit-window`
