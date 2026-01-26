# Replication Lab

Learn about single-leader replication with configurable quorum semantics using event-based logging.

## Overview

This lab demonstrates:

- **Single-leader replication**: All writes go through the leader
- **Write quorum (W)**: Number of **follower** acknowledgments needed before write succeeds
- **Read quorum (R)**: Number of **followers** to read from
- **Sync vs Async replication**: W followers get fast sync replication, others get slow async
- **Replication lag**: Visible delay as data propagates (5s for async nodes)
- **Fault tolerance**: What happens when nodes fail

## Key Concept: Quorum Formula

For N follower nodes:

- **W** = followers that must ack synchronously (leader always writes first)
- **R** = followers to read from for quorum
- **Rule: W + R > N** guarantees no stale reads (sync and read sets overlap)

### How It Works

1. **Sync followers** = First W smallest port followers (0.5s delay)
2. **Async followers** = Remaining followers (5s delay - visible lag!)
3. **Read followers** = Largest R port followers

This means:

- If W=2 and R=2 with N=3 followers: W+R=4 > 3 ✅ (overlap guaranteed)
- If W=1 and R=1 with N=3 followers: W+R=2 < 3 ❌ (stale reads possible)

## Files

| File | Description |
|------|-------------|
| `coordinator.py` | Cluster manager with HTTP API and event-based logging |
| `node.py` | Leader or follower node |
| `client.py` | Interactive client for read/write operations |

---

## Demo 1: Starting the Cluster

### Step 1: Start the coordinator with 3 followers

```bash
python labs/replication/coordinator.py --followers 3 --write-quorum 2 --read-quorum 2
```

This starts:

- **1 leader** on port 6001
- **3 followers** on ports 6002, 6003, 6004
- **Coordinator API** on port 6000

The coordinator will log events in the console as nodes start and join the cluster.

---

## Demo 2: Write with Quorum (W+R > N)

### Step 1: Start the interactive client

In a new terminal:

```bash
python labs/replication/client.py
```

### Step 2: Write data

In the client:

```bash
>>> write name distributed-systems
```

### Step 3: Watch the coordinator logs

You'll see the replication flow in the coordinator terminal:

1. Write arrives at leader → immediately stored
2. **Sync replication** (0.5s): follower-1, follower-2 get data (first 2 ports = W=2)
3. Coordinator logs sync acks and quorum status
4. **Async replication** (5s later): follower-3 receives the data automatically

### Step 4: Read immediately

In the client:

```bash
>>> read name
```

Even before async replication completes to `follower-3`, the read succeeds because R=2 queries `follower-2` and `follower-3`, and `follower-2` already has the data from the sync phase!

---

## Demo 3: Stale Reads (W+R ≤ N)

### Step 1: Restart with weak quorum

Stop the coordinator (Ctrl+C) and restart:

```bash
python labs/replication/coordinator.py --followers 3 --write-quorum 1 --read-quorum 1
```

Now:

- W=1: Only `follower-1` gets sync replication
- R=1: Only `follower-3` is in read quorum
- W+R=2 ≤ N=3: **No overlap!**

### Step 2: Write and immediately read

In the client:

```bash
# Write
>>> write test stale-check

# Read immediately (within 5s async delay)
>>> read test
```

**Expected**: The read will fail with "Key not found" because `follower-3` (the only node in the read quorum) hasn't received the async replication yet!

---

## Demo 4: Killing and Respawning Nodes

### Step 1: Kill a sync follower

From another terminal (or using the coordinator's status to find the ID):

```bash
# Example ID
curl -X POST http://localhost:6000/kill/follower-1
```

Coordinator logs will show:

- 💀 `KILLING: follower-1 [SYNC]`
- ⚠️ `WRITE QUORUM LOST` logging if you don't have enough nodes for W

### Step 2: Spawn replacement

```bash
curl -X POST http://localhost:6000/spawn
```

**Key behavior**: The dead follower is respawned on the same port to keep the cluster topology predictable.

---

## Configuration Options

```bash
python labs/replication/coordinator.py \
  --followers 3          # Number of followers
  --write-quorum 2       # W: Follower acks required for write
  --read-quorum 2        # R: Followers to read from
```

**Fixed delays** (for consistent demo):

- Sync replication: 0.5 seconds
- Async replication: 5 seconds

---

## Key Takeaways

1. **W + R > N = Strong consistency**: At least one node overlaps between write and read quorums
2. **W + R ≤ N = Eventual consistency**: Possible stale reads!
3. **Sync vs Async**: First W ports sync, rest async with visible lag
4. **Leader always writes**: But W followers must ack for success
5. **Spawn respawns dead first**: Same port reused for predictability

---

## Advanced: Direct API Access

While the `client.py` is the primary way to interact, you can also use `curl` for manual testing.

### Coordinator Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/write` | Write data (waits for W follower acks) |
| GET | `/read/{key}` | Read data (queries R quorum nodes) |
| GET | `/status` | Cluster status |
| POST | `/spawn` | Add follower |
| POST | `/kill/{node_id}` | Kill a follower |

### Example Curl Commands

```bash
# Write
curl -X POST http://localhost:6000/write -H "Content-Type: application/json" -d '{"key": "foo", "value": "bar"}'

# Read
curl http://localhost:6000/read/foo

# Status
curl http://localhost:6000/status
```

---

## Troubleshooting

**Writes timing out?**

- Check the coordinator logs to see which followers are alive
- If fewer than W followers are alive, writes will be rejected

**Seeing stale reads?**

- Check if W+R > N
- If not, async nodes (the ones with larger ports) may not have received data yet
