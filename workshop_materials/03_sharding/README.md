# Module 3 & 4: Sharding & Consistent Hashing

## 🎯 The Scenario

Your database has **1 billion user records** spread across 3 servers. You need to add a 4th server to handle growth.

With your current approach (modulo hashing: `user_id % 3`), adding a 4th server changes the formula to `user_id % 4`. 

*How many records need to move?*

---

## 🧠 Pause and Think

1. If you go from 3 servers to 4, what percentage of keys change their mapping?
2. During the data migration, what happens to requests for keys that are "in transit"?
3. Is there a way to minimize data movement when adding/removing servers?

---

## 💡 The Concepts

### Sharding (Partitioning)
Splitting data across multiple nodes based on a key. Each node is responsible for a **shard** of the data.

### Modulo Hashing
```python
server = hash(key) % num_servers
```
**Problem:** When `num_servers` changes, almost ALL keys move!

### Consistent Hashing
Arrange servers on a virtual ring (0-360°). Each key also maps to a position on the ring. A key is stored on the **first server clockwise** from its position.

**Advantage:** When you add/remove a server, only keys between that server and its predecessor move. ~1/N keys migrate instead of ~all keys.

### Virtual Nodes
To improve distribution, each physical server appears multiple times on the ring as "virtual nodes." This smooths out hotspots.

---

## 🚀 How to Run

### Step 1: See the Difference
```bash
python3 workshop_materials/03_sharding/visualize_rebalancing.py
```

**Expected output:**
```
🧪 Testing Strategy: MODULO
Keys Moved:   746/1000
Percentage:   74.6%
⚠️ HIGH IMPACT!

🧪 Testing Strategy: CONSISTENT_HASHING  
Keys Moved:   246/1000
Percentage:   24.6%
✅ LOW IMPACT!
```

### Step 2: Try the Router
```bash
python3 workshop_materials/03_sharding/router.py
```

### Step 3: Swap Strategies
Edit `workshop_materials/03_sharding/router.py`:
```python
# Line 7: Comment out
# self.strategy = ModuloStrategy()

# Line 8: Uncomment
self.strategy = ConsistentHashingStrategy(self.nodes)
```

Run again and add a 4th node. Notice the difference!

---

## 📚 The Real Incident

### Amazon DynamoDB — Why Consistent Hashing Exists

DynamoDB was designed from the ground up with consistent hashing. The 2007 Dynamo paper from Amazon describes why:

> "A system that needs to scale incrementally... should be able to add storage hosts one at a time, with minimal impact to the existing hosts."

Before consistent hashing, adding a single server to a sharded database meant:
1. Taking the entire cluster offline
2. Rehashing and migrating all data
3. Hours of downtime

With consistent hashing, DynamoDB can add capacity **without** taking the system offline. New nodes join the ring and receive only their fair share of keys.

---

### Cassandra Production Incident Pattern

Many Cassandra outages follow this pattern:
1. Cluster is at 80% capacity
2. Operator adds a new node
3. Data begins rebalancing... but rebalancing itself uses resources
4. Cluster tips over 100% capacity **during** rebalancing
5. Cascading failure

**Lesson:** Consistent hashing minimizes data movement, but you still need capacity headroom for rebalancing operations. Never add nodes to an already-stressed cluster.

---

## 🏆 Challenge

Implement **Rendezvous Hashing** (Highest Random Weight):

For each key, compute a score for each server: `score = hash(key + server_id)`. Assign the key to the server with the highest score.

Compare this to consistent hashing. When does Rendezvous perform better?
