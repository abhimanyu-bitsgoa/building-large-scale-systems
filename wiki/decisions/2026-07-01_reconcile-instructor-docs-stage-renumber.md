# Reconcile instructor docs to the post-renumber ladder (01–10, merged Stage 03)

**Date:** 2026-07-01
**Status:** accepted
**Area:** `build-kvstore/instructor/{motivating-incidents,real-world-systems,slide-deck}.md`

## Context

The 2026-06-30 change ([merge-horizontal-loadbalancing-deflake-inc03](2026-06-30_merge-horizontal-loadbalancing-deflake-inc03.md))
renumbered the code ladder: 1-indexed (00→01, 01→02) and merged old stages 02 (horizontal) + 03 (load
balancing) into a single **Stage 03 — horizontal scaling + load balancing**. The instructor narrative
docs had been *mostly* updated to match (section headers, most in-prose references), but an audit found
**residual stale references** — the renumber pass missed the summary tables, two arc lines, the
sources tags, and a theory cross-reference.

## Decision

Fix the stragglers so every stage reference matches the current code ladder (verified against
`checkpoints/`, `incidents/`, `tools/up.sh`: `01` single · `02` vertical · `03` horizontal+LB · `04`
rate limit · `05`–`10` unchanged):

- `motivating-incidents.md` — arc lines (`→ 01`→`→ 02`, `→ 02`→`→ 03`); **summary table** renumbered
  and the old "02 Horizontal" + "03 Load balancing" rows merged into one "03 Horizontal scaling + load
  balancing" row (keeping Twitter + Figma + Tail-at-Scale); sources tags (Stack Overflow `01`→`02`,
  Figma/Notion `02`→`03`).
- `real-world-systems.md` — **summary table** renumbered + the same 02/03 row merge.
- `slide-deck.md` — theory slide 10 ("Two ways to scale"): `S01 vertical, S02 horizontal` →
  `S02 vertical, S03 horizontal`, and `(→ S01, → S02)` → `(→ S02, → S03)`.
- `architecture.md` — audited, already consistent; no change.

Verified clean afterward: no `Stage 00` / `| 00` rows, no stray `(→ 01)` / `(→ S01)` arcs, no
standalone old `02 Horizontal` / `03 Load balancing` table rows; all `## Stage NN` headers across the
docs read 01–10 with the merged Stage 03.

## Alternatives considered

- **Re-do the whole renumber from scratch.** Unnecessary — most of it was already done; a targeted
  straggler audit (grep every stage-number token, fix the misses) was lower-risk than rewriting.
- **Leave the summary tables.** Rejected — they're the at-a-glance reference a reader trusts; stale
  numbers there are the most misleading place to leave them.

## Side effects / risks

- **No code touched** → `make validate` unaffected. Pure instructor documentation.
- Note: this is a *consistency* fix; the FAQ added earlier today
  ([instructor-faq-rate-limiting](2026-06-28_instructor-faq-rate-limiting.md)) was already authored
  against the 01–10 ladder, so all five instructor docs are now mutually consistent.
