# Automate `tools/validate_ladder.sh` into a real regression suite

**Date:** 2026-06-15
**Status:** accepted — implemented and verified (20/20 cases pass in-container).
**See also:** [restructure decision](2026-06-14_build-kvstore-incremental-restructure.md) ·
[checkpoint build approach](2026-06-14_build-kvstore-checkpoint-build-approach.md) ·
`build-kvstore/SPEC.md` §8/§12

## Context

`build-kvstore/` ships 11 checkpoints, 10 black-box incident scripts, and 4 code gaps. The
SPEC §8 invariant — *for every N, `incident_N` is RED on the "before" state and GREEN on
`checkpoints/N`* — was established and verified **once, manually** while the ladder was built.
There was no way to re-run it. `tools/validate_ladder.sh` was a stub that only *listed* what
files existed. That left the ladder's correctness un-checkable: any future edit to a
coordinator / registry / node / incident / assessment could silently break a stage (flip its
GREEN case to RED, or make an incident vacuously pass) with nothing to catch it.

This is the single highest-value remaining item because it converts the whole ladder into a
**self-checking regression suite**.

## Decision

Rewrite `validate_ladder.sh` to actually execute the invariant. For each requested stage N it
runs two cases and asserts the exit code:

- **GREEN** — seed `kvstore/` from `checkpoints/N`, launch it with the *attendee's own*
  `tools/up.sh N`, run `incidents/incident_N_*.py`, require exit 0.
- **RED** — seed/launch the **"before" state**, run the same incident, require exit ≠ 0.

Reusing `up.sh` for the GREEN launch is deliberate: the suite exercises the exact command
attendees run, so it also regression-tests `up.sh` itself.

### What "the before state" is, per stage

The before-state is not uniformly `checkpoints/(N-1)` — that doesn't always produce a
*meaningful* RED on the incident's fixed ports. Chosen per stage so the RED is **deterministic**
(no reliance on fragile timing margins):

| N | GREEN | RED (before) | Why this RED |
|---|-------|--------------|--------------|
| 01 | cp01 `--workers 4` | cp01 launched `--workers 1` | GIL serializes → p95 over budget |
| 02 | cp02 (3 nodes) | cp00 (single node) | only 1 of 3 ports answers → <90% served |
| 03 | cp03 | **gap** `stages/03` | `AdaptiveStrategy` raises → client can't measure adaptive |
| 04 | cp04 | **gap** `stages/04` | `FixedWindow.is_allowed` raises → 500s, never 429 |
| 05 | cp05 | **gap** `stages/05` | `replicate_to_follower` raises → followers never get data |
| 06 | cp06 (W2/R2) | cp05 launched W1/R1 | W+R≤N → immediate read is stale |
| 07 | cp07 (W2) | cp07 launched **W=3** | killing 1 follower loses the write quorum → 503 |
| 08 | cp08 | **gap** `stages/08` | `heartbeat_loop` raises → registry never sees the node |
| 09 | cp09 (auto-spawn) | cp08 (no auto-spawn) | killed follower stays dead |
| 10 | cp10 + `student_config_solution.json` | cp10 + broken `student_config.json` | starter config scores below the bar |

Two RED cases need a launch that `up.sh` doesn't expose as a stage (01 single-worker, 07 W=3);
these are spelled out as literal `cmd:` launches in the script. This is acceptable: the
validator is **author-only CI**, and each is a one-flag variation of the matching `up.sh` line.
The 4 code-gap REDs simply seed `stages/N` and reuse the checkpoint's `up.sh` launch — proving
the student's gap is exactly what the incident detects.

### Operational guards (SPEC §12 foot-guns)

- **Cleanup via `tools/down.sh` only** (kills by script name *and* by workshop port, so it
  catches orphaned `uvicorn --workers` whose cmdline is just `python`). The validator is run as
  a file (`bash tools/validate_ladder.sh`), so its own cmdline never contains
  `coordinator.py`/`node.py` — `down.sh`'s `pkill -f` cannot self-match it, and the incident
  scripts (`incident_NN_*.py`) don't match those patterns either.
- After every case, **block until all workshop ports are free** (poll `ss -ltn`) before the
  next launch, so leftover followers on 7002–7004 can't serve stale data into the next case.
- **Readiness gating** before each incident: node-tier stages poll `/health` (any HTTP answer
  counts — a gapped node may 500 but is still "up"); coordinator-tier stages poll `/status`
  until the expected number of followers report `alive`, then settle 2s for initial
  replication. A cluster that never comes up is reported as `SETUP-FAIL`, not a false RED.
- Runs a **subset** when given stage args (`bash tools/validate_ladder.sh 05 06`), the full
  ladder otherwise. `make validate` runs the full ladder.

## Alternatives considered

- **Uniform `checkpoints/(N-1)` for every RED** (literal SPEC §8 wording). Rejected: for several
  stages the previous checkpoint runs on different ports / different config and the incident
  would fail merely by *connection error* rather than by the absent feature, and for 01 the bare
  cp00 node has no load so the flood wouldn't even be slow (false GREEN). The per-stage
  before-state above produces a RED that is *about the feature*, which is the pedagogical point.
- **Gap-only REDs (skip the config-flip stages).** Simpler, but would leave 6 of 10 upgrades
  unguarded. Rejected — the config stages (06 quorum, 07 CAP, 09 recovery) are core teaching
  beats and cheap to assert deterministically.
- **Extend `up.sh` with hidden red variants.** Rejected — pollutes the attendee-facing launcher
  with author-test config. The two literal `cmd:` launches keep that noise inside the CI script.

## Consequences / risks

- A full run is ~3.5 min in-container (it boots and tears down ~20 clusters, several with
  multi-second propagation/heartbeat/catchup waits). It's author CI, not an attendee command;
  subset runs make iterating on a single stage fast.
- The only timing-sensitive case is **01** (p95 budget, `P95_BUDGET_MS=300`) — machine-dependent
  by nature. It passed comfortably here (green well under budget, red far over). If it ever
  flakes on slower hardware, widen the budget via the env var rather than weakening the suite.
- New guard against regressions: editing any coordinator/registry/node/incident/assessment now
  has a one-command check (`make validate`) that re-proves all 10 upgrades still discriminate.

## Verification

Run inside the Docker container. Every stage validated — both as subsets
(`… 02`, `… 05 06 07`, `… 03 04 08 09`, `… 01 10`) and as a full sequential `make validate`
run (3m32s) — **20/20 cases pass** (10 GREEN exit-0, 10 RED exit-1), with ports confirmed free
between cases. No source under `checkpoints/`, `stages/`, `incidents/`, or `labs/` was modified; this
change is confined to `tools/validate_ladder.sh`.
