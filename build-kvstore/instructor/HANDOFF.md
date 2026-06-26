# Handoff: finish the EuroPython "build-kvstore" workshop (remaining polish)

> Paste the section below to a fresh agent to continue. The workshop is functionally
> complete, demo-ready, and now self-checking — everything here is optional polish.

---

I'm building an incremental, narrative distributed-KV-store workshop for a EuroPython 2026
tutorial, living in `build-kvstore/` of this repo (a distributed-systems teaching workshop;
read `CLAUDE.md` first). Previous sessions built and verified the core **and** the regression
suite. Read these before doing anything:
- `build-kvstore/instructor/SPEC.md` — the full design + phase status (source of truth); start at §10.
- `build-kvstore/instructor/bugs-fixed.md` — running bug log (4 bugs fixed so far).
- `wiki/decisions/2026-06-14_build-kvstore-incremental-restructure.md`,
  `wiki/decisions/2026-06-14_build-kvstore-checkpoint-build-approach.md`, and
  `wiki/decisions/2026-06-15_build-kvstore-validate-ladder.md` — the decisions.

## What already exists & is verified (do NOT redo)

- 11 checkpoints `build-kvstore/checkpoints/00…10` (single node → full Redis/Dynamo-like KV
  store), each runnable. Checkpoint 10 is the full-system gateway demo (no incident/grader).
- 9 incident scripts `build-kvstore/incidents/incident_01…09.py` (black-box red→green checks);
  stage 10 has no incident (it's a demo).
- 4 code gaps `build-kvstore/stages/{03,04,05,08}` (NotImplementedError + guidance).
- Makefile toolchain: `make start|gap|up|down|incident|reset|status` (all work).
- **`tools/validate_ladder.sh` is a working regression suite** (`make validate`): for each
  incident N it asserts GREEN on `checkpoints/N` (launched via that stage's own `up.sh`) and RED
  on a per-stage "before" state (gapped `stages/N` for code stages; deterministic config-flips
  otherwise). 18/18 cases pass (~3.5 min in-container). Subset runs:
  `bash tools/validate_ladder.sh 05 06`. **Re-run `make validate` after ANY edit to a
  coordinator/registry/node/incident, or to `tools/up.sh`/`down.sh`.**
- `build-kvstore/docs/stages.md` (per-stage guide), README, SPEC.

## CRITICAL operational rules (these cost earlier sessions hours — honor them)

- EVERYTHING runs inside Docker: `docker-compose up -d` then
  `docker-compose exec -T workshop bash -c '...'`. No host ports (port 7000 collides with macOS
  Control Center on the host). `make` IS installed in the container.
- Ports: stages 00–04 → 5001-5003; 05–10 → registry 9000 / coordinator 7000 / gateway 8000.
- CLEANUP IS A TRAP:
  - `pkill -f "coordinator.py"` (or `node.py`) MATCHES YOUR OWN test script if the script text
    contains `python coordinator.py`. Keep pkill in a SEPARATE shell call using bracketed
    patterns only (`[c]oordinator.py`), with NO literal command names in that script. OR just
    use `make down` (it kills by script name AND by port — the safe default).
  - `uvicorn --workers N` spawns orphan worker processes whose command line is just `python`
    (not `node.py`), so `pkill -f node.py` MISSES them. `make down` handles this (kills by port).
  - Always confirm `ss -ltn | grep -cE ":5001|:7000|:9000"` is 0 before a fresh run.
- Verification invariant: `incident_N` must be GREEN on `checkpoints/N` and RED on the gapped /
  previous state. `make validate` enforces the whole ladder; use it as the regression gate.
- Conventions (CLAUDE.md): log every non-trivial change in `wiki/decisions/` (+ update INDEX);
  document every bug you fix in `build-kvstore/instructor/bugs-fixed.md`. Don't touch `labs/` (it's
  the untouched reference the checkpoints were derived from).

## Remaining work (priority order)

1. **`docs/diffs/` chapter explainers** for the two chunky boundaries — `04→05` (introduce
   coordinator + leader/follower replication) and `07→08` (introduce registry + heartbeats +
   catchup). Short markdown: what changed and why, so the jump reads as "new chapter," not
   "rewrite." (`docs/diffs/` dir already exists, empty.) Self-contained, low risk.
2. **Wire `build-kvstore` into the top-level repo `README.md`** as the primary workshop path.
   Quick, high-discoverability win. (Originally item #5.)
3. **tmux layout for `make up`** so attendees see registry/coordinator/gateway/node logs in
   panes instead of backgrounded (`tmux` is installed). Update `tools/up.sh`. NOTE: `up.sh` is
   what `validate_ladder.sh` drives for its GREEN launches and readiness polling — keep the
   non-tmux/scriptable path intact (e.g. gate tmux behind a flag or TTY check) and **re-run
   `make validate` afterward** to prove the suite still boots every stage.
4. **Per-stage task notes** for the 4 code stages — a short `stages/{03,04,05,08}/TASK.md` (or
   confirm `docs/stages.md` is enough) describing the gap + acceptance criteria.
5. **Full rehearsal**: a clean end-to-end pass (`make start`, walk 00→10 via gap/up/incident/
   reset), confirm timing and that nothing is flaky. NOTE: `make validate` now covers the
   red→green correctness mechanically; this rehearsal is about the *human* flow, pacing, and
   the few machine-dependent thresholds (incident_01 `P95_BUDGET_MS`, incident_03 relative p95).

## Explicitly deferred (do NOT start unless asked)

- Faithful any-W/any-R quorum (v2) — current deterministic port-pinned model is intentional.
- Geo-distributed final-project capstone (placement/cost/latency optimization) — design exists
  in conversation history but was deferred.
- Slide updates (framing: GIL=Redis single-thread, hybrid-quorum disclosure, "follower recovery
  not leader failover", per-concept real-world anchors) — those live in the speaker's Google
  Slides, not the repo.

Verify as you go (`make validate` is the gate) and keep the decision log + bug log current.
