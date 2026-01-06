# Module 19: Vector Clocks (Who came first?)

In a distributed system, we can't trust timestamps (Module 16). So how do we know if `Event A` caused `Event B`, or if they happened independently?

We use **Logical Clocks**. The most common version is a **Vector Clock**.

### The Concept
Every node maintains an array (a vector) where it tracks its own counter and what it *knows* about other nodes' counters.

1. When a node does something locally: "My counter += 1".
2. When a node sends a message: It attaches its entire vector.
3. When a node receives a message: It takes the `max` of each counter in the incoming vector and its own.

### Causal Ordering
- If $V_1 < V_2$ (all counters in $V_1$ are $\le$ $V_2$ and at least one is strictly less), then $V_1$ **happened before** $V_2$.
- If $V_1$ is not less than $V_2$ AND $V_2$ is not less than $V_1$, the events are **Concurrent** (They happened at the same time). This is how we detect **Conflicts**.

### How to Run

Run the simulation:
```bash
python3 workshop_materials/19_vector/vector_clocks.py
```

### What to Observe
1. **Causality**: Notice how Node 1's clock "incorporates" Node 0's clock after a message is sent. The system can prove Node 0 came first.
2. **Concurrency**: Notice the case where Node 0 says `[2, 0, 0]` and Node 1 says `[1, 1, 0]`.
   - Node 0 has a higher first counter.
   - Node 1 has a higher second counter.
   - Neither is "before" the other. They have branched! This is how Amazon Dynamo (the original) detected when two users updated their cart simultaneously on different nodes.
