# Module 19: Vector Clocks

## 🎯 The Scenario

User A (on Phone) edits a document: "Hello World"
User B (on Laptop) edits the same document: "Hello Universe"

Both were offline. When they sync, whose version wins?

*More importantly: how do you even detect this happened?*

---

## 💡 The Concept

### Logical Clocks → Vector Clocks
Each node maintains a vector of counters (one per node):
```
Node A: [A:3, B:1, C:2]  ← "I've seen 3 events from A, 1 from B, 2 from C"
Node B: [A:2, B:4, C:2]  ← Different history!
```

### Comparing Vectors
- **V1 < V2:** All counters in V1 are ≤ V2, at least one is strictly less → V1 happened before V2
- **Neither < other:** Concurrent events → CONFLICT detected!

---

## 🚀 How to Run

```bash
python3 workshop_materials/19_vector/vector_clocks.py
```

**What you'll see:**
- Events that are causally related (one happened before another)
- Events that are concurrent (branched history)

---

## 📚 The Real Use Case

Amazon's original Dynamo paper (2007) used vector clocks to detect conflicts. When two shopping cart updates happened on different nodes, Dynamo merged them rather than dropping one.

---

## 🏆 Challenge

Implement conflict resolution using vector clocks:
- Detect when two writes are concurrent
- Present both versions to the user (or merge automatically)
