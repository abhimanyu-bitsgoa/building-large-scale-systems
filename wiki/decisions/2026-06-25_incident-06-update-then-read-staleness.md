# Retool INC-06 to the update-then-read pattern for genuine staleness

- **Date:** 2026-06-25
- **Status:** accepted
- **Change / commit(s):** branch `europython-lab-design` (PR into `europython-branch` pending)

## Context

Stage 06 (quorum) and stage 05 (replication) had a symptom overlap that made them hard to tell
apart live. Both RED states produced a read that missed the expected value — in stage 05 because
the follower tier was empty (no replication), in stage 06 because the key was written for the
first time and the async follower hadn't caught up yet.

From the attendee's perspective both looked like "I wrote it and can't read it back." That
conflation undersells stage 06's core lesson, which is not "data is missing" but "data is
**stale**: the value that exists on the follower is an **old version**." The distinction matters
because:

- Stage 05 is about **durability** — does more than one node hold a copy at all?
- Stage 06 is about **consistency** — if multiple nodes hold copies, is the one you're reading
  the *current* version?

## Decision

Retool `incident_06_stale.py` to the **update-then-read** pattern:

1. Write `key` = `"old"` and **wait 7 seconds** (> the 5s async delay) so *every* follower,
   including the slow async ones, has the value.
2. Write `key` = `"fresh"` (the update) without waiting for async propagation.
3. Read `key` **immediately**.

With `W=1, R=1` (`W+R ≤ N=3`) the read hits the **async lagging follower**, which still holds
`"old"`. The attendee now sees `"old"` in their output instead of `"fresh"` — a genuinely stale
value, not a missing one. Every follower *has* the key; one is just *behind*.

The fix is still config (`raise R until W+R>N`), unchanged from before.

## Why 4 trials and 7s sleep

- 4 trials × 7s = ~28s per run. More trials add runtime without adding signal — 4/4 stale is
  as clear as 8/8 stale, and the validate run is already slow (~3.5 min).
- 7s > the 5s `ASYNC_DELAY` constant in `node.py` with 2s margin, ensuring the first write
  fully propagates on even a loaded container before the update.

## Alternatives considered

- **Keep writing a brand-new key each trial.** Rejected — produces "absence" (same symptom as
  stage 05), not "staleness." The whole purpose of the change is to make the two stages
  visually distinct.
- **Reduce the sleep / use a tighter margin.** Rejected — a flaky RED (where the first write
  sometimes hasn't propagated in time) would make the incident non-deterministic and hard to
  demo live.

## Side effects & risks

- **Ladder semantics preserved.** RED (W+R≤N, stage-05 config) exits 1; GREEN (W+R>N) exits 0.
  Verified with `bash tools/validate_ladder.sh 06` → 2/2.
- **Runtime increases slightly.** Each trial sleeps 7s; 4 trials = ~28s per run instead of the
  previous ~0s (immediate-read only). Acceptable for a workshop where each stage is walked
  through deliberately.
- The wait is on the **first** write (seeding "old"), not on the update; the update-to-read gap
  is still immediate, so the staleness window is faithfully reproduced.

## Verification

`bash tools/validate_ladder.sh 06` inside the container → **2/2**. Live output:
- RED: `4/4 immediate reads returned an old value — the async follower still held the previous
  value: raise R until W+R>N …`
- GREEN: `0/4 immediate reads returned an old value — the read set overlaps the write set
  (W+R>N): you always hit an up-to-date replica`

## References

- `build-kvstore/incidents/incident_06_stale.py`
- [`WORKSHOP-WALKTHROUGH.md`](../../WORKSHOP-WALKTHROUGH.md) (§06)
- [INC-05 fragility framing](2026-06-24_incident-05-fragility-framing.md) — the change that
  sharpened the contrast and motivated this one
- [validate ladder](2026-06-15_build-kvstore-validate-ladder.md)
