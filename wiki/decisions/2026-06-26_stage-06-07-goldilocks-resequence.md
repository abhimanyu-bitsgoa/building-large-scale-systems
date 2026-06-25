# 2026-06-26 — Re-sequence stages 06/07 into a "Goldilocks" arc (all-sync → majority quorum)

## Context

The replication arc ran: 05 weak quorum (`W=1,R=1`, stale reads) → 06 quorum (`W=2,R=2`, "W+R>N
kills stale reads") → 07 fault tolerance (lower `W` from 3 to tolerate failures). Two problems with
this order, raised by the speaker:

1. **Stage 07's RED state was a contrived manual command.** To demonstrate the outage, stage 07 had
   the user hand-run `python coordinator.py --write-quorum 3 --read-quorum 2` — a `W=3` config that
   *appears nowhere else in the ladder*. It read as "type this odd command so it breaks," not as a
   natural consequence of the previous stage. (In `validate_ladder.sh` the INC-07 red was likewise a
   one-off `cmd:` override.)
2. **The arc didn't show a tradeoff at 06.** Stage 06 jumped straight to the "correct" `W=2,R=2`, so
   there was no felt cost to motivate 07 — 07 then introduced `W=3` only to walk it back.

## Decision — the Goldilocks arc

| Stage | Old config | New config | Story |
| --- | --- | --- | --- |
| 05 | `W=1,R=1` | `W=1,R=1` *(unchanged)* | **too weak** — stale reads, fragile single copy |
| 06 | `W=2,R=2` | **`W=3,R=1`** | **too strong** — *all followers synchronous*: reads always fresh (write to everyone ⇒ read anyone), but a write needs all 3 → **zero fault tolerance** |
| 07 | `W=2,R=2` | `W=2,R=2` *(config unchanged; framing + RED state changed)* | **just right** — majority quorum: survives `floor(N/2)` deaths AND `W+R>N` keeps reads fresh; the CAP tuning knob |

Now **stage 06's real config (`W=3`) IS stage 07's RED state** — no manual command. INC-07's "before"
is simply the previous stage, exactly like INC-06 red = stage 05 and INC-09 red = stage 08.

### Why `W=3, R=1` for stage 06 (not `R=3`)

The speaker floated `W=3, R=3`. Rejected: `R=3` means a read needs *all 3* followers alive, so after
INC-07 kills one, reads would **also** fail — destroying the "writes refused, **reads survive**" CAP
demonstration that is the point of stage 07. `R=1` also tells a cleaner story ("write to everyone ⇒
read from anyone") and makes 05→06 a clean single-knob change (just raise `W`).

This works because of how the coordinator picks nodes (verified by reading `coordinator.py`):
`get_sync_followers` = the **lowest** `W` ports; `get_read_followers` = the **highest** `R` ports —
picked from opposite ends so they only overlap when `W+R>N`. At `W=3` the sync set is *all*
followers, so any read (even `R=1`, the highest port) is current.

## Incident mechanics preserved

Only configs, framing, and the INC-07 red seed changed — **the incident logic is untouched**:

- **INC-06** stays the update-then-read staleness probe. RED at 05 (`W=1,R=1`); GREEN at 06
  (`W=3,R=1` — every follower synchronous). Docstring/messages reframed from "raise R until W+R>N"
  to "make every follower synchronous (raise W to N)".
- **INC-07** stays the kill-`floor(N/2)` + CAP probe. GREEN at `W=2,R=2`; RED now seeds **stage 06
  (`W=3`)** via `up:06` instead of the `cmd:` override. The W+R>N freshness rule and the staleness
  discussion (drop R→1 and stale reads return) now live in stage 07, where "quorum" is taught — this
  is the "show staleness in the quorum" the speaker asked for.

## Verification

`make validate` re-run → expect **20/20**. The discriminators:
- INC-06: green `up:06` (`W=3,R=1`), red `up:05` (`W=1,R=1`).
- INC-07: green `up:07` (`W=2,R=2`), red `up:06` (`W=3,R=1`) — kill 1 of 3 → writes need 3, only 2
  alive → 503 (red); reads (`R=1`) still served by the 2 survivors.

## Relationship to prior decisions

Supersedes the *framing* (not the mechanics) of:
- `2026-06-25_incident-06-update-then-read-staleness.md` — the update-then-read probe is kept; its
  stage now teaches "all followers synchronous" rather than "W+R>N" (that rule moves to 07).
- `2026-06-25_incident-07-cap-tradeoff-and-06-07-connection.md` — the CAP probe is kept; its RED
  state is now stage 06's genuine config instead of a manual `W=3` command, and the 06→07 connection
  is reframed as all-sync (brittle) → majority quorum (fault-tolerant + fresh).

## Files touched
- Edited: `build-kvstore/tools/up.sh` (split 06/07: `W=3,R=1` and `W=2,R=2`),
  `build-kvstore/tools/validate_ladder.sh` (INC-07 red → `up:06`),
  `build-kvstore/tools/tmux_lab.sh` (stage-06 `W=3,R=1` + coordinator pane label),
  `build-kvstore/incidents/incident_06_stale.py` (reframe),
  `build-kvstore/incidents/incident_07_outage.py` (reframe docstring),
  `build-kvstore/docs/stages.md`, `build-kvstore/docs/diffs/README.md`,
  `build-kvstore/README.md`, `build-kvstore/SPEC.md`, `WORKSHOP-WALKTHROUGH.md`,
  `wiki/decisions/INDEX.md`.
