# Reframe the Stage 01/02 real-world examples (Stack Overflow + Figma)

**Date:** 2026-06-28
**Status:** accepted
**Area:** `build-kvstore/instructor/{motivating-incidents,real-world-systems,slide-deck}.md` (Stage 01 & 02 sections), instructor-only

## Context

The speaker flagged a real logical gap in Stage 01's framing: it motivated vertical scaling with
**Cloudflare's 2019 regex CPU meltdown** and **Redis `KEYS *`** — but neither is actually a
"vertical scaling *cured* it" story. Cloudflare's fix was to **kill the bad rule** (remove the work),
and Redis is single-threaded so it gets *nothing* from more cores (confirmed via web search: Redis
scales on clock speed + RAM, not core count). Those examples prove the **ceiling is real**, not that
*adding compute is the remedy*. The speaker wanted a clean example where scaling **up** demonstrably
solved the problem and the system was then fine — to motivate *why vertical scaling is the right first
move* — and a separate example to motivate Stage 02 (vertical *running out* → go horizontal).

## Decision

Split the two stages around two verified company stories (sources below):

- **Stage 01 → Stack Overflow** as the positive proof that scaling *up* is often the **whole answer**:
  one of the busiest sites on earth on a *handful* of servers, a single SQL primary taking almost all
  load, idling ~5–10% CPU for headroom, **never sharded**. Cloudflare is **demoted** to "the
  single-thread ceiling is real and brutal" (explicitly *not* a vertical-cure story). Added the
  everyday mechanism that maps to the lab's `--workers` flag: **workers = cores**
  (`gunicorn`/`uvicorn --workers`, Node `cluster`, `nginx worker_processes auto`). Kept Redis as the
  ceiling anchor with a one-line nuance that it does *not* prove throughput-scales-with-compute.
- **Stage 02 → Figma** as the bridge from Stage 01: for years all of Figma ran on a *single* Postgres
  on **AWS's largest instance**, until it hit limits money couldn't buy past (VACUUM reliability, max
  RDS IOPS) → forced horizontal. This is the "a bigger box is still one box" hinge. Notion's "Herding
  Elephants" cited as the corroborating counterpoint.

Concretely:
- `motivating-incidents.md` — Stage 01: new "payoff" paragraph (Stack Overflow + workers + the honest
  "Cloudflare is the ceiling, not the cure"); reframed Caveat; arc now tees up Figma. Stage 02: new
  "modern echo / bridge from 01" paragraph (Figma). Summary-table rows for 01 & 02 updated.
- `real-world-systems.md` — Stage 01: new Stack Overflow "vertical-as-end-state" block + "workers =
  cores" mechanism + a Redis nuance note. Stage 02: new Figma "when vertical runs out" block. Summary
  rows for 01 & 02 updated.
- `slide-deck.md` — Stage 01: reframed slide 24 (ceiling-not-cure), **new slide 26b** (Stack Overflow
  payoff), reframed slide 27 caveat/arc. Stage 02: **new slide 28b** (Figma bridge). Stage headers,
  Appendix A asset rows, and Appendix B cheat-sheet ranges updated; times +1m each (~7m / ~5m).

## Alternatives considered

- **Keep Cloudflare as the vertical-scaling proof.** Rejected — it's logically the opposite (the fix
  removed work; no compute would have helped). Keeping it *only* as the "ceiling is real" hook is the
  honest use.
- **Group Stack Overflow with Figma at Stage 02** (the speaker's first instinct). Rejected after
  discussion: Stack Overflow *never went horizontal* — it's the canonical "vertical was enough"
  story, so it belongs at **Stage 01**. Figma (vertical → ran out → horizontal) is the Stage 02 bridge.
  The contrast between the two is itself the 01→02 hinge.
- **Renumber the whole 73-slide deck to insert the two new slides.** Rejected as disproportionate for
  a "small change"; used sub-lettered slides (26b, 28b) so all downstream numbers + appendices stay
  stable, and noted the additions in the stage headers and cheat-sheet.

## Accuracy guardrails

- Load-bearing facts web-verified before writing: Stack Overflow hardware/headroom (Nick Craver, 2016
  — cited *as of 2016*), Figma single-largest-RDS-instance → VACUUM/IOPS ceiling (Figma blog, Apr
  2024), Redis "more cores don't help" (Redis benchmark docs + analysis), Notion "Cookie Clicker"
  rejection (Oct 2021). Specs hedged ("~768 GB", "~half a billion") and dated.
- Did **not** conflate Figma's *vertical scaling* phase (the 2020 single-largest-instance Postgres)
  with their later "vertical *partitioning*" (a sharding-flavored move) — only the single-box phase is
  cited as vertical-scaling proof.

## Side effects / risks

- **No code touched** → `make validate` unaffected (still 18/18). Pure instructor documentation,
  excluded from the attendee template.
- Risk: example specifics drift. Mitigation: each claim is dated and traceable to a primary source
  (Nick Craver / Figma blog / Redis docs / Notion blog).

## Sources

- Stack Overflow: https://nickcraver.com/blog/2016/03/29/stack-overflow-the-hardware-2016-edition/ ·
  https://nickcraver.com/blog/2016/02/17/stack-overflow-the-architecture-2016-edition/
- Figma: https://www.figma.com/blog/how-figmas-databases-team-lived-to-tell-the-scale/
- Notion: https://www.notion.com/blog/sharding-postgres-at-notion
- Redis single-thread / cores: https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/benchmarks/ ·
  https://pierreraffa.medium.com/redis-engine-cpu-investigation-77536adf6c6d
