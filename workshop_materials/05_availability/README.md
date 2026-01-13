# Module 5: Quorums & Availability

## 🎯 The Scenario

You run a banking app. Data is replicated across 3 servers for safety.

Suddenly, 2 of your 3 servers crash. You have **1 server left**.

*Can you still serve reads? Can you still serve writes? Should you?*

---

## 🧠 Pause and Think

1. If you allow reads from 1 server, could the data be stale?
2. If you allow writes to 1 server, what happens when the other 2 come back online?
3. What's the minimum number of servers that must agree for the data to be "safe"?

---

## 💡 The Concepts

### Replication
Storing the same data on multiple nodes. If one node dies, another has the data.

### Quorum
The minimum number of nodes that must participate in an operation for it to be valid.

**The Magic Formula: R + W > N**
- **N** = Total replicas
- **W** = Write quorum (nodes that must acknowledge a write)
- **R** = Read quorum (nodes that must respond to a read)

If R + W > N, every read will see at least one node that has the latest write.

| N | W | R | Guarantee |
|---|---|---|-----------|
| 3 | 2 | 2 | Strong consistency (2+2 > 3) |
| 3 | 1 | 1 | Eventual consistency (high availability, possible stale reads) |
| 5 | 3 | 3 | Can tolerate 2 failures |

### CAP Theorem
You can't have all three:
- **C**onsistency: Every read gets the latest write
- **A**vailability: Every request gets a response
- **P**artition tolerance: System works despite network splits

In practice, you must tolerate partitions. So you choose between C and A.

---

## 🚀 How to Run

```bash
python3 workshop_materials/05_availability/visualize_availability.py
```

**Expected output:**
```
--- SYSTEM HEALTHY ---
Result: SUCCESS. Got Version 1 from ['Node 1', 'Node 2', 'Node 3']

--- 💥 DISASTER: KILLING NODE 2 ---
Result: SUCCESS (Quorum Met). Got Version 1 from ['Node 1', 'Node 3']

--- 💥 CATASTROPHE: KILLING NODE 3 ---
Result: FAILURE. Only 1/3 nodes alive. R=2 not met.
```

---

## 📚 The Real Incidents

### XRP Ledger — February 2025 (1-Hour Halt)

The XRP Ledger relies on validators to agree on the next state. In February 2025:

1. Validation messages weren't being published correctly
2. Validators drifted apart—each saw different transactions
3. No single version could get the required 80% supermajority
4. **The network stopped for 1 hour**

The system chose **safety** (stop) over **liveness** (process potentially invalid transactions).

---

### etcd "Zombie Member" Bug (v3.5 → v3.6)

A subtle bug caused removed nodes to persist in etcd's membership list. This inflated the quorum requirement:

1. Real cluster: 3 nodes
2. Perceived cluster: 4 nodes (including "zombie")
3. Quorum requirement: 3 (instead of 2)
4. Operator takes 1 node down for maintenance
5. Active nodes: 2. Required quorum: 3. **Cluster freezes.**

Kubernetes control planes running this version suddenly became read-only.

---

## 🏆 Challenge

Implement **Read Repair**:

During a quorum read, if nodes return different versions:
1. Identify which version is newest
2. Update the stale nodes with the correct version
3. Return the newest version to the client

This self-heals consistency issues during normal reads.
