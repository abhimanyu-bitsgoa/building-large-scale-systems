# Decision log index

A chronological index of every decision recorded in this folder (newest first).

> **Rule:** whenever you add a decision file, add its row here in the *same* change. See the
> **Logging decisions** section of [`CLAUDE.md`](../../CLAUDE.md).

| Date | Decision | Status | File |
| ---- | -------- | ------ | ---- |
| 2026-06-26 | Stage 10 → 5-min synthesis demo + take-home capstone (end hands-on at 09); correct the "load balancer returns at the gateway" claim (it doesn't — responsibility moved server-side to the coordinator); add `kvflood`; leave read-selection code untouched | accepted | [2026-06-26_stage-10-finale-demo-and-gateway-lb-correction.md](2026-06-26_stage-10-finale-demo-and-gateway-lb-correction.md) |
| 2026-06-26 | Re-sequence stages 06/07 into a Goldilocks arc: 06 = all-sync (`W=3,R=1`), 07 = majority quorum (`W=2,R=2`); INC-07's RED state is now stage 06, not a manual `W=3` command | accepted | [2026-06-26_stage-06-07-goldilocks-resequence.md](2026-06-26_stage-06-07-goldilocks-resequence.md) |
| 2026-06-26 | `AdaptiveStrategy.get_node`: use O(n) `min` instead of O(n log n) sort (and match the line the walkthrough teaches) | accepted | [2026-06-26_adaptive-strategy-min-over-sort.md](2026-06-26_adaptive-strategy-min-over-sort.md) |
| 2026-06-26 | Move the load balancer's debut from stage 02 to 03 (stage 02 = naive inline client, no `load_balancer.py`) so the 02→03 step adds a real artifact | accepted | [2026-06-26_stage-02-naive-client-load-balancer-debuts-at-03.md](2026-06-26_stage-02-naive-client-load-balancer-debuts-at-03.md) |
| 2026-06-26 | Add a client-side vs server-side load-balancing reference (real systems + pros/cons) for stage 03 | accepted | [2026-06-26_load-balancing-client-vs-server-reference-doc.md](2026-06-26_load-balancing-client-vs-server-reference-doc.md) |
| 2026-06-25 | build-kvstore: per-service `make lab` tmux (kill/spawn by hand), full `docs/diffs/` narrative arc + 2 chapter deep-dives, code gaps trimmed to one core line each | accepted | [2026-06-25_build-kvstore-tmux-diffs-gap-reduction.md](2026-06-25_build-kvstore-tmux-diffs-gap-reduction.md) |
| 2026-06-25 | Optional tmux dashboards: stage-10 per-component view + per-incident "watch servers react" | superseded (stage-10 view folded into `make lab`) | [2026-06-25_tmux-stage10-dashboard.md](2026-06-25_tmux-stage10-dashboard.md) |
| 2026-06-25 | Make INC-07 show the CAP tradeoff (writes refused, reads survive) + connect 06→07 | accepted (framing superseded by 2026-06-26 Goldilocks re-sequence; CAP mechanics kept) | [2026-06-25_incident-07-cap-tradeoff-and-06-07-connection.md](2026-06-25_incident-07-cap-tradeoff-and-06-07-connection.md) |
| 2026-06-25 | Retool INC-06 to update-then-read pattern for genuine staleness (not absence) | accepted (probe kept; stage reframed to all-sync by 2026-06-26 Goldilocks re-sequence) | [2026-06-25_incident-06-update-then-read-staleness.md](2026-06-25_incident-06-update-then-read-staleness.md) |
| 2026-06-24 | Reframe INC-05 from "write rejected" to "a single copy is fragile" (read-replica stranding) | accepted | [2026-06-24_incident-05-fragility-framing.md](2026-06-24_incident-05-fragility-framing.md) |
| 2026-06-24 | Make the walkthrough red-first throughout; incident messages outcome-honest | accepted | [2026-06-24_red-first-walkthrough-and-honest-incident-messages.md](2026-06-24_red-first-walkthrough-and-honest-incident-messages.md) |
| 2026-06-24 | Add a `WORKERS` override to `make up` (demo the stage-01 single-thread choke) | accepted | [2026-06-24_make-up-workers-override.md](2026-06-24_make-up-workers-override.md) |
| 2026-06-24 | Fix walkthrough: load each stage into `kvstore/` (`reset`/`gap`) before `make up` | accepted | [2026-06-24_walkthrough-load-stage-before-up.md](2026-06-24_walkthrough-load-stage-before-up.md) |
| 2026-06-24 | Add a stage-00 smoke-test incident (`make incident STAGE=00` shows the baseline works) | accepted | [2026-06-24_build-kvstore-stage00-smoke-incident.md](2026-06-24_build-kvstore-stage00-smoke-incident.md) |
| 2026-06-23 | Add WORKSHOP-WALKTHROUGH.md (instructor + attendee run guide) | accepted | [2026-06-23_workshop-walkthrough-doc.md](2026-06-23_workshop-walkthrough-doc.md) |
| 2026-06-15 | Automate `validate_ladder.sh` into a real regression suite (GREEN/RED per stage) | accepted | [2026-06-15_build-kvstore-validate-ladder.md](2026-06-15_build-kvstore-validate-ladder.md) |
| 2026-06-14 | `build-kvstore/` checkpoint build approach (flag-gating + subtraction) | accepted | [2026-06-14_build-kvstore-checkpoint-build-approach.md](2026-06-14_build-kvstore-checkpoint-build-approach.md) |
| 2026-06-14 | Restructure workshop into an incremental `build-kvstore/` | accepted | [2026-06-14_build-kvstore-incremental-restructure.md](2026-06-14_build-kvstore-incremental-restructure.md) |
| 2026-06-14 | Introduce CLAUDE.md (agent guidance) and a decision log | accepted | [2026-06-14_introduce-claude-md-and-decision-log.md](2026-06-14_introduce-claude-md-and-decision-log.md) |
