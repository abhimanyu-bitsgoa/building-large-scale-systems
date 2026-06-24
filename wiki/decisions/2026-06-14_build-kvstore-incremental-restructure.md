# Restructure the workshop into an incremental "build-a-KVStore" (`build-kvstore/`)

**Date:** 2026-06-14
**Status:** accepted — implemented: 11 checkpoints, 10 incidents, 4 code gaps, Makefile toolchain,
per-stage guide, all verified in-container (4 latent lab bugs found & fixed). Optional polish
(`docs/diffs/` chapter explainers, tmux layout, faithful-quorum v2) remains.
**See also:** [checkpoint build approach](2026-06-14_build-kvstore-checkpoint-build-approach.md) ·
`build-kvstore/SPEC.md` · `build-kvstore/docs/bugs-fixed.md`

## Context

The workshop currently ships three *disjoint* labs (`labs/scalability`, `labs/replication`,
`labs/distributed-kvstore`), each with its own near-duplicate `node.py`/`client.py`/
`coordinator.py`. Concepts are presented as a menu rather than a story, and the three
near-identical files confuse anyone who diffs them. For the EuroPython tutorial we want a
**narrative** where the same system is built incrementally — from a single in-memory dict
behind HTTP up to a Redis-/Dynamo-like distributed KV store — so attendees *feel* they built
it, and each new feature is motivated by an incident that breaks the previous version.

## Decision

Add a new top-level directory `build-kvstore/` that presents the system as **11 stages
(00→10)**. Each stage is a complete, runnable **checkpoint** (a numbered directory, *not* a
git tag — chosen for zero-git-skill robustness in a 60-person room). Each transition has a
**black-box, red→green incident script**. Attendees work in a single `kvstore/` dir and can
`make reset STAGE=NN` to any checkpoint. A `Makefile` hides the multi-process startup.

Key sub-decisions (see `build-kvstore/SPEC.md` §9):
- **Derive checkpoints by subtraction** from the existing working system (checkpoint 10 ≈
  today's `labs/distributed-kvstore`), removing one feature at a time. Reuses lab code the
  author already knows; far safer than authoring 11 versions forward.
- **Keep the deterministic port-pinned quorum** for v1 (max reuse, rock-solid live demo) plus
  an honest "real systems count any-W/any-R" caveat. Faithful/random is a possible v2.
- Ports: stages 00–04 on `5001+`, 05–10 on the KV ports `7000/8000/9000` so the existing
  `assessment.py` runs unchanged at stage 10.
- 5 "write code" stages (03 adaptive LB, 04 rate limiter, 05 replication, 06 quorum read,
  08 heartbeat); the rest are config/observe. Gaps are `raise NotImplementedError`.
- Framing carried into stage READMEs: GIL = Redis's single-thread ceiling; per-concept
  "real-world anchors" (Redis/Dynamo/etcd); "automatic *follower recovery*, not leader
  failover"; capstone reframed as "misconfigure what *we* built."

## Alternatives considered

- **Keep the three disjoint labs** — robust and zero-effort, but weak narrative and the
  duplicate files are a smell. Rejected as the primary format.
- **Stitch labs as "previous + a diff" (A.5)** — cheaper, keeps independence, but loses the
  single-evolving-codebase feel. Kept as a fallback if time runs short.
- **Git-tag checkpoints** — clean diffs, but requires git fluency and an attendee editing in
  place loses work. Deferred to a secondary nicety; numbered dirs are primary.
- **Rewrite quorum to faithful any-W/any-R** — more honest, teaches the "intermittent bug"
  lesson, but more code and probabilistic (worse live demo). Deferred to v2.

## Consequences / risks

- **Authoring cost:** 11 checkpoints + 10 incidents + gaps + tooling. Mitigated by
  subtraction (reuse) and by the incident scripts doubling as a regression suite
  (invariant: `incident_N` RED on checkpoint N-1, GREEN on checkpoint N).
- **Two chunky boundaries** (04→05, 07→08) where the code jumps; documented in `docs/diffs/`.
- **Duplication in the repo** (11 snapshots) is intentional pedagogy, not rot.
- `labs/` is left untouched as the reference source; nothing existing is broken.

## Verification

All 11 checkpoints (00–10) were built and verified on clean ports inside the container; the full
pass/fail matrix lives in the
[checkpoint build approach](2026-06-14_build-kvstore-checkpoint-build-approach.md) and
`build-kvstore/SPEC.md`. Highlights: checkpoint 10 scores **100/100** on
`student_config_solution.json` (re-verified after every coordinator/registry edit); `05` shows
stale reads (W+R≤N), `06` fresh (W+R>N), `07` loses write quorum on `floor(N/2)+1` kills, `08`
keeps killed nodes dead, `09` auto-respawns **and** catches the revived node up.

## Bugs found during verification

Verification on realistic (manual, multi-second) timescales surfaced **three latent bugs in the
original labs** plus **one cleanup-robustness bug in the new tooling**, all fixed. The canonical
running log (full root-cause + verification per bug) is **`build-kvstore/docs/bugs-fixed.md`**; in
brief:

1. **Killed nodes resurrected themselves** — `/kill` used `terminate()` (SIGTERM), swallowed by the
   node's shutdown handler; the health loop re-marked it alive. Fixed → `process.kill()` (SIGKILL).
2. **Auto-respawned followers came up empty** — catchup only fired for a brand-new `node_id`, so a
   crashed node's same-id respawn never synced. Fixed → catchup moved to the coordinator's `/spawn`.
3. **`assessment.py reset_cluster()` was dead code** — read a non-existent `nodes` status key (the
   endpoint returns `followers`). Harmless only because the node-killing scenario runs last. Fixed.
4. **`make down` left orphaned uvicorn workers** holding the ports (their command line is just
   `python`, so `pkill -f node.py` missed them). Fixed → `down.sh` also kills by workshop port.

All re-verified; checkpoint 10 still scores 100/100, and the full `make` red→green flow works.
