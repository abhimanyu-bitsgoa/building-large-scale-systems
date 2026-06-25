# 2026-06-25 — build-kvstore: per-service tmux lab, full diff narrative, and leaner code gaps

## Context

The `build-kvstore/` workshop was functionally complete and self-validating (see the
2026-06-14/15 decisions), but three pieces of "optional polish" stood between it and a smooth
live EuroPython delivery. Acting on a review of the workshop's delivery risk, the speaker asked
for three concrete changes:

1. **Finish tmux for the cluster stages (05–10)** so attendees *observe* every service they work
   with — each in its own pane — and can **play** with the running system (notably **kill/spawn**
   nodes) directly, not only via the incident-checker scripts. All tmux in mouse mode.
2. **Write the `docs/diffs/` chapter explainers** — and beyond the two chunky chapter boundaries,
   explain *every* stage transition so the build reads as one continuous narrative arc.
3. **Shrink the code-gap exercises to their conceptual core** so attendees write as little code as
   possible (just the idea, not the boilerplate).

This file documents all three, plus an environmental issue surfaced during verification.

## 1. Per-process tmux "lab" dashboard (`make lab STAGE=NN`, stages 00–10)

### What changed
- New `build-kvstore/tools/tmux_lab.sh <NN>` for **every** stage (00–10). It lays out **one pane
  per process** the stage runs — the node(s) on 00–04, or registry / coordinator / gateway on
  05–10 — starts them in dependency order, and adds three more panes: a **control** pane (the
  "play" surface), an **incident** pane (pre-typed `make incident STAGE=NN`, not fired), and a
  **scratch** shell. Mouse mode on; pane identities shown in the border titles. (It originally
  shipped for 05–10; extended to 00–04 the same day so `make lab` is a single, consistent verb for
  the whole workshop — one window, every stage.)
- New `build-kvstore/tools/kvplay.sh` — sourced into the control pane, with a `$TIER` switch:
  - **node tier (00–04):** `nwrite`, `nread`, `nhealth` (talk to the node's `/data` API), and
    `nload [strategy] [reqs] [conc]` to fire client-side load across all nodes (so 02/03 can
    compare `adaptive` vs `round_robin` routing live).
  - **cluster tier (05–10):** `kvwrite`, `kvread`, `kvstatus`, **`kvkill <n>`** (crash follower-n),
    **`kvspawn`** (respawn + catchup on 09/10). Two URLs via env: `WR_URL` (data path — gateway on
    stage 10, coordinator otherwise) and `ADMIN_URL` (kill/spawn/status — always the coordinator).
    The kill/spawn interface mirrors the `labs/` READMEs (`POST /kill/follower-N`, `POST /spawn`,
    `GET /status` on `:7000`).
- `Makefile` gains a `lab` target and help text.
- Removed `tools/tmux_stage10.sh` — its stage-10 layout is the `N==10` case of the general
  `tmux_lab.sh`, so keeping both would be duplicated, drift-prone code.

### Why this design
- **The observe pedagogy needs separate panes.** `make up` backgrounds every service into one
  shell, so for the cluster stages you can't *watch* replication acks, quorum decisions, heartbeats
  or deaths as they happen. One pane per service makes the distributed behavior visible — which is
  the entire point of these stages.
- **Play, not just check.** A black-box incident script prints a verdict; it doesn't let a learner
  *feel* the system. `kvkill`/`kvspawn` let attendees crash a follower and watch the coordinator
  and registry react, then bring it back and watch catchup — the kinesthetic loop the incidents
  can't give. The incident pane is still right there for the graded check.
- **Non-destructive.** `tmux_lab.sh` does **not** reset `kvstore/` if it already exists, so it
  never wipes a code-stage (05/08) solution. It only seeds (from the stage checkpoint) when
  `kvstore/` is empty. Attendees load the stage first with `make reset`/`make gap`.

### Constraint honored
- The leader and followers are **child subprocesses the coordinator spawns**, so their stdout is
  inherited by the coordinator's pane — they cannot get their own panes without invasively
  rerouting their I/O. The coordinator pane is labelled to make this explicit.
- `tools/up.sh` is untouched, so `validate_ladder.sh` (which drives `up.sh`) is unaffected.

### Alternatives considered
- **Extend `tmux_incident.sh` instead of a new script.** Rejected: that script's value is the
  simple "servers in one pane + incident" view (still ideal for the single-node stages 00–04). The
  cluster stages want a different, richer per-service layout; conflating them would muddy both.
  `tmux_lab.sh` now owns 05–10; `tmux_incident.sh` is pointed at 00–04.
- **Give leader/followers their own panes** by having the coordinator write each child's logs to a
  FIFO/file and `tail` them in panes. Rejected as too invasive for a teaching aid and a drift risk
  against the real spawn path.

### Verified
Built both the smallest cluster layout (07: coordinator-only) and the largest (10: registry +
coordinator + gateway) detached inside the container: correct panes, all ports bound, all
followers alive. Exercised the play helpers against a live cluster — `kvwrite`/`kvread` (quorum
visible in the JSON), `kvkill 1` (crash) → `kvspawn` (revive) all worked; stage-10 writes correctly
routed through the gateway (`:8000`).

## 2. `docs/diffs/` — the build as one narrative arc

### What changed
- `docs/diffs/README.md` — the master narrative: every transition 00→10 with **what the diff is**
  (files added/changed/removed) and **why** (the problem it solves), an ASCII map of the arc, and a
  one-paragraph summary. It explicitly calls out the **"subtraction artifact"** that the load
  balancer and rate limiter *leave* at stage 05 and *return* at stage 10 — because in the single-
  node era those are node concerns, and in the cluster era they belong on the edge gateway.
- `docs/diffs/04-to-05-replication.md` — deep-dive on **Chapter 1** (single node → replicated
  cluster): what `coordinator.py` is and why, how `node.py` grows a leader/follower role, why the
  edge files leave, and the single core line the attendee writes.
- `docs/diffs/07-to-08-discovery.md` — deep-dive on **Chapter 2** (the cluster learns who's alive):
  `registry.py` + heartbeats, `catchup.py`, the node/coordinator changes, the BUG-2 design note on
  why catchup is coordinator-driven, and the single core line.

### Why
The review's sharpest pedagogy concern was that the two big boundaries (04→05, 07→08) feel like
*rewrites* mid-workshop, breaking the "one earned step at a time" promise, and that the diffs were
never explained. Documenting *all* transitions (not just the two boundaries) turns the eleven
checkpoints into a readable story and gives the speaker ready-made narration for each step.

### Sourcing
Diffs were derived directly from `diff -rq` between consecutive checkpoints and from endpoint/def
inventories of the changed files, so the prose matches the actual code (e.g. the no-code-change
stages 05→06, 06→07, 08→09 are documented as config flips, which the file diffs confirm).

## 3. Leaner code-gap exercises (stages 04, 05, 08)

### What changed — only the gapped `stages/`; checkpoints (answer keys) untouched
- **04 `rate_limiter.py` `is_allowed`:** pre-filled the response-metadata dict and the
  return; the attendee now writes only the two-line fixed-window core (reset-on-expiry + allow/
  reject). The metadata is purely cosmetic (response headers), so pre-filling it removes noise
  without removing the lesson.
- **05 `node.py` `replicate_to_follower`:** pre-filled the `try/except`, the HTTP-200 handling, the
  logging and the counter; the attendee writes only the single `requests.post(... /replicate ...)`
  — the line that *is* replication.
- **08 `node.py` `heartbeat_loop`:** pre-filled the `while running:` loop, the `try/except` and the
  `time.sleep(interval)` pacing; the attendee writes only the single `requests.post(... /heartbeat
  ...)`. The placeholder `raise` sits inside the pre-filled `try`, so a gapped node simply sends no
  heartbeat (registry stays blind) rather than crashing — which is exactly the RED behavior INC-08
  needs.
- **03** was already a one-liner (`min(nodes, key=...)`), so it was left as-is.

### Why
For a 3-hour, mixed-skill, BYO-laptop tutorial, asking attendees to type boilerplate (metadata
dicts, try/except scaffolds, loops, logging) is where time and morale are lost to syntax rabbit
holes — and it buries the one idea each stage is meant to teach. Reducing each gap to its single
conceptual core keeps the learning on *distributed-systems reasoning*, not Python plumbing, and
keeps the room moving together.

### Risk + how it was retired
The danger of restructuring a gap is breaking the ladder invariant (gap must be RED, checkpoint
GREEN) or making the gap unsolvable with the intended minimal edit. Both were checked:
- `make validate` (full ladder): **20/20** — every reduced gap still fails its incident (RED) and
  every checkpoint still passes (GREEN).
- **Solvability:** applied the intended minimal one-line fill to each reduced gap and ran the
  incident — 04, 05 and 08 each go **GREEN**. So the core line the attendee writes is sufficient.

## Side effect surfaced during verification — zombie accumulation (FIXED: `init: true`)

Repeatedly spawning clusters during testing accumulated ~1000 **zombie** (`<defunct>`) python
processes, eventually causing `fork()`/exec hangs in the container. Root cause: the container's
PID 1 was `tail -f /dev/null` (from `docker-compose`), which never **reaps** orphaned children.
When the coordinator is `kill -9`'d (as `make down`/cleanup does), the leader/follower subprocesses
it spawned reparent to PID 1 and, on exit, become unreaped zombies. `tools/down.sh` kills by script
name and by port but cannot clear zombies (they hold no port and are already dead).

- **Impact on the workshop:** a single attendee doing many `up`/`down` (or `make lab`) cycles over
  3 hours could, in the worst case, approach the PID limit. The validate suite alone spawns ~40
  node processes per run.
- **Fix applied:** added `init: true` to the `workshop` service in `docker-compose.yml`. Docker
  inserts a tiny init (`/sbin/docker-init`, i.e. tini) as PID 1 that reaps orphans automatically.
  Verified: PID 1 is now `docker-init -- tail -f /dev/null`, and an orphan-fork test leaves **0**
  zombies (it left a growing pile before). **Requires `docker-compose up -d` to recreate the
  container** for the change to take effect.
- **Workaround if it ever recurs (e.g. an old container):** `docker-compose restart workshop`.

This was inherent to the spawn-subprocess + `tail`-as-PID-1 setup and predated this change; it is
now closed.

## Files touched
- New: `build-kvstore/tools/tmux_lab.sh`, `build-kvstore/tools/kvplay.sh`,
  `build-kvstore/docs/diffs/README.md`, `build-kvstore/docs/diffs/04-to-05-replication.md`,
  `build-kvstore/docs/diffs/07-to-08-discovery.md`.
- Removed: `build-kvstore/tools/tmux_stage10.sh`.
- Edited: `docker-compose.yml` (`init: true`), `build-kvstore/Makefile` (lab target+help),
  `build-kvstore/stages/04-rate-limit/rate_limiter.py`, `build-kvstore/stages/05-replication/
  node.py`, `build-kvstore/stages/08-discovery/node.py`, `build-kvstore/docs/stages.md`,
  `build-kvstore/README.md`, `build-kvstore/SPEC.md`.
