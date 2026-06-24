# Add an optional `WORKERS` override to `make up` (to demo the stage-01 choke)

- **Date:** 2026-06-24
- **Status:** accepted
- **Change / commit(s):** branch `europython-lab-design` (PR into `europython-branch` pending)

## Context

Stage 01 teaches vertical scaling: a single-worker node (one GIL) chokes on CPU-bound load, and
adding workers fixes it. But `make up STAGE=01` hardcoded `--workers 4` — the fixed/green
config — so there was **no `make`-level way to show the RED** (the choke). Demoing it meant
either editing `tools/up.sh` by hand (error-prone in a big room, and it breaks the hidden-startup
abstraction `make up` exists to provide) or a manual `python node.py ... --workers 1` launch
(off the `make` path).

## Decision

Add an optional `WORKERS` variable to the `make up` target, threaded through to `up.sh` and read
**only by stage 01**, defaulting to 4:

- `make up STAGE=01 WORKERS=1` → single-worker choke (the incident, RED).
- `make up STAGE=01` → unchanged (4 workers, GREEN).

Updated the stage-01 walkthrough to demo choke → fix via this flag, and added a Makefile help
note.

## Alternatives considered

- **Manual `python node.py --workers 1` launch.** Works, but leaves the `make` flow; kept as a
  fallback, not the primary path.
- **Editing `up.sh` live.** Error-prone in a 60-person room and breaks the abstraction.
- **A separate `01-slow` pseudo-stage.** More surface area and a duplicate launch path; the env
  override is smaller and touches only stage 01.

## Side effects & risks

- `WORKERS` defaults to 4 via `${WORKERS:-4}`, so `make up STAGE=01` (with `WORKERS` empty) is the
  byte-for-byte same launch as before. Every other stage ignores `WORKERS`.
- `tools/up.sh` changed → the regression suite was re-run (the standing rule for any `up.sh`
  edit). `validate_ladder.sh` invokes `up.sh` **without** setting `WORKERS`, so its stage-01
  GREEN launch is unchanged, and its stage-01 RED uses its own literal `--workers 1` command.

## Verification

In-container on 2026-06-24: `make up STAGE=01 WORKERS=1` prints "1 worker(s)" and
`make up STAGE=01` prints "4 worker(s)", both booting cleanly. `make validate` re-run after the
edit: **20/20** (the ladder is unaffected — confirmed before commit).

## References

- [`build-kvstore/Makefile`](../../build-kvstore/Makefile), [`build-kvstore/tools/up.sh`](../../build-kvstore/tools/up.sh) (stage 01)
- [`WORKSHOP-WALKTHROUGH.md`](../../WORKSHOP-WALKTHROUGH.md) (stage 01)
- [load stage before up](2026-06-24_walkthrough-load-stage-before-up.md) · [validate ladder](2026-06-15_build-kvstore-validate-ladder.md)
