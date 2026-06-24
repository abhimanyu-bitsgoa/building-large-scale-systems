# Reframe INC-05 from "write rejected" to "a single copy is fragile" (read-replica stranding)

- **Date:** 2026-06-24
- **Status:** accepted
- **Change / commit(s):** branch `europython-lab-design` (PR into `europython-branch` pending)

## Context

Rehearsing stage 05, the RED state printed `write rejected (503)` and stopped. That is an
internal-mechanism message — it tells attendees the quorum machinery refused the write, but it
does *not* convey the lesson the stage exists to teach (*why* you need replication). It also
risked being mis-framed as "the leader died and we lost data," which this workshop explicitly
does **not** model (it recovers *followers*, not the leader — see talk-readiness findings).

Two reframings were on the table (proposed by the speaker):

1. **Fragility / unavailability** — show that a single copy is fragile, motivating replication
   for durability, *without* invoking leader failover.
2. **Read distribution / scaling** — show that reads pile onto one node, and replication spreads
   them across replicas.

## What the code actually does (the deciding fact)

Reading the checkpoint:

- The leader's `/data` handler stores the write **locally first** (`node.py:248`), *then* calls
  replication (`node.py:263`). In the gapped state `replicate_to_follower` raises
  `NotImplementedError`, so the leader keeps the only copy and the coordinator write 503s — but
  **the data exists on the leader**.
- The coordinator read path (`coordinator.py` `get_read_followers` / `read_data`) queries the
  **follower tier only** — reads are *never* served by the leader. This is the Redis
  primary–replica model the stage ladder already anchors to.

So option 2's literal mechanic ("reads bombard the leader") is **false here** — reads already go
to the followers; without replication those followers are simply *empty* and reads miss. Option 1
is exactly what the architecture demonstrates: the write is stranded on one node, unreachable
through the read path. Option 1 also subsumes the durability intuition behind option 2 ("data
should live on more than one node").

**Decision: option 1, realized as read-replica stranding.**

## Decision

1. **`incident_05_replication.py`** no longer early-returns on the write's non-200. It lets the
   flow continue to the coordinator read (served by the empty follower tier), and uses the
   **read miss** as the RED signal. Messages are now outcome-honest and carry the lesson:
   - ❌ "the leader holds the only copy: the follower read-tier is empty, so the data is
     stranded on a single node — replication is what populates the replicas that serve reads"
   - ✅ "the write reached the follower read-tier — your data now lives on more than one node
     and reads are served from the replicas"
2. **`WORKSHOP-WALKTHROUGH.md` §05** reframed from "write isn't durable" to the stranded-copy
   story, with an optional live `curl` (`leader:7001/data/<key>` HAS it vs
   `coordinator:7000/read/<key>` MISSES) and an explicit "we are not doing leader failover here"
   caveat.

## Alternatives considered

- **Keep the 503 and only reword the message.** Rejected — the speaker found the rejection itself
  unconvincing; the read miss is a stronger, more intuitive failure to *watch*.
- **Option 2 (read load-balancing across replicas).** Rejected — not what this code does (reads
  never hit the leader), so it would require hand-waving and break the "say only what the system
  does" honesty bar held elsewhere in the walkthrough.
- **Kill the leader to show fragility.** Rejected — that is the failover/SPOF story the workshop
  deliberately does not model (no leader promotion), and it would contradict the recorded framing
  caveat.

## Side effects & risks

- **Ladder semantics preserved.** RED (no replication) still fails — the read misses → exit 1.
  GREEN (replication implemented) still passes — the write propagates → read returns `v1` →
  exit 0. The student-exercise gap and `node.py` are untouched. Re-run `make validate` as the gate.
- The RED path now performs a real coordinator read after the write; `can_read()` is satisfied
  because the followers are alive (just empty), so the read proceeds and misses as intended.
- Slightly longer RED runtime (the `time.sleep(6)` replication wait now also runs on RED). Minor.

## Verification

Stage 05 validated in isolation inside the container after the change —
`bash tools/validate_ladder.sh 05` → **2/2** (RED still exits 1, GREEN exits 0). The RED run now
prints the fragility message ("the leader holds the only copy: the follower read-tier is empty,
so the data is stranded on a single node …"). A full `make validate` is the standing gate before
committing (expect 20/20, modulo the known INC-03 timing flake — see
[red-first walkthrough](2026-06-24_red-first-walkthrough-and-honest-incident-messages.md) §8.4).

## References

- [`WORKSHOP-WALKTHROUGH.md`](../../WORKSHOP-WALKTHROUGH.md) (§05) ·
  `build-kvstore/incidents/incident_05_replication.py` ·
  `build-kvstore/checkpoints/05-replication/{node.py,coordinator.py}`
- [red-first walkthrough & honest incident messages](2026-06-24_red-first-walkthrough-and-honest-incident-messages.md) ·
  [validate ladder](2026-06-15_build-kvstore-validate-ladder.md)
