# Module 16: Clock Skew

## 🎯 The Scenario

Server A says: "Write received at 12:00:00.000"
Server B says: "Write received at 11:59:59.500"

Server B's timestamp is *earlier*, but it happened *after*.

Your database uses "last write wins" with timestamps. **Server A's write gets overwritten by Server B's older write.**

*Can you trust clocks in a distributed system?*

---

## 💡 The Concept

### Clock Skew
The difference between clocks on different machines. Even with NTP, skew of 10-100ms is common.

### The Problem
If you use wall-clock timestamps for ordering:
- Newer events can appear older (and be discarded)
- Older events can appear newer (and overwrite)

### Solutions
- **Logical Clocks**: Counters, not timestamps (see Module 19: Vector Clocks)
- **Hybrid Logical Clocks**: Combine physical and logical time
- **TrueTime (Google Spanner)**: GPS + atomic clocks with bounded uncertainty

---

## 🚀 How to Run

```bash
python3 workshop_materials/16_clocks/skewed_node.py --port 16001 --offset 0
python3 workshop_materials/16_clocks/skewed_node.py --port 16002 --offset -300
```

Node 2's clock is 300 seconds (5 minutes) behind!

---

## 📚 The Real Incident

### Cassandra Consistency Issue

Cassandra uses client-supplied timestamps for versioning. If clients have different clock settings:
- Client A writes at (real) T=100
- Client B writes at (real) T=101 but sends timestamp T=50
- Client B's "newer" write is ignored, Client A's "older" write wins

About 1 in 10,000 operations showed stale data.

**Lesson:** Never trust client timestamps. Use server-side lamport clocks or hybrid logical clocks.

---

## 🏆 Challenge

Implement **Lamport Timestamps**:
- Each node has a counter
- On local event: counter++
- On send: attach counter
- On receive: counter = max(local, received) + 1
