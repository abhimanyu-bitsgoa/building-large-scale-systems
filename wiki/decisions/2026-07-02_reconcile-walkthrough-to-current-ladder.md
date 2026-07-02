# Reconcile WORKSHOP-WALKTHROUGH.md to the current 01–10 ladder

**Date:** 2026-07-02
**Scope:** root `WORKSHOP-WALKTHROUGH.md` only (no lab code touched). Status: accepted.

## Context

`WORKSHOP-WALKTHROUGH.md` is the root-level, attendee-and-instructor-facing guide for the
EuroPython workshop. It had drifted to the **pre-2026-06-30 stage ladder** while the lab under
`build-kvstore/` moved on. Two structural changes it never absorbed:

1. **The 2026-06-30 renumber + merge** ([2026-06-30_merge-horizontal-loadbalancing-deflake-inc03.md](2026-06-30_merge-horizontal-loadbalancing-deflake-inc03.md)):
   old `00→01`, `01→02`, and old **02 (horizontal) + 03 (load balancing) merged into one code
   stage 03**; stages 04–10 kept their numbers. `make start` now seeds checkpoint 01; validate
   is **16/16** (was 18/18).
2. **The registry-as-sole-detector redesign** ([2026-07-01_registry-as-sole-failure-detector-path-b.md](2026-07-01_registry-as-sole-failure-detector-path-b.md)):
   split the kill verbs into `kvkill` (administrative removal *through* the coordinator — it's
   told) vs `kvcrash` (unannounced crash — only the registry's heartbeats notice).

The reconciliation was done section-by-section against the two current authorities:
`build-kvstore/docs/stages.md` and `build-kvstore/LAB-MANUAL.md`.

## What changed

**Stage numbering (the core fix):** §1 config-stage list, §2 "checkpoint 00"→01, §3 cheat sheet,
§4.0 port tiers (`00–04`→`01–04`), §4.2 (`WORKERS=1` choke moved from STAGE=01 to STAGE=02), §5
ladder table (full rewrite to 01–10 with the merged stage 03), §6 stage headers/recipes/args, and
the top intro ("11 stages (00→10)"→"10 stages (01→10)"). §6's old stages 00/01/02/03 were rewritten
into new 01 (single node), 02 (vertical), and a merged 03 (horizontal + load balancing) whose red→
green is the adaptive-vs-round-robin p95 check (`nload … 96 12`, best-of-3).

**Incident renumbering in §8.4 / §9:** the p95-budget timing incident is **`incident_02`** (choke),
not `incident_01` (which is now the stage-01 smoke test); the `P95_BUDGET_MS=500` escape hatch is
now `make incident STAGE=02`. `incident_03`'s profile corrected from "24 requests" to "96 requests,
best-of-3".

**Counts:** validate 18/18→**16/16** (§8.1); "11 stages"→"10 stages" (§8.2 ×2); the 2-hour path
table re-bucketed (quick-framing `00,02`→`01`; fast-config `01,06,07`→`02,06,07`).

**kvkill vs kvcrash:** §4.2 helper table corrected (`kvkill` was wrongly described as "a hard kill
— simulates a real crash"; that is now `kvcrash`) and rows for `kvcrash` (08–10) and `kvflood` (10)
added. Demos that hinge on an *unannounced* death switched `kvkill`→`kvcrash`: stage 08 (§6 + §8.6),
stage 09 (§6 + §8.6), and the stage-10 finale beat 3 (§7). Stages 06/07 keep `kvkill` — the
"administrative removal, so the coordinator is told" framing is the exact teaching hinge into 08.

**Also:** §7 beat 1 "smart routing … back in stages 02–04" → "at stage 03" (routing is the
load-balancing stage now); §8.3 "Stage 01's single-thread ceiling" → "Stage 02's"; cosmetic
re-alignment of the §1 code block after the earlier verb rename.

## A source conflict I had to resolve (flag for future edits)

The stage-10 self-heal command **disagrees between the two authorities**: `docs/stages.md` uses
`kvcrash 1`, `LAB-MANUAL.md` uses `kvkill 1`. I chose **`kvcrash`** for the WALKTHROUGH finale
because the beat's own narration says "**Detected the death** → … → auto-respawned", which is
heartbeat detection (`kvcrash`), and because it keeps the WALKTHROUGH internally consistent with
its own helper-table definition (`kvkill` = "the coordinator is told", so nothing is "detected").
LAB-MANUAL's stage-10 `kvkill 1` is arguably a looser usage; worth aligning LAB-MANUAL to `kvcrash`
in a later pass so all three docs match.

## Risks / verification

- Docs-only; no code, no assessment impact. Numbers/claims were checked against the live repo:
  `checkpoints/` (01–10), `incidents/` (`incident_02_choke` = the p95 budget; `incident_03_imbalance`
  = 96 req / best-of-3), `validate_ladder.sh` (16 `run` cases), and `kvplay.sh` (`kvkill`=`/kill`,
  `kvcrash`=`/crash`, `kvflood`, `kvspawn`).
- Post-edit sweeps confirmed zero remaining `STAGE=00`, `checkpoint 00`, `18/18`, `11 stage`,
  `incident_01`-as-p95, `make gap`/`make reset`, or stray old-number cross-references; §6 headers
  are a clean 01→09 sequence (10 in §7).
- Resolves the "known residual staleness" flagged in
  [2026-07-02_make-verify-preflight-and-linux-chmod.md](2026-07-02_make-verify-preflight-and-linux-chmod.md).
