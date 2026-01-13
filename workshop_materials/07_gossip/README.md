# Module 07: Gossip Protocol

## 🎯 The Scenario

You run a cluster of **10,000 servers**. Each server needs to know:
- Which other servers are alive
- What data each server holds
- Configuration updates

*Do you really want a central "master" server that everyone polls? What if it dies?*

---

## 🧠 Pause and Think

1. If 10,000 nodes all poll a central server every second, how many requests/sec is that?
2. What if nodes just told their neighbors, and those neighbors told their neighbors?
3. How long would it take for information to spread?

---

## 💡 The Concept

**Gossip Protocol** (aka Epidemic Protocol): Nodes spread information like rumors or viruses.

1. Every few seconds, each node picks a **random neighbor**
2. They exchange what they know
3. The neighbor does the same with another random node
4. Information spreads exponentially

**Properties:**
- **Decentralized:** No single point of failure
- **Scalable:** O(log N) rounds to reach all nodes
- **Eventually consistent:** All nodes converge to the same state

Used by: Cassandra, DynamoDB, Consul, Serf, Riak

---

## 🚀 How to Run

### Step 1: Start 4 Gossip Nodes
```bash
python3 workshop_materials/07_gossip/gossip_node.py --port 7001 --id 1 --neighbors 7002,7003,7004
python3 workshop_materials/07_gossip/gossip_node.py --port 7002 --id 2 --neighbors 7001,7003,7004
python3 workshop_materials/07_gossip/gossip_node.py --port 7003 --id 3 --neighbors 7001,7002,7004
python3 workshop_materials/07_gossip/gossip_node.py --port 7004 --id 4 --neighbors 7001,7002,7003
```

### Step 2: Run the Visualizer
```bash
python3 workshop_materials/07_gossip/visualize_gossip.py
```

### Step 3: Inject an Update
```bash
curl -X POST http://localhost:7001/update
```

**What you'll see:** The update propagates across all nodes within seconds.

---

## 🎮 Micro-Challenge

1. Kill Node 3 (`Ctrl+C`)
2. Update Node 1: `curl -X POST http://localhost:7001/update`
3. **Question:** Does Node 4 still get the update? How?
4. Restart Node 3. Does it catch up?

---

## 📚 The Real Incident

### Slack — February 2022 (Gossip Storm)

Slack uses Consul for service discovery. Consul uses the Serf gossip protocol.

During a rolling upgrade, nodes were restarted too quickly. Each restart triggered a flood of gossip messages:
- "Node A is leaving!"
- "Node A is joining!"

The gossip traffic **saturated the network**. Health checks couldn't get through. Nodes started marking healthy peers as dead. This generated MORE gossip ("Node B is dead!").

The system "gossiped itself to death"—consuming all bandwidth on metadata about failures, leaving no capacity for actual traffic.

**Lesson:** Gossip is efficient at steady-state but can explode during mass membership changes. Slow rollouts prevent gossip storms.

---

## 🏆 Challenge

Modify the gossip node to use **Anti-Entropy**:

Instead of just spreading new updates, periodically do a full state comparison with neighbors. If your state differs, reconcile.

This catches cases where a message was lost (unreliable network).
