# Make the walkthrough red-first throughout, and incident messages outcome-honest

- **Date:** 2026-06-24
- **Status:** accepted
- **Change / commit(s):** branch `europython-lab-design` (PR into `europython-branch` pending)

## Context

Two related rough edges surfaced while rehearsing the walkthrough:

1. **Incident messages claimed the failure mode even on success.** e.g. `incident_02` printed
   `"…30/30 served (100%); a single node leaves the rest unreachable"` — the trailing clause is
   *false* once the incident passes. An audit found most incidents (01, 02, 03, 04, 06, 07, 08,
   09, 10) appended static failure-mode/advice text ("scale up with --workers", "raise R", "lower
   W", "edit student_config.json") regardless of the actual result.
2. **The walkthrough mostly showed only the GREEN command.** Several stages jumped straight to
   the fixed launch (`make up STAGE=NN` → pass), so an attendee never *saw* the failure the stage
   is supposed to resolve — undercutting the whole red→green premise.

## Decision

1. **Outcome-conditional incident detail.** Every incident now computes its pass/fail boolean and
   prints one message for ✅ and a different one for ❌. The boolean itself is unchanged, so the
   scripts' exit codes (and therefore the regression suite) are unaffected.
2. **Red-first walkthrough.** Rewrote `WORKSHOP-WALKTHROUGH.md` so every stage **01–10** first
   runs the incident against the *un-fixed* state (❌), then applies the change and re-runs (✅).
   The "before" states are exactly the ones `validate_ladder.sh` already verifies:
   - 01 → `WORKERS=1`; 02 → single node (`up:00`); 03/04/05/08 → the gapped code; 06 → stage-05
     weak quorum; 07 → a manual `--write-quorum 3` launch; 09 → stage 08 (no auto-spawn);
     10 → the broken `student_config.json`.
   - Code stages note the **restart** (`make down ; make up`) needed for edited code to take
     effect; stage 07's RED uses a subshell `(cd kvstore && python coordinator.py …)` so shell A
     stays in `build-kvstore/`.
   - **Stage 00 is the sole exception** — it is the baseline (nothing precedes it to fail), kept
     as the green smoke test.

## Alternatives considered

- **Fix only `incident_02`'s message.** Rejected — the same static-text flaw was in most
  incidents; fixing one would leave the output inconsistent.
- **Leave the walkthrough green-only and explain the red in prose.** Rejected — *seeing* the
  failure is the pedagogy; per-stage commands should demonstrate it.

## Side effects & risks

- Incident edits are **message-only** (the `resolved` boolean is computed exactly as before), so
  `validate_ladder.sh` (which asserts exit codes) is logically unaffected — re-run as the gate.
- The red-first flows lengthen each stage's command block; mitigated by the consistent
  "fail first → fix" shape that now repeats identically across stages.

## Verification

`make validate` re-run inside the container after the incident edits: **19/20**, with the single
miss being `INC-03/green` — the adaptive-vs-round-robin p95 comparison flaked (adaptive measured
61ms vs round-robin 44ms that run). Re-running stage 03 alone passed 2/2
(`bash tools/validate_ladder.sh 03`), confirming it's the known timing artifact (see
WORKSHOP-WALKTHROUGH §8.4), **not** a regression: the incident edits are message-only and leave
every `resolved` boolean unchanged. (The two preceding changes' full runs were 20/20.)

## References

- [`WORKSHOP-WALKTHROUGH.md`](../../WORKSHOP-WALKTHROUGH.md) (§6, §7) · `build-kvstore/incidents/incident_0*.py`
- [load stage before up](2026-06-24_walkthrough-load-stage-before-up.md) · [WORKERS override](2026-06-24_make-up-workers-override.md) · [validate ladder](2026-06-15_build-kvstore-validate-ladder.md)
