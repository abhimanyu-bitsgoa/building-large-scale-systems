# Make INC-07 show the CAP tradeoff (writes refused, reads survive) and connect it to stage 06

- **Date:** 2026-06-25
- **Status:** accepted
- **Change / commit(s):** branch `europython-lab-design` (PR into `europython-branch` pending)

## Context

Stage 07 was the least compelling incident in the ladder. The RED state set `W=3` (=N) and showed
a single follower kill → write `503`. Two problems:

1. **`W=3` read as a strawman.** Nobody sets `W=N` on purpose, so "too-tight W breaks writes"
   landed as "don't do the dumb thing," with no motivation.
2. **The CAP tradeoff was named in the title but never shown as a tradeoff.** Attendees saw only
   one side — writes going down — not what was gained (consistency) or that reads kept working.
   A tradeoff needs both sides visible.

The deeper, more compelling story is the **06 → 07 connection**: stage 06 says *raise W+R for
consistency*; stage 07 says *but W is a dial with a price* — tolerable failures = `N - W`, so
cranking W to N buys a zero failure budget. `W=2, R=2` for `N=3` is the **majority quorum**
(`floor(N/2)+1`), the unique sweet spot that survives `floor(N/2)` deaths AND keeps `W+R>N`.

## Decision

1. **`incident_07_outage.py`** — enrich (not change) the discriminator:
   - Write a **canary** key while the cluster is healthy and wait 7s so every follower (incl. the
     async one) holds it. This is what lets us prove reads survive a kill.
   - Kill `floor(N/2)` followers.
   - Attempt a new write — **this remains the pass/fail discriminator** (`writes_ok`).
   - **Also probe a read of the canary.** Fold the result into the message: on RED, report
     "writes REFUSED (503) while reads still succeed — the system sacrifices write-availability to
     keep consistency (CP)." The `report()` boolean is still `writes_ok`, so the ladder is
     unaffected.
2. **`WORKSHOP-WALKTHROUGH.md` §07** — rewrite the narrative around the 06→07 connection, the
   `N − W` formula, the majority-quorum insight, and the CAP moment. Added the *scope caveat* that
   this is follower fault tolerance only (the leader remains an unaddressed SPOF).

## Why reads survive on RED (verified, not assumed)

RED is `W=3, R=2, N=3`. After killing 1 follower, 2 remain alive:
- Writes need `W=3` followers → only 2 alive → `can_write()` false → `503`.
- Reads need `R=2` followers → 2 alive → `can_read()` true → the canary (replicated before the
  kill) is returned.

Confirmed live in the container: RED printed *"writes are REFUSED (503: W quorum lost) while reads
still succeed … (CP)"* and exited 1.

## Alternatives considered

- **Read back the failed write instead of a canary.** Rejected — on RED the `after_failure` write
  is *rejected*, so that key never exists; reading it would miss regardless and prove nothing. A
  canary written *before* the kill is the only way to show reads survive.
- **Flip the pass/fail to consider reads too.** Rejected — the ladder discriminator must stay the
  write (that's what `W` changes between RED and GREEN). Reads are reported for narrative only.
- **Leave §07 as the bare 503 outage.** Rejected — the speaker found it uncompelling; the CAP
  tradeoff only teaches if both sides (lost write-availability, kept consistency) are visible.

## Side effects & risks

- **Ladder semantics preserved.** RED exits 1 (writes refused), GREEN exits 0 (writes survive).
  Verified `bash tools/validate_ladder.sh 07` → 2/2, and the full `make validate` → 20/20.
- **Runtime increases** by ~7s (the canary propagation wait) plus the existing 8s post-kill wait.
  Acceptable for a deliberately-paced stage.
- The canary write must succeed on BOTH configs before the kill: RED `W=3` with all 3 alive → ok;
  GREEN `W=2` with all 3 alive → ok. Holds.

## Verification

- `bash tools/validate_ladder.sh 07` → **2/2**.
- Full `make validate` → **20/20** (run after this change; INC-03 did not flake this run).
- Live RED message captured: writes refused + reads survive + CP framing.

## References

- `build-kvstore/incidents/incident_07_outage.py`
- [`WORKSHOP-WALKTHROUGH.md`](../../WORKSHOP-WALKTHROUGH.md) (§07)
- [INC-06 update-then-read staleness](2026-06-25_incident-06-update-then-read-staleness.md) ·
  [INC-05 fragility framing](2026-06-24_incident-05-fragility-framing.md) — the two prior stages
  this one builds the arc on
- [validate ladder](2026-06-15_build-kvstore-validate-ladder.md)
