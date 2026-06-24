# Add WORKSHOP-WALKTHROUGH.md (instructor + attendee run guide)

- **Date:** 2026-06-23
- **Status:** accepted
- **Change / commit(s):** branch `europython-lab-design` (PR into `europython-branch` pending)

## Context

`build-kvstore/` is functionally complete (11 checkpoints, 10 incidents, 4 code gaps, Makefile
toolchain, regression suite) and documented across several files: `build-kvstore/README.md`
(attendee intro), `SPEC.md` (design source of truth), `docs/stages.md` (per-stage guide),
`docs/HANDOFF.md` (agent continuation), and the three `build-kvstore` decision records. What was
missing was a **single operational guide** the speaker can hold and run the whole session
from — covering setup, the run model, every stage, the capstone, instructor pre-flight/pacing,
framing talking points, and troubleshooting — without having to assemble it from five sources
mid-talk.

## Decision

Add a top-level **`WORKSHOP-WALKTHROUGH.md`** as the master run guide, split into an
**attendee** path (stage-by-stage commands and the 4 code tasks) and an **instructor** path
(pre-flight `make validate`, pacing around the code stages and chapter boundaries, the framing
anchors, the two timing-sensitive incidents, and the cleanup foot-guns). Content is *derived
from* the existing docs/tooling — exact `make` verbs from the `Makefile`, the per-stage launch
behavior from `tools/up.sh`, the code-gap signatures read from `stages/{03,04,05,08}`, and the
ports/caveats from `SPEC.md` — so it stays faithful rather than inventing a parallel narrative.

## Alternatives considered

- **Extend `build-kvstore/README.md` instead of a new file** — keeps everything in one place,
  but the README is intentionally a short attendee on-ramp; folding in instructor pre-flight,
  pacing, and framing would bury that. Rejected in favor of a dedicated guide.
- **Put the guide inside `build-kvstore/`** — reasonable, but a root-level file is the more
  discoverable "start here" for someone opening the repo to run the workshop. Chose the root and
  linked down into `build-kvstore/` for all commands.
- **Instructor-only vs attendee-only docs (two files)** — rejected; the two audiences share most
  context (setup, the loop, the ladder), so one document with two clearly-marked sections avoids
  duplication and drift.

## Trade-offs

- Some overlap with `docs/stages.md` and `README.md` is unavoidable; mitigated by keeping the
  walkthrough command-focused and pointing to `SPEC.md`/`stages.md` for depth.
- A second hand-maintained doc can drift from the tooling. Mitigated by deriving every command
  from the actual `Makefile`/`up.sh` and by `make validate` remaining the mechanical correctness
  gate the walkthrough points instructors at.

## Side effects & risks

- If the code-gap signatures, ports, or `make` verbs change, `WORKSHOP-WALKTHROUGH.md` must be
  updated alongside (same risk every doc carries). The HANDOFF item "wire build-kvstore into the
  top-level README" is now partially served by this root-level guide.
- No code, checkpoint, incident, or tooling was modified — this change is documentation only.

## Verification

Ran `make validate` (the full regression suite) inside the container on 2026-06-23: **20/20
cases pass** (10 GREEN exit-0, 10 RED exit-1, ports confirmed free between cases). This confirms
the stage ladder that `WORKSHOP-WALKTHROUGH.md` documents is green on a clean run, so the
guide's commands and red→green claims are backed by a passing check rather than only derived
from the source files.

## References

- [`WORKSHOP-WALKTHROUGH.md`](../../WORKSHOP-WALKTHROUGH.md)
- [`build-kvstore/SPEC.md`](../../build-kvstore/SPEC.md), [`build-kvstore/docs/stages.md`](../../build-kvstore/docs/stages.md)
- [restructure](2026-06-14_build-kvstore-incremental-restructure.md) · [checkpoint build approach](2026-06-14_build-kvstore-checkpoint-build-approach.md) · [validate ladder](2026-06-15_build-kvstore-validate-ladder.md)
