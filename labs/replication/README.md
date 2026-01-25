# Replication Lab

Learn about single-leader replication with configurable quorum semantics.

## Overview

This lab demonstrates:
- **Single-leader replication**: All writes go through the leader
- **Write quorum (W)**: Number of acknowledgments needed before write succeeds
- **Read quorum (R)**: Number of nodes to read from
- **Replication lag**: Visible delay as data propagates to followers
- **Fault tolerance**: What happens when nodes fail

## Files

| File | Description |
|------|-------------|
| `coordinator.py` | Cluster manager with HTTP API and TUI dashboard |
| `node.py` | Leader or follower node |
| `client.py` | Interactive client for read/write operations |

---

## Demo 1: Starting the Cluster

### Step 1: Start the coordinator with 2 followers

```bash
python labs/replication/coordinator.py --followers 2 --write-quorum 2 --read-quorum 1
```

This starts:
- **1 leader** on port 6001
- **2 followers** on ports 6002, 6003
- **Coordinator API** on port 6000

The TUI dashboard shows cluster status in real-time.

---

## Demo 2: Write with Replication

### Step 1: Open a new terminal and write data

```bash
# Using curl
curl -X POST http://localhost:6000/write \
  -H "Content-Type: application/json" \
  -d '{"key": "name", "value": "distributed-systems"}'

# Or use the client
python labs/replication/client.py
# Then type: write name distributed-systems
```

### Step 2: Observe the dashboard

Watch the coordinator terminal. You'll see:
1. Write arrives at leader
2. Leader stores locally
3. Replication delay (configurable, default 1s)
4. Followers receive data
5. Ack returned to coordinator

---

## Demo 3: Read from Cluster

```bash
# Using curl
curl http://localhost:6000/read/name

# Or use the client (interactive mode)
python labs/replication/client.py
# Then type: read name
```

The response shows:
- Which node served the read
- The data version
- How many quorum responses received

---

## Demo 4: Killing a Node

### Step 1: Kill a follower

```bash
curl -X POST http://localhost:6000/kill/follower-1
```

### Step 2: Observe the dashboard

The dashboard updates to show:
- `follower-1` marked as 🔴 dead
- Quorum status may change

### Step 3: Try writing again

```bash
curl -X POST http://localhost:6000/write \
  -H "Content-Type: application/json" \
  -d '{"key": "test", "value": "123"}'
```

With W=2 and only 2 nodes remaining (leader + 1 follower), writes should still work.

---

## Demo 5: Destroying Write Quorum

### Step 1: Kill another follower

```bash
curl -X POST http://localhost:6000/kill/follower-2
```

### Step 2: Try to write

```bash
curl -X POST http://localhost:6000/write \
  -H "Content-Type: application/json" \
  -d '{"key": "test", "value": "456"}'
```

Expected: **503 Error** - Write quorum not available

The system refuses writes when it can't guarantee durability!

---

## Demo 6: Spawning a Replacement

### Step 1: Add a new follower

```bash
curl -X POST http://localhost:6000/spawn
```

### Step 2: Check status

```bash
curl http://localhost:6000/status
```

The new follower appears and writes are enabled again!

---

## Understanding Quorum

For a cluster with N nodes:
- **W (Write Quorum)**: Minimum acks needed for successful write
- **R (Read Quorum)**: Minimum nodes to read from
- **Rule**: W + R > N guarantees overlap (no stale reads)

### Examples:

| N | W | R | Behavior |
|---|---|---|----------|
| 3 | 2 | 2 | Strong consistency (W+R=4 > 3) |
| 3 | 2 | 1 | Eventual consistency (W+R=3 = 3) |
| 3 | 1 | 1 | Fast but risky (W+R=2 < 3) |

---

## API Reference

### Coordinator Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/write` | Write data with quorum |
| GET | `/read/{key}` | Read data with quorum |
| GET | `/status` | Cluster status |
| POST | `/spawn` | Add new follower |
| POST | `/kill/{node_id}` | Kill a follower |

### Example Requests

```bash
# Write
curl -X POST http://localhost:6000/write \
  -H "Content-Type: application/json" \
  -d '{"key": "foo", "value": "bar"}'

# Read
curl http://localhost:6000/read/foo

# Status
curl http://localhost:6000/status

# Spawn follower
curl -X POST http://localhost:6000/spawn

# Kill follower
curl -X POST http://localhost:6000/kill/follower-1
```

---

## Configuration Options

```bash
python labs/replication/coordinator.py \
  --followers 3 \           # Number of followers
  --write-quorum 2 \        # W: Acks required for write
  --read-quorum 2 \         # R: Nodes to read from
  --replication-delay 2.0   # Delay in seconds (for visualization)
```

---

## Key Takeaways

1. **Single leader simplifies writes**: No conflict resolution needed
2. **Quorum ensures durability**: W acks means data survives W-1 failures
3. **Trade-offs exist**: Higher W = more durable but slower and less available
4. **Replication lag is real**: Followers may be behind leader
5. **System rejects writes when quorum unavailable**: Prevents data loss

---

## Troubleshooting

**Coordinator not starting?**
- Check if ports 6000-6003 are available
- Make sure no other instances are running

**Writes failing?**
- Check quorum status with `/status`
- Ensure enough nodes are alive for write quorum

**Replication seems stuck?**
- Check node terminals for errors
- Verify leader URL is correct for followers
