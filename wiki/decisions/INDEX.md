# Decision log index

A chronological index of every decision recorded in this folder (newest first).

> **Rule:** whenever you add a decision file, add its row here in the *same* change. See the
> **Logging decisions** section of [`CLAUDE.md`](../../CLAUDE.md).

| Date | Decision | Status | File |
| ---- | -------- | ------ | ---- |
| 2026-06-25 | Optional tmux dashboards: stage-10 per-component view + per-incident "watch servers react" | accepted | [2026-06-25_tmux-stage10-dashboard.md](2026-06-25_tmux-stage10-dashboard.md) |
| 2026-06-25 | Make INC-07 show the CAP tradeoff (writes refused, reads survive) + connect 06→07 | accepted | [2026-06-25_incident-07-cap-tradeoff-and-06-07-connection.md](2026-06-25_incident-07-cap-tradeoff-and-06-07-connection.md) |
| 2026-06-25 | Retool INC-06 to update-then-read pattern for genuine staleness (not absence) | accepted | [2026-06-25_incident-06-update-then-read-staleness.md](2026-06-25_incident-06-update-then-read-staleness.md) |
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
