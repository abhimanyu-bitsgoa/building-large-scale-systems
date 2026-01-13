# Module 21: CRDTs (Conflict-free Replicated Data Types)

How do Google Docs, Figma, or Notion allow multiple people to edit the same page at the same time without "locking" the file or losing data?

In traditional systems, you'd have a **Leader** who decides the order of edits. If two people type "A" and "B" at the same time, the Leader picks one and the other might get an "Update Conflict" error.

### The Solution: CRDTs
A CRDT is a data structure that can be replicated across multiple nodes where:
1. Every node can update its local copy independently.
2. Nodes can sync in any order (Commutative, Associative, Idempotent).
3. Once all nodes have merged all updates, they are **guaranteed** to arrive at the same state.

### Types of CRDTs
1. **G-Set (Grow-only Set)**: You can only add items. Merge is a simple "Union".
2. **LWW-Register (Last-Writer-Wins)**: Every update has a timestamp. Merge takes the one with the highest timestamp.
3. **OR-Set (Observed-Remove Set)**: More complex, allows adding and removing items.

### How to Run

Run the visualizer:
```bash
python3 workshop_materials/21_crdt/visualize_crdt.py
```

### What to Observe
- Node A and Node B both add items while "offline" (disconnected).
- Their states branch apart. 
- When we trigger a **Merge**, they both end up with the exact same list of items.
- This is the magic of "Eventual Consistency" without needing a central bottleneck!
