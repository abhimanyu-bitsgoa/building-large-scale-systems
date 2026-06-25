# 2026-06-26 — Add a client-side vs server-side load-balancing reference for stage 03

## Context

Stage 03 teaches load balancing, and in this workshop the load balancer is **client-side** — it
lives in `load_balancer.py`, a library that `client.py` imports; the nodes never see it. While
preparing the talk, the speaker wanted a ready reference for the natural follow-up question: *which
real systems are client-side, which are server-side, and what are the trade-offs?* — to narrate on
stage and to point attendees at.

## Decision

Added `build-kvstore/docs/load-balancing-client-vs-server.md`: a speaker cheat-sheet covering

- the two models in one diagram (decision-in-client + 1 hop vs decision-in-proxy + 2 hops),
- **real systems** for each (client-side: gRPC, Finagle, Ribbon, and — most relevant to a KV talk —
  Cassandra/Redis-Cluster/Mongo/Kafka drivers; server-side: Nginx/HAProxy/Envoy, cloud LBs, F5,
  kube-proxy/Ingress, Maglev/Katran, GSLB/anycast),
- **pros/cons** of each, the **L4 vs L7** distinction, and the **service-mesh/sidecar hybrid**,
- a one-liner that maps it back to the lab's own arc (client-side in 00–04 → server-side gateway +
  coordinator in 05–10).

Linked it from `docs/stages.md` §03 as a **Talk reference**.

## Why this placement

`docs/` already holds the speaker-facing material (`stages.md`, `diffs/`). A standalone file keeps
the conceptual reference out of the step-by-step stage guide while staying one click away from the
stage that raises it. No code or checkpoints touched, so the ladder is unaffected (`make validate`
not impacted).

## Notes

This is reference material, not a behavior change — there were no real alternatives beyond *where*
to put it (inline in `stages.md` §03, rejected as too long for the terse stage guide) and whether
to also link it from `diffs/README.md` (deferred; `stages.md` §03 is where the load-balancer
question actually surfaces).

## Files touched
- New: `build-kvstore/docs/load-balancing-client-vs-server.md`
- Edited: `build-kvstore/docs/stages.md` (§03 talk-reference link), `wiki/decisions/INDEX.md`
