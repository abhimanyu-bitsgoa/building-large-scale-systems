# Replication Lab

Learn about single-leader replication with configurable quorum semantics.

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
| `coordinator.py` | Cluster manager with HTTP API and real-time dashboard |
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

The TUI dashboard shows:
- Cluster status with sync/async/read follower indicators
- **Real-time data table** showing what data exists on each node

---

## Demo 2: Write with Quorum (W+R > N)

### Step 1: Write data

```bash
curl -X POST http://localhost:6000/write \
  -H "Content-Type: application/json" \
  -d '{"key": "name", "value": "distributed-systems"}'
```

### Step 2: Watch the dashboard

You'll see:
1. Write arrives at leader → immediately stored
2. **Sync replication** (0.5s): follower-1, follower-2 get data (first 2 ports = W=2)
3. Data table updates to show value on leader + sync followers
4. Response returns to client with acks
5. **Async replication** (5s later): follower-3 gets data

### Step 3: Read immediately

```bash
curl http://localhost:6000/read/name
```

Even before async sync completes, reads work because R=2 reads from follower-2 and follower-3 (largest ports), and follower-2 is in sync set!

---

## Demo 3: Stale Reads (W+R ≤ N)

### Step 1: Restart with weak quorum

```bash
python labs/replication/coordinator.py --followers 3 --write-quorum 1 --read-quorum 1
```

Now:
- W=1: Only follower-1 (port 6002) gets sync replication
- R=1: Only follower-3 (port 6004) is in read quorum
- W+R=2 ≤ N=3: **No overlap!**

### Step 2: Write and immediately read

```bash
# Write
curl -X POST http://localhost:6000/write \
  -H "Content-Type: application/json" \
  -d '{"key": "test", "value": "stale-check"}'

# Read immediately (within 5s async delay)
curl http://localhost:6000/read/test
```

**Expected**: The read may fail with 404 or return stale data because follower-3 hasn't received the async replication yet!

---

## Demo 4: Data Table Visualization

The dashboard shows a real-time table like:

```
📊 DATA TABLE (Real-time)
   Key          | leader       | follower-1   | follower-2   | follower-3  
   ----------------------------------------------------------------------
   name         | dist..(v1)   | dist..(v1)   | dist..(v1)   | ---        
   test         | new..(v1)    | new..(v1)    | ---          | ---        
```

Watch as async followers catch up over 5 seconds!

---

## Demo 5: Killing and Respawning Nodes

### Step 1: Kill a sync follower

```bash
curl -X POST http://localhost:6000/kill/follower-1
```

Dashboard updates:
- follower-1 shows 🔴 (dead)
- Another follower may become sync if needed

### Step 2: Spawn replacement

```bash
curl -X POST http://localhost:6000/spawn
```

**Key behavior**: Dead follower is respawned on same port!

```json
{
  "status": "respawned",
  "node_id": "follower-1",
  "port": 6002,
  "was_dead": true
}
```

---

## Understanding the Dashboard

```
📊 QUORUM STATUS
   Write Quorum (W=2 followers): ✅ OK
   Read Quorum  (R=2 followers): ✅ OK

👑 LEADER
   🟢 leader @ http://localhost:6001

📋 FOLLOWERS (3)
   🟢 follower-1 @ http://localhost:6002 (port 6002) [SYNC]
   🟢 follower-2 @ http://localhost:6003 (port 6003) [SYNC, READ]
   🟢 follower-3 @ http://localhost:6004 (port 6004) [ASYNC, READ]
```

- **SYNC**: Gets fast replication (0.5s) - part of write quorum
- **ASYNC**: Gets slow replication (5s) - visible lag for demo
- **READ**: Used for read quorum queries

---

## API Reference

### Coordinator Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/write` | Write data (waits for W follower acks) |
| GET | `/read/{key}` | Read data (queries all, waits for R follower acks) |
| GET | `/status` | Cluster status with sync/async/read classification |
| GET | `/data-table` | Raw data from all nodes (JSON) |
| POST | `/spawn` | Add follower (respawns dead ones first) |
| POST | `/kill/{node_id}` | Kill a follower |

### Example Requests

```bash
# Write (waits for W=2 follower acks)
curl -X POST http://localhost:6000/write \
  -H "Content-Type: application/json" \
  -d '{"key": "foo", "value": "bar"}'

# Read (queries all, needs R=2 follower responses)
curl http://localhost:6000/read/foo

# See sync/async/read assignments
curl http://localhost:6000/status

# Kill follower
curl -X POST http://localhost:6000/kill/follower-1

# Spawn (respawns dead follower-1 first!)
curl -X POST http://localhost:6000/spawn
```

---

## Configuration Options

```bash
python labs/replication/coordinator.py \
  --followers 3          # Number of followers
  --write-quorum 2       # W: Follower acks required for write
  --read-quorum 2        # R: Followers to read from
  --no-dashboard         # Disable TUI (use for background mode)
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

## Troubleshooting

**Dashboard not updating?**
- Data table polls every 1 second
- Make sure nodes are alive (🟢)

**Writes timing out?**
- Check if W followers are alive
- Sync replication has 60s timeout

**Seeing stale reads?**
- Check if W+R > N
- If not, async nodes may not have data yet
