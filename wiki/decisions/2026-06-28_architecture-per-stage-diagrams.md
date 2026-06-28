# Add a per-stage architecture/component-diagram doc for the talk

**Date:** 2026-06-28
**Status:** accepted
**Area:** `build-kvstore/instructor/architecture.md` (new), instructor-only (excluded from attendee template)

## Context

The speaker wants a **component diagram for every stage (00–10)** to put on screen during the talk —
the visual the audience watches "grow one box at a time." The [`slide-deck.md`](2026-06-28_slide-deck-blueprint.md)
blueprint repeatedly calls for "the architecture diagram growing by one box per stage"; this doc is the
concrete realization of that, kept separate so it can be shown/screenshotted on its own.

## Decision

Add `build-kvstore/instructor/architecture.md`: one ASCII component diagram per stage, each with the
flow, the box the stage adds (⚡ NEW), the pain it exposes (⚠), the quorum config where relevant, and a
one-line "teaches/scar." Plus a legend, a port map, the "subtraction story" callout, and a
"Full system at a glance" master diagram + layer→port→real-world table at the end.

**Built from the actual code, not memory** — read before writing:

- [`tools/up.sh`](../../build-kvstore/tools/up.sh) — the canonical per-stage launch (ports, node
  counts, quorum flags). This pinned the load-bearing facts:
  - Stages **00–04 run nodes on `:5001–:5003`** (not `:5000`); stage 04's rate limiter is **on the
    node** (`node.py --rate-limit`), *not* a gateway — the limiter only graduates to the gateway at S10.
  - Cluster stages **05–10**: coordinator `:7000`, leader `:7001`, followers `:7002–:7004` (N=3).
  - Quorum per stage: **05 = W1/R1** (weak → stale visible), **06 = W3/R1** (all-sync), **07 = W2/R2**
    (majority). Registry `:9000` joins at **08** (no auto-spawn), `--auto-spawn` at **09**, gateway
    `:8000` at **10**.
- `checkpoints/10-full-system/{coordinator,node,registry,gateway}.py` — the exact endpoints/arrows:
  coordinator `/write`→leader `/data`, `/read`→largest-R followers; leader `/replicate` to sync
  (smallest-W ports, 0.5s) + async (rest, ~5s); node `heartbeat_loop`→registry `/heartbeat` (2s);
  registry prune (5s TTL)→coordinator `/node-died` and, with `--auto-spawn`, `/spawn`; recovery via
  leader `/snapshot`→coordinator→follower `/catchup`. The `W+R>N` overlap is drawn explicitly for
  05/06/07 (sync set = smallest-W ports, read set = largest-R ports).

## Alternatives considered

- **Mermaid instead of ASCII.** Rejected for the *primary* per-stage form: ASCII renders everywhere
  (terminal, any slide tool, GitHub), matches the repo's existing diagram style (`CLAUDE.md`,
  `real-world-systems.md`, `docs/diffs/`), and — critically — lets the diagram **grow one box per
  stage on a fixed canvas** without auto-layout reflowing boxes between stages. **But** a Mermaid
  rendering of the *full-system* diagram was added as a complement (one place where auto-layout helps
  and the GitHub-rendered graphic is genuinely nicer), color-coded by tier; the per-stage diagrams
  stay ASCII.
- **Fold the diagrams into `slide-deck.md` or `docs/stages.md`.** Rejected: the slide deck is the
  narration/timing spine and `stages.md` is the attendee run-loop; a standalone diagram sheet is easier
  to show full-screen and to maintain. Cross-linked all three instead.
- **One combined diagram with toggles.** Rejected: the pedagogy *is* the incremental growth, so one
  diagram per rung (same canvas, +1 box) beats a single busy diagram.

## Accuracy guardrails

- Every port, box, arrow, and quorum value is sourced from `tools/up.sh` and the stage-10 checkpoints
  (cited above), not from the root `CLAUDE.md` (which still documents the legacy `labs/` ports
  `:5000`/`:6000` and is out of scope for this talk).
- Honesty caveats carried onto the relevant stage: S07 leaderless-rule-on-single-leader + port-ordered
  overlap; S09 follower-recovery-not-leader-election; S10 gateway-doesn't-load-balance.

## Side effects / risks

- **No code touched** → `make validate` unaffected (still 18/18). Pure instructor documentation,
  excluded from the attendee template.
- Risk: diagrams drift if ports/quorum/stage-launch change. Mitigation: the doc states it's derived
  from `tools/up.sh` and links it as the source of truth — re-derive from there if a stage is
  re-sequenced (as 06/07 were on 2026-06-26).
