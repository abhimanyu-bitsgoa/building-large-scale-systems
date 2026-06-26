# Build a Distributed Key-Value Store — Lab Manual

Welcome! Over this workshop you'll build a distributed key-value store from scratch — starting from a
single Python `dict` behind HTTP and growing it, one step at a time, into a fault-tolerant cluster
with replication, tunable read/write quorums, a rate-limited gateway, service discovery, and
automatic recovery. You'll break it on purpose at every step and watch how each new feature fixes it.

No prior distributed-systems experience is needed. You only need to be comfortable reading Python and
running commands in a terminal.

## The ladder

Each stage adds one idea. You don't have to finish all of them — every stage stands on its own.

| # | Stage | What you learn |
|---|---|---|
| 00 | single node | a KV store is a dict behind HTTP |
| 01 | vertical scaling | one process has a hard ceiling (the GIL) |
| 02 | horizontal scaling | many nodes, and why naive copies diverge |
| 03 | load balancing | round-robin vs. capacity-aware routing |
| 04 | rate limiting | protecting a node from floods |
| 05 | replication | single-leader replication |
| 06 | synchronous replication | all followers sync → no stale reads |
| 07 | quorum & fault tolerance | majority quorum (`W + R > N`) + the CAP trade-off |
| 08 | service discovery | heartbeats that detect death |
| 09 | auto-recovery | respawn + catch-up |
| 10 | full system | the whole thing, with an edge gateway (demo) |

Stages **03, 04, 05, 08** ask you to write one line of code. The rest are run-and-observe or a small
config change.

---

## Setup

Everything runs inside a Docker container, so nothing touches your machine's ports. Run these from the
workshop folder.

Build and start the container:

```
docker compose up -d
```

Open a shell inside it:

```
docker compose exec workshop bash
```

Everything below runs **inside that shell**. Seed your working copy from the starting checkpoint (do
this once):

```
make start
```

---

## How a stage works

Every stage follows the same loop: **start the system → run the incident and watch it fail → make
the change → run the incident again and watch it pass.**

Start the system for a stage (this one keeps running, so leave it in its own shell):

```
make up STAGE=03
```

Open a **second** shell into the container so you can interact while the system runs:

```
docker compose exec workshop bash
```

Run the stage's incident — a small script that checks for the problem this stage fixes:

```
make incident STAGE=03
```

The first run is expected to **fail** (that's the problem). After you make the stage's change, run the
same command again and it should **pass**.

If you fall behind or want the worked solution for a stage, reset your working copy to a known-good
version:

```
make reset STAGE=03
```

See your progress so far:

```
make status
```

When you move to a different stage, stop the previous one first:

```
make down
```

---

## Stage 00 — A single node

A key-value store in its purest form: a Python `dict` behind two HTTP routes, `POST /data` and
`GET /data/{key}`.

Start it:

```
make up STAGE=00
```

In your second shell, confirm a write-then-read round-trip works:

```
make incident STAGE=00
```

## Stage 01 — Vertical scaling

One process can only do so much. Python runs your handler on a single thread (the GIL), so under
concurrent load latency climbs. The fix is to run more worker processes.

Start the node with multiple workers:

```
make up STAGE=01
```

Run the incident — with enough workers, latency stays low:

```
make incident STAGE=01
```

To *feel* the single-thread ceiling, stop it, then start it again pinned to one worker and re-run the
incident — latency spikes:

```
WORKERS=1 make up STAGE=01
```

## Stage 02 — Horizontal scaling

One box is a single point of failure and a capacity wall. So we run three nodes and have the client
spread requests across them — by **naive round-robin**, with no load balancer yet.

Start three nodes:

```
make up STAGE=02
```

Run the incident — load is now served across the cluster:

```
make incident STAGE=02
```

Note the catch: the three nodes have **separate** dicts, so the data is split across them. That's what
motivates replication later. And round-robin is blind to how busy each node is — which motivates the
load balancer next.

## Stage 03 — Load balancing ⌨️

Round-robin sends an equal share to every node, even a slow one, so the slow node drags your
tail latency. You'll implement a **capacity-aware** strategy that prefers the least-loaded node.

Load the starting point for this code stage:

```
make gap STAGE=03
```

Open `kvstore/load_balancer.py` and complete `AdaptiveStrategy.get_node` — return the node with the
lowest load score (one line). Then start the system:

```
make up STAGE=03
```

Run the incident — the adaptive strategy should beat round-robin on tail latency:

```
make incident STAGE=03
```

## Stage 04 — Rate limiting ⌨️

Load balancing shares load; it doesn't *cap* it. A burst can still overwhelm a node. You'll implement
a fixed-window limiter that sheds excess requests.

Load the starting point:

```
make gap STAGE=04
```

Open `kvstore/rate_limiter.py` and complete the core of `FixedWindowStrategy.is_allowed` — reset the
counter when the window rolls over, allow while under the limit, reject once it's hit. Then start it:

```
make up STAGE=04
```

Run the incident — requests over the limit now come back as `429`:

```
make incident STAGE=04
```

## Stage 05 — Replication ⌨️

From here we become a real cluster: one **leader** plus **followers**, coordinated by a `coordinator`
service. Reads are served from the followers, so a write that never reaches them is stranded. You'll
implement the replication call.

Load the starting point:

```
make gap STAGE=05
```

Open `kvstore/node.py` and complete `replicate_to_follower` — `POST` the write to the follower's
`/replicate` route. Then start the cluster:

```
make up STAGE=05
```

Run the incident — a value written via the coordinator can now be read back from the replicas:

```
make incident STAGE=05
```

## Stage 06 — Synchronous replication

In stage 05 some followers replicate asynchronously, so a read right after a write can land on a
follower that hasn't caught up yet — a **stale** read. The fix: make **every** follower synchronous,
so a write reaches all of them before it returns. This stage just changes the quorum config (`W = N`).

Start the cluster in all-sync mode:

```
make up STAGE=06
```

Run the incident — an immediate read after an update is always fresh:

```
make incident STAGE=06
```

The cost: a write now needs *every* follower alive. That's the problem the next stage solves.

## Stage 07 — Quorum & fault tolerance

All-sync gives fresh reads but tolerates **zero** failures — kill one follower and writes stop. The
sweet spot is a **majority quorum** (`W = 2, R = 2` with `N = 3`): it survives one follower failure
*and* keeps `W + R > N`, so reads stay fresh. When the quorum is lost, the system refuses writes to
preserve consistency — the CAP trade-off, made visible.

Start the cluster with a majority quorum:

```
make up STAGE=07
```

Run the incident — writes survive a follower failure:

```
make incident STAGE=07
```

## Stage 08 — Service discovery ⌨️

The cluster can't recover from a death it never notices. A **registry** service tracks which nodes are
alive via heartbeats. You'll implement the heartbeat each node sends.

Load the starting point:

```
make gap STAGE=08
```

Open `kvstore/node.py` and complete `heartbeat_loop` — `POST` the node's identity to the registry's
`/heartbeat` route on each interval. Then start it:

```
make up STAGE=08
```

Run the incident — a killed follower is now detected as dead within the heartbeat timeout:

```
make incident STAGE=08
```

## Stage 09 — Auto-recovery

Detecting death just gives you an accurate map of the damage; the cluster still runs degraded. With
auto-spawn enabled, a follower that stops heartbeating is **respawned**, and the coordinator **catches
it up** from the leader's snapshot. This stage enables that with config.

Start the self-healing cluster:

```
make up STAGE=09
```

Run the incident — a killed follower is respawned and rejoins with the full dataset:

```
make incident STAGE=09
```

This is the cluster healing itself — the high point of what you build by hand.

## Stage 10 — The full system (demo)

Stage 10 puts an **edge gateway** in front of everything and ties the whole system together. There's
no exercise here — it's the synthesis of everything from stages 00–09, and the best way to experience
it is to drive it yourself in the lab dashboard (see below).

---

## Playing with the system

For any stage, you can launch a **dashboard**: every process gets its own pane, plus a control pane
where you type commands to drive the system by hand. Mouse mode is on — click a pane, scroll to read.

Launch the dashboard for a stage:

```
make lab STAGE=10
```

In the control pane, list the commands available for this stage:

```
kvhelp
```

On the cluster stages (05–10) you can, for example, write and read a key, check cluster status, flood
the edge to trigger rate limiting, and crash a follower to watch recovery:

```
kvwrite cart shoes
```

```
kvread cart
```

```
kvkill 1
```

When you're done, tear the dashboard down:

```
make lab-down
```

---

## Cheat sheet

Seed your working copy once:

```
make start
```

Start a stage's system:

```
make up STAGE=NN
```

Run a stage's check:

```
make incident STAGE=NN
```

Load the starting point for a code stage (03, 04, 05, 08):

```
make gap STAGE=NN
```

Restore the worked solution for a stage:

```
make reset STAGE=NN
```

Open the dashboard for a stage:

```
make lab STAGE=NN
```

Stop everything for the current stage:

```
make down
```

---

## If something breaks

Stop all workshop processes and start clean:

```
make down
```

If a dashboard session is still around, tear it down too:

```
make lab-down
```

If a stage won't start because a port is busy, it's almost always a leftover process from a previous
stage — `make down` clears it. When in doubt, restart the container:

```
docker compose restart
```
