# Module 21: CRDTs (Conflict-free Replicated Data Types)

## 🎯 The Scenario

Google Docs: You're typing in New York. Your collaborator is typing in Tokyo. You're both offline for a moment.

When you reconnect, **neither of you loses your work.** It just merges.

*How?*

---

## 💡 The Concept

### The Problem with Traditional Databases
If two writers update the same row, you need a central authority to pick a winner.

### CRDTs: No Coordination Needed
Data structures designed so that:
1. Every node can update independently
2. Updates can sync in any order
3. All nodes **converge** to the same state

### Common CRDT Types
| Type | Behavior |
|------|----------|
| G-Counter | Only increment. Merge = sum. |
| G-Set | Only add items. Merge = union. |
| LWW-Register | Last Writer Wins (by timestamp). |
| OR-Set | Add/remove items reliably. |

---

## 🚀 How to Run

```bash
python3 workshop_materials/21_crdt/visualize_crdt.py
```

**What you'll see:**
- Two nodes edit "offline"
- States diverge
- On merge, they converge to the same result

---

## 📚 The Real Use Case

- **Figma:** Real-time collaborative design
- **Redis Enterprise:** Geo-distributed conflict-free data
- **Riak:** Eventually consistent database

---

## 🏆 Challenge

Implement a **PN-Counter** (Positive-Negative Counter):
- Track increments separately from decrements
- Merge by summing each independently
- Value = sum(increments) - sum(decrements)
