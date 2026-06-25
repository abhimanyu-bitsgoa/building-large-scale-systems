# Optional tmux stage-10 dashboard (one component per pane)

- **Date:** 2026-06-25
- **Status:** accepted
- **Change / commit(s):** branch `europython-lab-design` — adds one new file, modifies nothing else.

## Context

The core workshop hides the multi-process startup behind a single `make up STAGE=NN`
(see `tools/up.sh`). For stage 10 that one command fans out into ~6 processes — registry,
coordinator (which itself spawns leader + 3 followers), and gateway — but the attendee sees only
the gateway's foreground log. This is the right default for a paced, low-friction workshop, but it
costs *component appreciation*: you don't viscerally see that these are separate services talking
over HTTP.

We wanted an **optional** way to surface the full topology — one component per terminal — without
touching the validated core flow.

## Decision

Add a single standalone script `tools/tmux_stage10.sh` that lays stage 10 out in a tiled tmux
session with five panes: **registry**, **coordinator**, **gateway**, an interactive **client**,
and a free **scratch** shell. Each pane's border is titled with the component + its port.

Design constraints honoured:

- **Modifies nothing.** It is not wired into the Makefile, up.sh, down.sh or the walkthrough.
  Removing the feature = deleting this one file (grep `tmux_stage10`).
- **Reuses the known-good launch commands** copied verbatim from `up.sh`'s stage-10 block, and
  reuses `tools/down.sh` for teardown — so it can't drift from the real workshop behaviour.
- **Stable pane IDs** (`#{pane_id}`, captured at split time) instead of positional indexes, which
  renumber unpredictably.
- **Re-tiles after every split** to avoid tmux's "no space for new pane" error on small terminals.
- **Dependency-ordered startup** (registry → coordinator → gateway) with short waits between, the
  same ordering `up.sh` uses.
- **Mouse mode on** (`set -g mouse on`) so you click a pane to focus it — far friendlier than the
  `Ctrl-b` prefix for tmux newcomers. (macOS: hold Option/Alt to drag-select text for copy.)
- `down` subcommand: `bash tools/tmux_stage10.sh down` kills the session and all processes.

## How to use it in the workshop (important)

This is an **instructor / projector** tool, not a mandatory attendee step:

- **Instructor demo → use tmux.** One controlled machine, big screen, rehearsed: the 5-pane
  reveal is a great ~2-minute "watch the whole system breathe" moment.
- **Attendees → keep the default `make up STAGE=10` + `curl :7000/status` reveal.** It renders
  identically on every host terminal and has zero tmux friction. Offer the dashboard to attendees
  only as an *optional* extra.
- **Why not mandatory for the room:** tmux itself is uniform (it runs inside the container, so
  version/availability are identical for everyone), but it renders to the *host* terminal — so on
  small laptop screens 5 panes get cramped, and the `Ctrl-b` prefix trips up newcomers. Manual
  "start 5 components in 5 terminals" is worse still (more error-prone than the script). So the
  per-component view is opt-in, with the simple single-log flow remaining the default path.

## Alternatives considered

- **Rebuild the whole workshop run model around tmux.** Rejected — highest risk, would require
  re-rehearsing all 11 stages, and the abstraction is partly load-bearing for a paced room (see
  the discussion that led here). This script is the opt-in version that leaves the core intact.
- **Wire it into the Makefile (`make dashboard`).** Rejected for now — the user explicitly wanted
  it separate and easy to discard. Can be added later if it proves useful.
- **Positional pane indexes + single final `tiled`.** Rejected — both are fragile: indexes
  renumber, and a single late tile hits "no space for new pane" at 80×24.

## Side effects & risks

- **Re-seeds `kvstore/` from `checkpoints/10-*`** on launch. Safe because the capstone is
  config-only (you tune `student_config.json`, you don't edit code), so there is no student code
  in `kvstore/` to lose at stage 10.
- Don't run `assessment.py` at the same time — it spins up its own cluster on the same ports.
- The leader + followers are coordinator child processes, so their logs appear in the
  *coordinator* pane (not separate panes). This is inherent to the coordinator-spawns-nodes
  design and is called out in the script header.

## Verification

Tested headlessly inside the container (tmux 3.4):

- Pane construction builds 5 correctly-titled panes even at the default 80×24 (after adding the
  re-tile-per-split fix; the naive version failed with "no space for new pane").
- Full bring-up via the real service commands: all 7 ports bound (9000, 7000, 7001, 7002, 7003,
  7004, 8000), `/status` reported leader + 3 followers with `W=2, R=2, can_write=true`, and the
  registry/coordinator/gateway panes showed healthy output (no tracebacks; gateway `200 OK`).
- `bash -n` syntax check passes; teardown releases all ports and the session.

## Follow-up (same day): generic per-incident dashboard — `tools/tmux_incident.sh`

The stage-10 script shows the *components*, but the more common need is to **watch the servers
react while an incident runs** — an incident script is only a thin HTTP client that prints a
verdict; the real drama (replication acks, quorum decisions, heartbeats, respawns) is in the
server logs. Added a second standalone script `tools/tmux_incident.sh <NN>` for *any* stage:

- **3 panes, `main-vertical`:** a big left **servers** pane running `make up STAGE=NN`, plus
  **incident** (pre-typed `make incident STAGE=NN`, fired on Enter so the instructor controls
  timing) and **scratch**.
- **DRY / no drift:** it shells out to `make up` and `make incident` verbatim — no copied launch
  commands, works for every stage 00–10.
- **Does NOT reset `kvstore/`** (unlike the stage-10 script) so it never wipes a code-stage
  solution; the header tells you to `make reset`/`make gap` first as appropriate.
- Same conventions as the stage-10 script: stable pane IDs, re-tile-per-split, mouse mode on,
  `down` subcommand, single-file/disposable.

Verified headless on stage 05: 3 panes built, the servers pane showed the live replication trail
(`Sync followers`, `Leader: written (v1)`, `follower-1: sync ack received`, `QUORUM MET`,
`Async replication queued`) in response to the incident's write, and teardown released all ports.

**Workshop guidance applies to both scripts:** instructor/projector tool, not a mandatory attendee
step (see "How to use it in the workshop" above).

## References

- `build-kvstore/tools/tmux_stage10.sh` (per-component view) ·
  `build-kvstore/tools/tmux_incident.sh` (per-incident "watch the servers react" view)
- `build-kvstore/tools/up.sh` (stage-10 block — source of the launch commands) ·
  `build-kvstore/tools/down.sh` (reused for teardown)
