# Merge stages 02+03 into one "horizontal scaling + load balancing" stage; de-flake INC-03; 1-index the ladder

**Date:** 2026-06-30
**Status:** accepted
**Scope:** `build-kvstore/` only (the EuroPython workshop ladder). The legacy top-level `labs/` is untouched.

## Context / problem

Two related problems with the front of the ladder:

1. **Stage 02 (horizontal scaling) had a hollow red→green.** Its incident (`incident_02_spof.py`)
   only checked that ">=90% of requests are served across 3 nodes" — which, run sequentially with no
   concurrency, was effectively "did you start the other two processes." Stage 01 (vertical) already
   owns the genuine "single node saturates → scale it" incident, so stage 02 re-tread it with a
   trivial config flip and no observable dynamics. It was really a *narrative bridge* promoted to a
   full graded stage.

2. **Stage 03 (load balancing) was flaky and barely discriminating.** The incident
   (`incident_03_imbalance.py`) compared two single noisy p95 samples with a zero-margin `ad < rr`,
   and — critically — **all three nodes ran identical `--load-factor 28`**, differing only in worker
   count (1 vs 4). With equal per-request cost the worker-count gap is a weak, second-order signal
   that only appears under heavy concurrency, so adaptive often *lost* to round-robin. Measured at the
   incident's own params (`--concurrent 4 --requests 24`): adaptive lost 3/3 trials (68/52/61ms vs
   51/52/52ms). In the full `make validate` ladder, host contention pushed it around and INC-03/green
   intermittently failed (observed rr p95=44ms vs ad p95=59ms → MISMATCH), so the ladder occasionally
   reported 17/18 purely from timing noise, not a regression.

The user (the speaker) asked to (a) make adaptive *predictably* faster, (b) merge 02+03 into one
stage whose red is blind round-robin and whose green is adaptive routing, and (c) fix the flakiness.

## Decision

### 1. Make adaptive predictably win — via a real per-request capacity gap (load-factor)

Empirically (measured in-container), the lever that makes adaptive reproducibly beat round-robin is a
**deterministic per-request cost gap**, not a worker-count gap. The weak node now runs
`--load-factor 30 --workers 1`; the two strong nodes run `--load-factor 25 --workers 4` (in both
`tools/up.sh` stage 03 and `tools/tmux_lab.sh`). Under concurrency the weak node's heavier requests
queue on its single worker, so round-robin's blind 1/3 share lands there and drags the tail; adaptive
reads the rising latency/in-flight count and steers away. Measured at `--concurrent 12`: round-robin
p95 ≈ 210ms (rock-steady), adaptive ≈ 160–180ms — a consistent ~25% win across trials.

*Rejected knobs:* a bigger fib load-factor (33) was exponentially too slow (a single run timed out at
2 min) and GIL-noisy — fib is a poor *tuning* knob. A different strategy (weighted) was considered
and rejected: weighted deliberately keeps feeding the weak node a proportional slice, so its p95 win
is *smaller*, not larger. Adaptive (`min(nodes, key=score)`) stays the graded one-line exercise;
it gives the sharpest p95 win and the cleanest gap to fill. (Power-of-two is the strongest
real-world alternative and is shown alongside in the play phase.)

### 2. De-flake `incident_03_imbalance.py`

Three reinforcing changes (all overridable via env):
- **More load:** `--concurrent 12 --requests 96` (was 4 / 24) so p95 is stable and the weak node
  actually queues.
- **Best-of-N:** run each strategy `TRIALS=3` times and take the **minimum** p95. Host contention is
  strictly *additive*, so the minimum is the least-disturbed sample — comparing best-of-N for both
  strategies removes the single-noisy-sample flakiness. (This directly addresses the observed cause.)
- **Margin:** require `adaptive < round_robin * 0.9` (≥10% better), not a zero-margin `<`, so noise
  can't flip the verdict. The measured true gap (~25%) clears this comfortably.
Adaptive is measured first; in the gapped state it raises `NotImplementedError`, so the red case
fails fast without spending time on round-robin.

### 3. Merge 02+03 into one graded stage; 1-index the ladder

Stage 03 becomes **"horizontal scaling + load balancing"**: a two-act stage whose red is blind
round-robin bombarding the weak node and whose green is the adaptive routing the attendee implements.
This is exactly what `incident_03` already measures, so the graded incident is unchanged in role.

To keep the ladder contiguous (no gap, no "lab 0") **without** renumbering the complex back half, the
two *front* stages shift up and 02+03 collapse into 03:
- `00 single-node` → **01**, `01 vertical` → **02**, `02 horizontal` + `03 load-balancing` → **03**.
- **Stages 04–10 are completely untouched** (this is the whole point — the risky replication/quorum/
  discovery code never moves).

Resulting ladder: `01 single · 02 vertical · 03 horizontal+LB · 04 rate-limit · 05 replication ·
06 sync · 07 quorum · 08 discovery · 09 auto-recovery · 10 full-system`.

Mechanical consequences applied:
- Renamed `checkpoints/00-single-node`→`01-single-node`, `01-vertical`→`02-vertical`; **deleted**
  `checkpoints/02-horizontal` (the merged stage uses the load-balancing checkpoint, which already
  does round-robin via `--strategy round_robin`).
- Renamed `incidents/incident_00_smoke`→`incident_01_smoke`, `incident_01_choke`→`incident_02_choke`;
  **deleted** `incident_02_spof.py` (its hollow check is gone; the SPOF point is now spoken framing).
- Updated `tools/{up.sh,tmux_lab.sh,validate_ladder.sh,status.py,kvplay.sh,down.sh}`, `Makefile`
  (default `STAGE ?= 01`, `start` seeds `checkpoints/01-*`), `progress.json` (reset to `{}`).
  `validate_ladder.sh` now grades 02–09 (stage 01 single-node is the baseline with no red→green).
- Renumbered/merged every doc: `README.md`, `LAB-MANUAL.md`, `docs/stages.md`, `docs/diffs/README.md`,
  `docs/load-balancing-client-vs-server.md`, and instructor docs (`slide-deck.md`, `architecture.md`,
  `motivating-incidents.md`, `real-world-systems.md`, `SPEC.md`, `HANDOFF.md`, `TEMPLATE.md`,
  `INSTRUCTOR-GUIDE.md`, `europython-tutorial-prep.md`). In the slide deck the **slide numbers stay
  1–73** (they're content labels, not derived) — only the stage *groupings* and lab commands change;
  merged stage 03 spans slides 28–35 as a two-act section and carries two scars (Twitter + Google).

## Alternatives considered

- **Full renumber (02+03→02, shift 04–10 down to 03–09):** cleanest final numbering but rewrites the
  45KB slide deck + every back-half doc and renames 6 incident files right before the talk. Rejected
  for risk; the speaker chose the shift-the-front approach.
- **Keep the numbers, leave a non-graded stub stage 02:** fewest edits, but leaves an awkward
  content-less stage and isn't a true merge. Rejected.

## Risks / side effects

- Anyone with old muscle memory (`make lab STAGE=00`, `STAGE=01` for vertical) must relearn: single
  node is now **01**, vertical **02**, horizontal+LB **03**.
- INC-03 is slower (best-of-3 × 2 strategies): ~30s for its green case; the full ladder is ~6 min.
- The `incident_03` thresholds (`INC03_CONCURRENT/REQUESTS/TRIALS/MARGIN`) are machine-dependent; env
  overrides exist for a busier/quieter host.

## Verification

- `bash tools/validate_ladder.sh 03` run **5×** in a row: 5/5 green + 5/5 red (the flake is gone).
- Full `make validate` (now stages 02–09): **16/16 pass**, ladder invariant holds.
- Both run in the Docker container in the background (foreground times out and leaves orphan
  clusters). All node processes cleaned up afterward.
