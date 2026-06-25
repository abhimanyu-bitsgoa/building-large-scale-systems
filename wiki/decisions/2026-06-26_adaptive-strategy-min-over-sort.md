# 2026-06-26 — AdaptiveStrategy.get_node: O(n) `min` instead of O(n log n) sort

## Context

The stage-03 answer key (`checkpoints/03-load-balancing/load_balancer.py`,
`AdaptiveStrategy.get_node`) selected the best node by building a list of `(node, score)` tuples,
sorting it ascending, and returning the first element:

```python
scored_nodes = [(node, node_stats.get_score(node)) for node in nodes]
scored_nodes.sort(key=lambda x: x[1])
return scored_nodes[0][0]
```

Two problems:

1. **Wrong tool for the job.** We only need the *minimum*, not a full ordering. Sorting is
   O(n log n) and allocates a throwaway list of tuples; finding the minimum is a single O(n) pass.
2. **Inconsistent with what we teach.** `WORKSHOP-WALKTHROUGH.md` §03 tells students the one-line
   answer is `return min(nodes, key=node_stats.get_score)` — but the answer key did something else.
   For a teaching repo, the canonical solution should be exactly the line we tell people to write.

## Decision

Replace the sort with the idiomatic O(n) argmin:

```python
# Pick the lowest-score node (score blends latency + active requests; lower is better).
# We only need the minimum, so this is a single O(n) pass — no full sort.
return min(nodes, key=node_stats.get_score)
```

Only the **checkpoint** (answer key) changed. The gapped exercise in
`stages/03-load-balancing/load_balancer.py` is untouched — it still raises `NotImplementedError`
with the TODO, so the student writes this line themselves.

## Why this is behavior-preserving

`min(nodes, key=f)` returns the **first** element achieving the minimum (Python's `min` keeps the
earliest on ties). `list.sort` is **stable**, so `scored_nodes[0]` was likewise the first node in
input order with the minimum score. Both pick the same node for every input, including ties — so the
adaptive routing decision is identical and the incident outcome cannot change.

## Verification

`make validate` re-run after the change — the INC-03 GREEN case seeds this checkpoint. (Expected
**20/20**, unchanged, since the selection is semantically identical.)

## Files touched
- Edited: `build-kvstore/checkpoints/03-load-balancing/load_balancer.py`, `wiki/decisions/INDEX.md`.
