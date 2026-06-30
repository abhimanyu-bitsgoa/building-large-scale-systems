# 2026-07-01 — Give stage 05 its own lesson: the deterministic stale read (replication narrative)

**Status:** accepted
**Scope:** docs only — `build-kvstore/LAB-MANUAL.md`, `build-kvstore/docs/stages.md`. No code,
config, incident, checkpoint, or stage-numbering changes.

## Context

The replication arc is taught across three stages whose **code is byte-identical** — `node.py` and
`coordinator.py` are the same file in `checkpoints/05`, `06`, and `07`. The only thing that differs
between the three is the launch config in `tools/up.sh`:

- **05** — `W=1, R=1` (weak quorum) + the student code gap (`replicate_to_follower`)
- **06** — `W=3, R=1` (all followers sync — fresh reads, zero fault tolerance)
- **07** — `W=2, R=2` (majority quorum, `W + R > N` — fresh *and* fault-tolerant)

The instructor's concern (the trigger for this change): **stage 05 felt like it "did nothing"** that
stage 06 didn't — the student implements one function, and the stage's only distinct payoff (per the
manual) was "data is now readable from a replica," which is thin enough to blur into stage 06.

Two framings were on the table.

## Alternatives considered

**A. Merge 05 into 06 (two stages instead of three).** Lead with strong consistency (replicate to
*all*, `W=N`), reveal it's brittle, then stage 07 introduces quorum. Pro: removes the
"identical-code, flag-flip" redundancy; each remaining stage carries a genuine conceptual leap. Con:
the merged stage carries both the code task *and* the consistency trade-off (denser to land live);
requires renumbering 07→06, 08→07, … across `Makefile`, `up.sh`, `tmux_lab.sh`, `incidents/`,
`checkpoints/`, and every doc — broad, mechanical churn and risk.

**B. Keep three stages, but give stage 05 a distinct, observable lesson (chosen).** Stage 05 owns
the **stale read**; stage 06 *fixes* it (all-sync); stage 07 finds the middle (quorum). A stage in a
live workshop is justified by a distinct *aha*, not by distinct code — and the weak-quorum config
stage 05 already runs makes a stale read directly demonstrable. This is the existing on-disk arc;
it was simply under-narrated.

We chose **B**. The deciding point: in a teaching context the redundancy that motivated A is a
*narrative* gap, not a *structural* one. Filling it (B) is lower-risk (docs only, no renumber) and
yields a clean pendulum — weak/stale (05) → all-sync/brittle (06) → quorum/balanced (07) — where each
stage has one sharp beat with room to dwell.

## Why the stage-05 stale-read demo is reliable (verified in code, not assumed)

The demo only works if a read at `R=1` is *guaranteed* to land on a lagging follower. It is, by
construction, in `coordinator.py`:

- `get_sync_followers()` = the **smallest** `W` ports → at `W=1`, the single sync follower
  (replicates in `SYNC_REPLICATION_DELAY = 0.5s`).
- `get_read_followers()` = the **largest** `R` ports → at `R=1`, the highest-port follower.
- With `N=3`, smallest-port ≠ largest-port, and the largest-port follower is **async**
  (`ASYNC_REPLICATION_DELAY = 5.0s`).

So the write set (smallest 1) and read set (largest 1) are **disjoint** (`W + R = 2 ≤ N = 3`): a
write acks off the sync follower in ~0.5s while the read deterministically targets an async follower
that is ~5s behind. The stale read is reproducible, not a race — the only requirement is to read
*within* the ~5s lag window. This matches the canonical rule in the root `CLAUDE.md`: stale reads
happen exactly when `W + R ≤ N`.

The stage-06 brittleness cliffhanger (`kvkill 1` → write `503`) is likewise verified: at `W=3, N=3`,
`can_write()` requires `alive_followers >= 3`; killing one drops it to 2 and writes are refused.
Stage 06 has no registry/auto-spawn, so the dead follower stays dead and the 503 persists. Control-
pane helpers used in the demos (`kvwrite`, `kvread`, `kvkill`) are defined in `tools/tmux_lab.sh`.

## What changed

- **`LAB-MANUAL.md` stage 05** — after the existing green ("data readable from a replica"), added
  *The win* (replication buys read availability + read-throughput; writes still go through the
  leader — deliberately *not* claiming write-throughput gains) and *The twist* — a hands-on
  write→wait→update→immediate-read sequence that surfaces the stale read, with the mechanism
  (`W+R ≤ N`, async read-follower) and the "read promptly, it catches up in ~5s" caveat.
- **`LAB-MANUAL.md` stage 06** — re-led the section as "you just watched a stale read in 05; now turn
  the knob the other way," and turned the brittleness note into a *live* `kvkill 1` → `503` demo.
- **`LAB-MANUAL.md` ladder table** — stage 05 row now reads "single-leader replication — and the
  stale reads a weak quorum can serve."
- **`docs/stages.md`** — stage 05 gains a "Then observe (the hook into 06)" line describing the
  deterministic stale read; stage 06's incident line now references the stale read "from stage 05"
  for continuity.

## Side effects / risks

- **None to running behavior** — no `.py`/`.sh`/config/checkpoint touched, so the assessment ladder
  is unaffected. `make validate` was therefore **not** run (it exercises code/config, not prose; and
  per project notes the foreground run is flaky and can leave orphan clusters). Correctness of the
  documented demos was instead verified by reading the coordinator's quorum/selection logic (above).
- **Live-demo timing** is the one thing the instructor must respect: read within the ~5s async
  window, or the follower has caught up and the stale read won't show. The manual now states this.
- **Throughput framing** was deliberately scoped to *reads* to avoid the common (incorrect) "more
  replicas = more write throughput" claim a sharp attendee would challenge.
