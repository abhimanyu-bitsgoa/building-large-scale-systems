# 🎓 Capstone: Building the Resilient Node

## The Journey So Far

Throughout this workshop, you've learned individual distributed systems concepts in isolation:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     YOUR LEARNING PATH                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Module 1: Nodes          → Basic HTTP server with state           │
│        ↓                                                            │
│   Module 2: Rate Limiting  → Protecting servers from overload       │
│        ↓                                                            │
│   Module 3: Load Balancing → Distributing traffic across nodes      │
│        ↓                                                            │
│   Module 7: Sharding       → Distributing DATA across nodes         │
│        ↓                                                            │
│   Module 8: Replication    → Copying data for fault tolerance       │
│        ↓                                                            │
│   Module 9: Gossip         → Eventual consistency without leader    │
│        ↓                                                            │
│   Module 11: Registry      → Service discovery & membership         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
                    🎯 NOW: PUTTING IT ALL TOGETHER
```

---

## The Resilient Node

Open `23_resilient_system/resilient_node.py` - this is what a **production-grade distributed node** looks like.

It combines EVERYTHING you learned:

| Concept | Where It Appears | Lines |
|---------|-----------------|-------|
| **Heartbeats** | `heartbeat_loop()` | 59-76 |
| **Gossip Protocol** | `gossip_loop()` | 80-121 |
| **Consistent Hashing** | `get_responsible_nodes()` | 127-155 |
| **Replication** | `replicate_to_peers()` | 161-179 |
| **Version Conflicts** | `receive_replica()` | 234-246 |
| **Graceful Shutdown** | `graceful_shutdown()` | 307-320 |

---

## Hands-On: Run the Complete System

### Step 1: Start the Registry

```bash
cd 11_membership
python registry.py --port 5000
```

### Step 2: Start 3 Resilient Nodes

```bash
cd 23_resilient_system

# Terminal 1
python resilient_node.py --port 5001 --id node-1 --registry http://localhost:5000

# Terminal 2  
python resilient_node.py --port 5002 --id node-2 --registry http://localhost:5000

# Terminal 3
python resilient_node.py --port 5003 --id node-3 --registry http://localhost:5000
```

### Step 3: Write Data to Any Node

```bash
curl -X POST http://localhost:5001/data \
  -H "Content-Type: application/json" \
  -d '{"key": "user:1", "value": "Alice"}'
```

### Step 4: Watch It Replicate!

Check all three nodes:
```bash
curl http://localhost:5001/data/user:1
curl http://localhost:5002/data/user:1
curl http://localhost:5003/data/user:1
```

**All nodes should have the data!** (via gossip + replication)

---

## Test Fault Tolerance

### Kill a Node

1. Press `Ctrl+C` on node-3's terminal
2. Watch node-3 deregister gracefully
3. Write new data: `curl -X POST localhost:5001/data -d '{"key":"test","value":"hello"}'`
4. Data is still replicated to node-2!

### Restart the Node

1. Start node-3 again: `python resilient_node.py --port 5003 --id node-3 --registry http://localhost:5000`
2. Wait 3-6 seconds (gossip interval)
3. Check node-3: `curl http://localhost:5003/data/test`

**The data appears on node-3 via gossip!**

---

## Architecture Diagram

```
                    ┌─────────────────────┐
                    │     Registry        │
                    │   (Port 5000)       │
                    │                     │
                    │ • Tracks live nodes │
                    │ • Receives heartbts │
                    └─────────┬───────────┘
                              │ heartbeat every 2s
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
   │   Node 1    │     │   Node 2    │     │   Node 3    │
   │  Port 5001  │◄───►│  Port 5002  │◄───►│  Port 5003  │
   │             │     │             │     │             │
   │ • Data      │     │ • Data      │     │ • Data      │
   │ • Replicate │     │ • Replicate │     │ • Replicate │
   │ • Gossip    │     │ • Gossip    │     │ • Gossip    │
   └─────────────┘     └─────────────┘     └─────────────┘
          ▲                   ▲                   ▲
          │         GOSSIP every 3s               │
          └───────────────────────────────────────┘
```

---

## Tracing the Code: What Happens on a Write?

When you POST to `/data`:

```
1. Client → POST /data {"key": "x", "value": "1"}
   │
2. Node receives request
   │  └→ store_data() at line 199
   │
3. Store locally
   │  └→ data_store[key] = value
   │  └→ data_versions[key] = version + 1
   │
4. Trigger async replication
   │  └→ background_tasks.add_task(replicate_to_peers, ...)
   │  
5. replicate_to_peers() runs
   │  └→ get_responsible_nodes() → who should have this key?
   │  └→ for each responsible node: POST /replicate
   │
6. Target nodes receive /replicate
   │  └→ Compare versions (line 240)
   │  └→ Accept if newer, reject if stale
   │
7. Meanwhile, gossip_loop() runs every 3s
   └→ Picks random peer, syncs all keys
   └→ Eventually everyone converges
```

---

## 🏆 Congratulations!

You've now seen how all the pieces fit together:

- **Registry** keeps track of who's alive
- **Heartbeats** let nodes announce their presence  
- **Consistent Hashing** determines data ownership
- **Replication** copies data for fault tolerance
- **Gossip** handles eventual consistency
- **Graceful Shutdown** ensures clean deregistration

**This is how real distributed systems like Cassandra, DynamoDB, and Riak work!**

---

## Challenge Exercises (Optional)

1. **Add Rate Limiting**: Modify resilient_node.py to reject clients doing > 10 req/s
2. **Add Backpressure**: Track active requests and return 429 when > 50 concurrent
3. **Visualize Gossip**: Run `visualize_gossip.py` to see anti-entropy in action
4. **Break Things**: Kill the registry - what happens? (Nodes keep running!)
