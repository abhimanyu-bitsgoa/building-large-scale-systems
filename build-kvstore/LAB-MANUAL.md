# Build a Distributed Key-Value Store — Lab Manual

Welcome! Over this workshop you'll build a distributed key-value store from scratch — starting from a
single Python `dict` behind HTTP and growing it, one step at a time, into a fault-tolerant cluster
with replication, tunable read/write quorums, a rate-limited gateway, service discovery, and
automatic recovery. At every stage you get a **live dashboard** to poke the system by hand and watch
it react.

No prior distributed-systems experience is needed — just comfort reading Python and running commands.

## The ladder

Each stage adds one idea. You don't have to finish all of them — every stage stands on its own.

| # | Stage | What you learn | You write code? |
|---|---|---|---|
| 01 | single node | a KV store is a dict behind HTTP | — |
| 02 | vertical scaling | one process has a hard ceiling (the GIL) | — |
| 03 | horizontal scaling + load balancing | many nodes (and why naive copies diverge), then round-robin vs. capacity-aware routing | ✏️ |
| 04 | rate limiting | protecting a node from floods | ✏️ |
| 05 | replication | single-leader replication — and the stale reads a weak quorum can serve | ✏️ |
| 06 | synchronous replication | all followers sync → no stale reads | — |
| 07 | quorum & fault tolerance | majority quorum (`W + R > N`) + CAP | — |
| 08 | service discovery | heartbeats that detect death | ✏️ |
| 09 | auto-recovery | respawn + catch-up | — |
| 10 | full system | the whole thing, with an edge gateway | — (demo) |

The four ✏️ stages ask you to write **one line** of code. The rest are run-and-explore.

---

## Setup

Everything runs inside a Docker container, so nothing touches your machine's ports. From the workshop
folder:

```bash
docker compose up -d                 # build + start the container (first run takes a few minutes)
docker compose exec workshop bash    # open a shell inside it — everything below runs in here
make start                           # seed your working copy (kvstore/) from the first checkpoint
```

---

## How a stage works

Every stage is the same three beats: **load it → explore it in the dashboard → check it.**

**1. Load the stage's code into your working copy (`kvstore/`).** Two commands do this:

```bash
make gap STAGE=NN      # the ✏️ code stages (03/04/05/08): loads the exercise with one blank function
make reset STAGE=NN    # any stage: loads the complete, working code (also your "rescue" button)
```

For the run-and-explore stages, `make lab` (below) loads the stage for you automatically — you only
need `make gap`/`make reset` by hand on the ✏️ code stages (or to rescue a stage you broke).

**2. Explore it — this is the main way to learn.** Open the live dashboard:

```bash
make lab STAGE=NN
```

This opens one window with several panes:
- **service panes** — every process the stage runs (the node(s), or registry / coordinator / gateway), so you can watch them react;
- a **control pane** — pre-loaded with helper commands so you drive the system by hand (it prints its own command list when it opens);
- an **incident pane** — the automated check, pre-typed and ready;
- a **scratch** pane — a free shell.

Mouse mode is on: click a pane to focus it, scroll to read history. Tear the dashboard down with
`make lab-down`.

**3. Check it.** In the **incident pane**, press **Enter** to run the stage's automated check — it
goes ❌ before the stage is solved and ✅ after. (Prefer plain shells? After loading the stage, run
`make up STAGE=NN` in one shell and `make incident STAGE=NN` in another.)

See your overall progress any time with `make status`.

---

## Stage 01 — A single node

A key-value store in its purest form: a Python `dict` behind two HTTP routes.

```bash
make lab STAGE=01        # loads stage 01 automatically + opens the dashboard
```

In the **control pane**, write and read a key:

```bash
nwrite cart shoes        # POST /data
nread cart               # GET /data/cart  → "shoes"
```

When you're ready, press **Enter** in the **incident pane** to confirm the round-trip works (✅).
Reload this stage by hand any time with `make reset STAGE=01`.

## Stage 02 — Vertical scaling

One process can only do so much: Python runs your handler on a single thread (the GIL), so under
concurrent load latency climbs. The fix is more worker processes.

```bash
make lab STAGE=02        # loads stage 02: a node with a CPU-load simulator, running 4 workers
```

The **incident pane** drives concurrent load and measures latency — press **Enter** there and note
the p95 with 4 workers (✅). To *feel* the single-thread ceiling, restart pinned to one worker and run
the check again:

```bash
make lab-down
WORKERS=1 make lab STAGE=02     # same check, one worker → latency spikes
```

(The control pane's `nwrite` / `nread` / `nhealth` confirm the node serves. Reload by hand:
`make reset STAGE=02`.)

## Stage 03 — Horizontal scaling + load balancing ✏️

One box is a single point of failure and a capacity wall, so we go wide: run **three** nodes and
spread requests across them. But the cluster is *heterogeneous* — one weak node (load 30, 1 worker)
and two strong ones (load 25, 4 workers) — and the simplest spread, **round-robin by turn**, is blind
to that. It bombards the weak node with its fair 1/3 share; the weak node queues and the tail latency
tanks. You'll fix it by implementing a **capacity-aware** strategy that prefers the least-loaded node.

```bash
make gap STAGE=03        # load the exercise: AdaptiveStrategy.get_node is left blank
make lab STAGE=03        # dashboard: 3 node panes (1 weak, 2 strong) + control + incident pane
```

In the control pane, watch round-robin punish the weak node (adaptive errors until you implement it):

```bash
nload round_robin 96 12  # blind 1/3 share lands on the weak node → bad global p95
nload adaptive 96 12     # (errors until you write the one line below)
nwrite a 1               # note: writes land on different nodes — the data is SPLIT across them
nread a                  #   (a key on node 1 isn't on node 2 — this is what motivates replication, stage 05)
```

Now implement it: open `kvstore/load_balancer.py` and complete **`AdaptiveStrategy.get_node`** —
return the node with the lowest load score (one line). Then restart so your change loads, and check:

```bash
make lab-down            # stop the lab so the edit is picked up
make lab STAGE=03        # your code is preserved; adaptive now steers around the weak node
```

Press **Enter** in the incident pane → ✅ (adaptive p95 clearly below round-robin p95). Stuck?
`make reset STAGE=03` loads the worked solution.

## Stage 04 — Rate limiting ✏️

Load balancing shares load; it doesn't *cap* it. A burst can still overwhelm a node. You'll implement
a fixed-window limiter that sheds excess requests.

```bash
make gap STAGE=04        # load the exercise: FixedWindowStrategy.is_allowed is left blank
make lab STAGE=04        # dashboard: the node + control + incident pane
```

In the control pane, flood the node past its limit and watch the responses (you'll see no `429`s
until you implement the limiter).

Now implement it: open `kvstore/rate_limiter.py` and complete the core of
**`FixedWindowStrategy.is_allowed`** — reset the counter when the window rolls over, allow while under
the limit, reject once it's hit. Then restart and check:

```bash
make lab-down
make lab STAGE=04        # requests over the limit now come back as 429
```

Press **Enter** in the incident pane → ✅. Rescue: `make reset STAGE=04`.

## Stage 05 — Replication ✏️

From here we become a real cluster: one **leader** plus **followers**, coordinated by a `coordinator`
service. Reads are served from the followers, so a write that never reaches them is stranded. You'll
implement the replication call.

```bash
make gap STAGE=05        # load the exercise: replicate_to_follower is left blank
make lab STAGE=05        # dashboard: coordinator pane (it spawns leader + followers) + control
```

In the control pane, drive the cluster (writes won't reach the read replicas until you implement
replication):

```bash
kvwrite order paid
kvstatus                 # leader + 3 followers
kvread order             # misses until replication works
```

Now implement it: open `kvstore/node.py` and complete **`replicate_to_follower`** — `POST` the write
to the follower's `/replicate` route and return success on `200`. Then restart and check:

```bash
make lab-down
make lab STAGE=05        # the write now reaches the replicas
```

Press **Enter** in the incident pane → ✅ (data readable from a replica).

**The win:** a write now lives on several nodes, so the cluster keeps serving reads even if a node
dies, and reads spread across the followers instead of hammering one box. (This buys read
availability and scales *read* throughput — writes still funnel through the leader.)

**Now the twist — stale reads.** This stage runs a **weak quorum** (`W = 1, R = 1`). A write returns
as soon as the *sync* follower acks (~0.5s), but a read at `R = 1` is served by a *different*
follower that replicates asynchronously (~5s behind the leader). The write set and read set don't
overlap (`W + R = 2 ≤ N = 3`), so for a few seconds after an update the read hands back the **old**
value. See it yourself:

```bash
kvwrite order paid       # write v1 — then wait ~5s so every follower (even the async one) has it
kvwrite order shipped    # UPDATE to v2 — the sync follower gets it fast, the async one lags
kvread order             # read immediately → "paid" (stale!); read again after ~5s → "shipped"
```

You're watching one follower lag behind the leader in real time. That fleeting wrong answer is
exactly what **stage 06** removes. Rescue: `make reset STAGE=05`.

## Stage 06 — Synchronous replication

You just watched a stale read in stage 05: at `W = 1, R = 1` the read lands on an async follower that
hasn't caught up. Now turn the knob the other way — make **every** follower synchronous (`W = N`), so
a write reaches all of them before it returns. No follower can lag, so no read is stale.

```bash
make lab STAGE=06        # loads stage 06 (all-sync W=3, R=1) + dashboard
```

In the control pane, update a key and read it back immediately — it's always fresh now:

```bash
kvwrite order paid
kvread order             # always the latest value
kvstatus
```

Press **Enter** in the incident pane → ✅ (no stale reads). But you've over-corrected: a write now
needs *every* follower alive. Prove it — kill one and watch writes stop:

```bash
kvkill 1                 # take down a follower
kvwrite order delivered  # → 503: the write can't reach all N followers anymore
```

Zero fault tolerance — the price of strong consistency. **Stage 07** finds the middle ground. Reload
by hand: `make reset STAGE=06`.

## Stage 07 — Quorum & fault tolerance

All-sync gives fresh reads but tolerates **zero** failures. The sweet spot is a **majority quorum**
(`W = 2, R = 2` with `N = 3`): it survives one follower failure *and* keeps `W + R > N`, so reads
stay fresh. When the quorum is lost, the system refuses writes to preserve consistency — the CAP
trade-off, made visible.

```bash
make lab STAGE=07        # loads stage 07 (majority quorum W=2, R=2) + dashboard
```

In the control pane, kill a follower and confirm writes still succeed:

```bash
kvwrite order paid
kvkill 1                 # crash one follower
kvstatus                 # one dead, but the quorum holds
kvwrite order shipped    # still works
kvread order             # still fresh
```

Press **Enter** in the incident pane → ✅ (writes survive a follower failure). Reload:
`make reset STAGE=07`.

## Stage 08 — Service discovery ✏️

The cluster can't recover from a death it never notices. A **registry** service tracks which nodes are
alive via heartbeats. You'll implement the heartbeat each node sends.

```bash
make gap STAGE=08        # load the exercise: heartbeat_loop is left blank
make lab STAGE=08        # dashboard: registry + coordinator panes + control
```

In the control pane, kill a follower and check the registry — without heartbeats it never even learns
the node existed, so it can't be marked dead:

```bash
kvkill 1
kvstatus
```

Now implement it: open `kvstore/node.py` and complete **`heartbeat_loop`** — `POST` the node's
identity (`node_id`, `port`, `url`, `role`) to the registry's `/heartbeat` route each interval. Then
restart and check:

```bash
make lab-down
make lab STAGE=08        # a killed follower is now detected as dead within the timeout
```

Press **Enter** in the incident pane → ✅. Rescue: `make reset STAGE=08`.

## Stage 09 — Auto-recovery

Detecting death just gives you an accurate map of the damage; the cluster still runs degraded. With
auto-spawn, a follower that stops heartbeating is **respawned**, and the coordinator **catches it up**
from the leader's snapshot.

```bash
make lab STAGE=09        # loads stage 09 (auto-spawn enabled) + dashboard
```

In the control pane, crash a follower and watch the cluster heal itself:

```bash
kvwrite order paid
kvkill 1                 # crash a follower
kvstatus                 # degraded...
# wait ~5s — the coordinator pane shows the respawn + catch-up
kvstatus                 # back to full strength
kvread order             # the revived node has the data
```

Press **Enter** in the incident pane → ✅ (respawned and caught up). This is the cluster healing
itself — the high point of what you build by hand. Reload: `make reset STAGE=09`.

## Stage 10 — The full system (demo)

Stage 10 puts an **edge gateway** in front of everything and ties the whole system together. There's
no exercise and no check here — it's the synthesis of stages 01–09, and the way to experience it is
to drive it yourself.

```bash
make lab STAGE=10        # registry + coordinator + gateway panes + control
```

In the control pane, take the whole system for a spin:

```bash
kvwrite cart shoes       # trace it: gateway (:8000) → coordinator (:7000) → leader → followers
kvread cart
kvflood 15               # hammer the edge — the rate limiter sheds the overflow as 429s
kvwrite order paid
kvkill 1                 # crash a follower — quorum holds, then it auto-respawns and catches up
kvread order             # still fresh
```

Tear it down with `make lab-down`.

---

## Cheat sheet

```bash
make start               # seed your working copy (once, at the very beginning)
make gap STAGE=NN        # load a ✏️ code stage's exercise (03/04/05/08)
make reset STAGE=NN      # load a stage's complete, working code (also the rescue button)
make lab STAGE=NN        # the dashboard: explore the stage by hand (loads non-code stages for you)
make lab-down            # tear the dashboard down
make incident STAGE=NN   # run a stage's check on its own (or just press Enter in the lab's incident pane)
make status              # show your progress across the ladder
```

The typical loop: **code stage** → `make gap` → `make lab` → edit the one function → `make lab-down`,
`make lab` → press Enter in the incident pane. **Run-and-explore stage** → `make lab` → poke it →
press Enter in the incident pane.

---

## If something breaks

```bash
make lab-down            # tear down the dashboard + all its processes
make down                # stop any stray workshop processes
docker compose restart   # last resort: restart the whole container
```

If a stage won't start because a port is busy, it's almost always a leftover process from a previous
stage — `make lab-down` (or `make down`) clears it. If you've tangled up a stage's code, jump back to
a known-good state with `make reset STAGE=NN`.

### Windows: `make lab` fails with "invalid option name: pipefail"

This is a line-endings mismatch. Windows Git rewrites files with CRLF (`\r\n`) on clone; the Linux
container's `bash` then sees a trailing `\r` on every line and rejects it as an unknown option.

The repo ships a `.gitattributes` that forces LF on checkout, so this should not happen on a fresh
clone. If you cloned before that file was in the repo (or your Git ignored it), fix it once inside
the container:

```bash
find /workspace -name '*.sh' | xargs dos2unix
```

Then re-run your `make` command — it will work.

If you want a permanent fix so you never have to run this again on future pulls — run these on your
**Windows machine** (not inside the container), after pulling the `.gitattributes` commit:

```bash
git pull                   # get the .gitattributes commit if you haven't already
git rm --cached -r .       # wipe Git's index so it re-reads every file
git reset --hard           # re-checkout everything, now normalized to LF
```

This makes Git on Windows permanently honour the repo's LF policy for every future pull.
