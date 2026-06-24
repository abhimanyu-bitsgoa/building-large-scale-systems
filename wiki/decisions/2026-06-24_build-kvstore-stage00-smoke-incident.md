# Add a stage-00 smoke-test incident (`make incident STAGE=00` shows the baseline works)

- **Date:** 2026-06-24
- **Status:** accepted
- **Change / commit(s):** branch `europython-lab-design` (PR into `europython-branch` pending)

## Context

`WORKSHOP-WALKTHROUGH.md` documents a uniform per-stage loop (`make up` → `make incident`), and
attendees naturally try `make incident STAGE=00` for the first stage. But the incident scripts
ran `01`–`10` only — stage 00 was a bare warm-up with no check — so the Makefile glob
`incident_00_*.py` matched nothing, the literal pattern was passed to `python`, and the command
failed with `No such file or directory`. Stage 00 also gave the attendee no positive
confirmation that the foundation (a single node = a dict behind HTTP) actually works before
building on it.

## Decision

Add `build-kvstore/incidents/incident_00_smoke.py`: a black-box **baseline smoke test** that
writes a key to the single node (`POST /data` on `:5001`) and reads it back (`GET /data/{key}`),
reporting GREEN via the standard `_harness.report` when the round-trip succeeds. Now
`make incident STAGE=00` behaves like every other stage and visibly confirms "the store works."
Updated the stage-00 entry in `WORKSHOP-WALKTHROUGH.md` and added a clarifying note to
`SPEC.md` §5.

## Alternatives considered

- **Doc-only: state "stage 00 has no incident"** (the first attempt). Rejected — it leaves the
  natural `make incident STAGE=00` command broken and gives attendees no confirmation the
  baseline works.
- **Make the Makefile print a friendly "no incident for stage 00" message.** Rejected — still no
  *positive* signal that the single node functions; a passing smoke test is more reassuring and
  keeps the loop uniform.

## Trade-offs

- `incident_00` has **no RED counterpart**, a deliberate departure from the strict red→green
  model the other incidents follow (nothing precedes stage 00 to break). Mitigated by documenting
  it explicitly as a *smoke test* and excluding it from the regression suite.

## Side effects & risks

- `tools/validate_ladder.sh` enumerates stages `01`–`10` (hardcoded loop), so it does **not**
  reference `incident_00` — `make validate` is unaffected and still passes 20/20.
- `tools/status.py` already lists stage `00`, so `make status` now shows it ✅ once the smoke
  test passes — consistent, no change needed there.

## Verification

Ran in the container on 2026-06-24: `make incident STAGE=00` → **GREEN** (write+read round-trip
succeeds) against a freshly seeded stage-00 node. `make validate` remains **20/20** (the new
file is not part of the 01–10 ladder).

## References

- [`build-kvstore/incidents/incident_00_smoke.py`](../../build-kvstore/incidents/incident_00_smoke.py)
- [`WORKSHOP-WALKTHROUGH.md`](../../WORKSHOP-WALKTHROUGH.md) (stage 00) · [`build-kvstore/SPEC.md`](../../build-kvstore/SPEC.md) §5
- [validate ladder](2026-06-15_build-kvstore-validate-ladder.md) · [walkthrough doc](2026-06-23_workshop-walkthrough-doc.md)
