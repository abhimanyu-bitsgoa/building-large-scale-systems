# Add a slide-by-slide deck blueprint for the talk

**Date:** 2026-06-28
**Status:** accepted
**Area:** `build-kvstore/instructor/slide-deck.md` (new), instructor-only (excluded from attendee template)

## Context

The speaker wants to build the EuroPython presentation as an **image-heavy, minimal-text** deck used
*alongside* the live labs — slides as a backdrop, the tmux dashboard as the proof. They asked for a
single artifact telling them *what to put on every slide* for the full ~175-minute session, drawing on
the workshop's existing narrative material rather than inventing new content.

We already had the two source docs but neither is a presentation plan:
- [`instructor/motivating-incidents.md`](../../build-kvstore/instructor/motivating-incidents.md) — the
  "why" (one real outage per stage, with pre-written hooks to say aloud).
- [`instructor/real-world-systems.md`](../../build-kvstore/instructor/real-world-systems.md) — the
  "what" (the production system each stage embodies; reusable tables).

Plus [`INSTRUCTOR-GUIDE.md`](../../build-kvstore/instructor/INSTRUCTOR-GUIDE.md) (pacing, caveats,
exercise answers) and [`../LAB-MANUAL.md`](../../build-kvstore/LAB-MANUAL.md) (exact commands).

## Decision

Add `build-kvstore/instructor/slide-deck.md`: a per-slide blueprint for the entire talk (73 slides
across Open → The Tenets [theory] → the 00–10 ladder → Close), with:

- **Design rules** enforcing the speaker's intent: ≤6-word headlines, one idea/visual per slide,
  scar-before-concept, the architecture diagram growing one box per stage, and the terminal treated as
  a slide on `[LIVE]` cues.
- **An explicit scope note up top** stating the deck targets the `build-kvstore/` ladder (stages
  00–10, `make lab STAGE=NN`) *only*, and that the repo's legacy top-level `labs/` folder
  (scalability/replication/distributed-kvstore, `:5000`/`:6000` ports) is **not** part of this talk —
  verified the deck names no `labs/` path, no legacy port, and that all four code-stage file paths
  (`load_balancer.py`, `rate_limiter.py`, `node.py`×2) and control-pane helpers exist under
  `build-kvstore/`.
- **A consistent per-slide template** — `Show` (visual) / `Text` (literal on-slide words) / `Say`
  (narration, quoting the incident hooks verbatim) / `Do [LIVE]` (dashboard commands) / `Caveat`.
- **A ~175-min timing budget** with a break and a **cut list** lifted from `INSTRUCTOR-GUIDE.md` §2
  (demote stage 08 to a demo, compress 00/02, end hands-on at 09).
- **Two appendices:** an asset checklist (which image to source per scar, pointing at the
  `motivating-incidents.md` Sources list) and a slide↔command speaker cheat-sheet.

Content is *assembled from*, not duplicative of, the existing docs: hooks come from
`motivating-incidents.md`, system/pattern tables from `real-world-systems.md`, commands from
`LAB-MANUAL.md`, and the honesty caveats from `INSTRUCTOR-GUIDE.md`. The theory section ("The Tenets")
is the one genuinely new stretch — fallacies, latency numbers, scaling, state, consistency spectrum,
CAP/PACELC, the `W+R>N` spine, tail latency, failure-at-scale — sequenced so each concept is "cashed
in" at a specific later stage (cross-referenced inline as → SNN).

## Alternatives considered

- **Generate actual `.pptx`/`.key` slides.** Rejected: the speaker explicitly wants a markdown *spec*
  to build the visual deck from (image sourcing, licensing, and their own design system are human
  decisions). A blueprint is more durable and reviewable than binary slides, and lives in git next to
  the labs.
- **Fold the slide plan into `INSTRUCTOR-GUIDE.md`.** Rejected: that guide is the run-the-room
  companion (pacing/troubleshooting/answers); a 73-slide visual plan is a different artifact and would
  bury both. Cross-linked instead.
- **One slide per stage.** Rejected: too coarse for an image-heavy talk where the *scar* needs its own
  full-bleed moment separate from the *concept* and the *live* run. Settled on a small cluster of
  slides per stage (scar → concept → [your-turn] → live → caveat → arc), matching the talk's rhythm.
- **Reproduce the theory in depth on slides.** Rejected in favour of visual, fast theory slides (the
  "slide is a backdrop" rule) that map onto the speaker's existing Google Slides theory deck.

## Accuracy guardrails

- All incident specifics (dates, magnitudes, root causes) are taken from `motivating-incidents.md`,
  which was itself web-verified when written (see
  [`2026-06-27_motivating-incidents-narrative-arc.md`](2026-06-27_motivating-incidents-narrative-arc.md)).
  No new factual claims were introduced.
- Every honesty **Caveat** from `INSTRUCTOR-GUIDE.md` is carried onto a slide where it belongs (S07
  the leaderless-rule-on-single-leader hybrid; S06 deterministic staleness; S09 follower-recovery-not-
  leader-election; S10 the gateway doesn't load-balance), plus a dedicated scope-honesty close slide
  (no leader election / no sharding / no persistence).
- All commands match `LAB-MANUAL.md`/`docs/stages.md` (`make gap/lab/reset/incident STAGE=NN`, the
  `nload`/`kv*` control-pane helpers, `WORKERS=1` for the S01 choke).

## Side effects / risks

- **No code touched** → `make validate` unaffected (still 18/18). Pure instructor documentation,
  excluded from the attendee template alongside the rest of `instructor/`.
- Risk: slide *count/numbering* drifts if the ladder changes (e.g. a stage is re-sequenced). Mitigation:
  the deck is organized by stage with a slide↔command cheat-sheet, so it re-numbers locally; treat it
  as a living doc and update it when stages move (as 06/07 did on 2026-06-26).
- Risk: image licensing for company logos/screenshots. Mitigation: Appendix A says to prefer official
  public postmortems or clean redraws and to verify licensing before the talk.
