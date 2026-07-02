# Workshop Walkthrough — Build-a-KVStore

The complete guide to running the **Building Large Scale Systems** tutorial, for both the
**instructor** (you, running the room) and the **attendees** (following along). It covers
setup, the run model, every stage, the finale demo, and what to do when things go wrong.

> **What attendees build:** starting from a single in-memory dict behind HTTP, they grow a
> distributed key-value store — single-leader replication and snapshot resync *like Redis*,
> tunable read/write quorums *like Dynamo* — and watch it survive failures injected at each
> step. The system is built in **10 stages (01 → 10)**, each motivated by an **incident** that
> breaks the previous version and only passes once the next feature is added.

The primary workshop lives in [`build-kvstore/`](build-kvstore/). The original three labs under
[`labs/`](labs/) remain as a standalone reference (see [Appendix](#appendix)).

---

## Table of contents

1. [How the workshop works (the core idea)](#1-how-the-workshop-works-the-core-idea)
2. [One-time setup (instructor & attendees)](#2-one-time-setup-instructor--attendees)
3. [The command cheat sheet](#3-the-command-cheat-sheet)
4. [Running the system: two shells, or the tmux dashboard](#4-running-the-system-two-shells-or-the-tmux-dashboard)
5. [The stage ladder](#5-the-stage-ladder)
6. [Attendee guide — stage by stage](#6-attendee-guide--stage-by-stage)
7. [The finale (stage 10): a 5-minute whole-system demo](#7-the-finale-stage-10-a-5-minute-whole-system-demo)
8. [Instructor guide — running the room](#8-instructor-guide--running-the-room)
9. [Troubleshooting](#9-troubleshooting)
10. [Appendix](#appendix)

---

## 1. How the workshop works (the core idea)

Every stage follows the same **red → green** loop:

```
make checkpoint STAGE=NN   # load this stage into kvstore/ (use `make todo` for code stages)
make up STAGE=NN           # start the system               (in shell A — it keeps running)
make incident STAGE=NN     # ❌ reproduce the incident       (in shell B) — watch it FAIL
   …you add the next feature (write code) or change config…
make incident STAGE=NN     # ✅ run it again — watch it PASS
make status                # see the ladder of resolved incidents
```

Two kinds of stage:

- **⌨️ Code stages — `03, 04, 05, 08`.** You implement a missing function. Start from the
  gapped code with `make todo STAGE=NN`. **The gap is deliberately tiny** — all the boilerplate
  (loops, try/except, metadata, logging) is pre-filled and a single `raise NotImplementedError(...)`
  marks the **one core line** you write. You're adding the *idea*, not the plumbing.
- **⚙️ Config / observe stages — `01, 02, 06, 07, 09, 10`.** No code to write; load the
  stage with `make checkpoint STAGE=NN`, then launch and observe (the corrected configuration is
  baked into the launcher).

**The panic button:** at any time, `make checkpoint STAGE=NN` overwrites the working directory with
the known-good, complete code for stage `NN`. Nobody can get permanently stuck.

**Two ways to drive the system** (covered in detail in [§4](#4-running-the-system-two-shells-or-the-tmux-dashboard)):

- **Two shells** — `make up` in one, `make incident` in another. Simple, minimal.
- **One window — `make lab STAGE=NN`** (recommended for demos). A tmux dashboard puts every
  process in its own pane and gives you a control pane to drive the system *by hand* (write/read,
  and on the cluster stages **crash and respawn nodes**). This is the best way to project the
  system to a room.

---

## 2. One-time setup (instructor & attendees)

Everything runs **inside a Docker container** — no Python, no ports, nothing installed on the
host. (This is deliberate: host port `7000` collides with macOS Control Center, so no ports are
exposed.)

**Prerequisite:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed
and running.

```bash
# 1. Get the repo (attendees: clone the workshop repo / the template you were given)
git clone <repo-url>
cd building-large-scale-systems

# 2. Build & start the container (first build pulls Ubuntu + installs deps — do this on wifi early)
docker-compose up -d

# 3. Open a shell inside the container
docker-compose exec workshop bash

# 4. Move into the workshop
cd build-kvstore
```

Inside the container, `python` and `make` are on the `PATH` (the venv at `/opt/venv` is
pre-activated). Verify you're ready:

```bash
make verify        # preflight: checks Python/tmux + boots a real node (~15s) — do this the day before
make help          # prints the workshop commands
make start         # seed the working dir from checkpoint 01 (do this once)
```

> **Editing files:** the repo is bind-mounted, so you can edit files in
> `build-kvstore/kvstore/` with your **normal editor on your host machine** and run them in the
> container shell — changes are shared live. Or use `nano`/`vim` inside the container.

---

## 3. The command cheat sheet

Run all of these from inside the container, in the `build-kvstore/` directory.

| Command | What it does |
|---|---|
| `make verify` | **Preflight check** (~15s): Python, libraries, tmux, and a real node boot + write/read. Run it once before the workshop. |
| `make start` | Seed the working dir `kvstore/` from checkpoint 01. **Run once at the beginning.** |
| `make todo STAGE=NN` | Load the **gapped** starting point for a code stage (`03/04/05/08`) into `kvstore/`. |
| `make up STAGE=NN` | Start this stage's process(es). **Blocks the terminal** — run it in its own shell. |
| `make down` | Stop **all** workshop processes (safe to run between every stage). |
| `make incident STAGE=NN` | Run this stage's red→green check. Exit `0` = ✅ resolved, `1` = ❌ active. |
| `make checkpoint STAGE=NN` | Overwrite `kvstore/` with the known-good code for stage `NN` (the rescue). |
| `make lab STAGE=NN` | **tmux dashboard for any stage (01–10):** every process in its own pane + a control pane to drive it by hand. See [§4](#4-running-the-system-two-shells-or-the-tmux-dashboard). |
| `make lab-down` | Tear down the `make lab` tmux session **and** all stage processes. |
| `make status` | Show the ladder of resolved incidents (reads `progress.json`). |
| `make validate` | **Author/instructor only.** Run the whole regression suite (~3.5 min). |

`STAGE` is always a two-digit number (`01`, `02`, … `10`). Tear down a `make lab` session with
`make lab-down` (it kills the tmux session **and** all stage processes).

---

## 4. Running the system: two shells, or the tmux dashboard

There are two ways to run a stage. The **two-shell model** is the minimal path. The **tmux
dashboard (`make lab`)** is richer and is what you'll want for **demos** — one window, every
process visible, and a control pane to poke the system live.

### 4.0 Ports (both models)

Ports shift once, at the architecture jump from a single service to a cluster:

| Stages | Ports |
|---|---|
| `01`–`04` (single-service tier) | nodes on `5001`, `5002`, `5003` |
| `05`–`10` (cluster tier) | registry `9000`, coordinator `7000` (it spawns leader `7001` + followers `7002`–`7004`), gateway `8000` |

**Always run `make down` (or `make lab-down`) before starting a different stage** —
it stops every process *and* frees the ports (including orphaned `uvicorn` workers that a plain
process-name kill would miss). Leftover processes serving stale data on `7002–7004` are the #1
cause of confusing behavior.

### 4.1 The two-shell model

`make up` runs the system in the **foreground** so you can see the logs — it does not return
until you stop it. So you work with **two container shells**:

- **Shell A** — runs `make up STAGE=NN` (the system; leave it running).
- **Shell B** — runs `make incident STAGE=NN`, edits code, runs `make status`.

Open a second shell the same way: `docker-compose exec workshop bash`, then `cd build-kvstore`.
All the per-stage recipes in [§6](#6-attendee-guide--stage-by-stage) are written in this model.

### 4.2 The tmux dashboard — `make lab STAGE=NN` (recommended for demos)

`make lab STAGE=NN` builds a **single tmux window** with one pane per process the stage runs,
plus panes to drive and check it. **Mouse mode is on**, so it's friendly even if you've never
used tmux.

```bash
make lab STAGE=07        # build the dashboard for stage 07 and attach
```

**What you get (panes):**

- **One pane per process** — the node(s) on stages `01`–`04`; `registry` / `coordinator` /
  `gateway` (as the stage requires) on `05`–`10`. Each pane is labelled in its top border.
  *(The leader + followers are children the coordinator spawns, so their logs share the
  **coordinator** pane — there's no separate pane for them.)*
- **A `control` pane** — pre-loaded with helper commands so you drive the system **by hand**
  (see the table below). This is where the live demo happens.
- **An `incident` pane** — the graded check is **pre-typed** (`make incident STAGE=NN`); press
  **Enter** to fire it, re-run as often as you like.
- **A `scratch` pane** — a free shell (e.g. `make status`, ad-hoc `curl`).

**Control-pane helpers** (already loaded; type them in the `control` pane):

| Stages | Helper | What it does |
|---|---|---|
| `01`–`04` | `nwrite <key> <value>` | write to the node (`POST /data`) |
| `01`–`04` | `nread <key>` | read it back |
| `01`–`04` | `nhealth` | node health + in-flight request count |
| `03`–`04` | `nload [strategy] [reqs] [conc]` | fire load via the load balancer — compare `nload adaptive` vs `nload round_robin` (the stage-03 lesson) |
| `05`–`10` | `kvwrite <key> <value>` / `kvread <key>` | write / read via the cluster (gateway on stage 10, coordinator otherwise) |
| `05`–`10` | `kvstatus` | show the leader + followers (alive/dead) |
| `05`–`10` | `kvkill <n>` | take `follower-<n>` offline — a **planned** removal *through the coordinator* (it's told) |
| `08`–`10` | `kvcrash <n>` | **crash** `follower-<n>` unannounced — it dies telling no one; only the registry (heartbeats) notices |
| `05`–`10` | `kvspawn` | respawn a follower (auto-catchup on stages 09/10) |
| `10` | `kvflood [n]` | fire n quick writes; the edge gateway sheds the overflow as `429` |

Type `kvhelp` in the control pane at any time to reprint the menu for the current stage.

**tmux controls (mouse mode on):**

- **Click** a pane to focus it. **Scroll** with the mouse wheel to read a pane's history
  (press **`q`** to leave scroll/copy mode).
- **Detach** (leave it running): **`Ctrl-b`** then **`d`** (press and release `Ctrl-b`, *then*
  the next key). Re-attach with `tmux attach -t kvlab`.
- **Tear it all down:** `make lab-down`.

**Seeding behaviour:** `make lab` is **non-destructive on the code stages (`03/04/05/08`)** — it
will not overwrite a solution you're working on. For all other stages it seeds the correct
checkpoint code automatically. So the normal flows are:

- **Config/observe stage:** `make lab STAGE=06` — just works (boots the correct code).
- **Code stage:** `make todo STAGE=05` first (load the gap), *then* `make lab STAGE=05`.

**Demoing a code stage in the dashboard** (one extra step — you must restart the edited process):

```bash
make todo STAGE=05            # load the gap
make lab STAGE=05            # boots with the gapped code
#   → press Enter in the incident pane: ❌ (replication not implemented)
#   → edit kvstore/node.py (host editor or nano) — fill the one core line
#   → in the COORDINATOR pane: Ctrl-C, then ↑ Enter to relaunch with your edit
#   → press Enter in the incident pane again: ✅
```

> `make lab STAGE=02` runs 4 workers by default; **`WORKERS=1 make lab STAGE=02`** demos the
> single-thread choke.

---

## 5. The stage ladder

| # | Stage | Type | You learn | Real-world anchor |
|---|---|---|---|---|
| 01 | single node | ⚙️ | a KV store is a dict behind HTTP | Redis in-memory keyspace |
| 02 | vertical scaling | ⚙️ | the single-thread (GIL) ceiling | Redis is single-threaded on purpose |
| 03 | horizontal scaling + load balancing | ⌨️ | more nodes (why naive copies diverge), then round-robin vs adaptive routing | power-of-two / least-connections (Nginx, HAProxy) |
| 04 | rate limiting | ⌨️ | protecting the store from floods | Redis `INCR`+`EXPIRE` fixed window |
| 05 | replication | ⌨️ | single-leader replication + the stale read a weak quorum serves | Redis primary–replica async replication |
| 06 | synchronous replication | ⚙️ | all followers sync (`W = N`) → no stale reads | synchronous replication / read-from-any |
| 07 | quorum & fault tolerance | ⚙️ | majority quorum (`W + R > N`) & the CAP tradeoff | Dynamo/Cassandra tunable consistency; CP choice |
| 08 | service discovery | ⌨️ | heartbeats that detect an unannounced death | Redis Cluster gossip / etcd / Consul |
| 09 | auto-recovery | ⚙️ | respawn + catchup (*follower* recovery) | Redis `PSYNC` resync |
| 10 | full system | 🖥️ demo | edge gateway + whole-system synthesis (no incident) | the whole thing, working end-to-end |

The two **chapter boundaries** — where the code jumps rather than nudges — are **04 → 05**
(introduce the coordinator + leader/follower replication) and **07 → 08** (introduce the
registry + heartbeats). Flag these to the room as "new chapter," not "rewrite."

> **What changes between every stage, and why** is documented as a single narrative arc in
> [`build-kvstore/docs/diffs/README.md`](build-kvstore/docs/diffs/README.md), with deep-dives on
> the two boundaries ([04→05](build-kvstore/docs/diffs/04-to-05-replication.md),
> [07→08](build-kvstore/docs/diffs/07-to-08-discovery.md)). Read these to narrate *why* the system
> grows the way it does (e.g. why the load balancer and rate limiter leave at stage 05 and return
> on the gateway at stage 10).

---

## 6. Attendee guide — stage by stage

Begin once with `make start`. **Then every stage starts by loading its code into the working
directory `kvstore/` — before you `make up`:**

- **Code stages (`03`, `04`, `05`, `08`):** `make todo STAGE=NN` (loads the gapped code you complete).
- **All other stages:** `make checkpoint STAGE=NN` (loads that stage's ready-to-run code).

`make up STAGE=NN` runs *that stage's* launch command against whatever is in `kvstore/`, so
skipping the load step runs a new stage's command against old code and errors out. The per-stage
loop is then *run the incident → watch it fail → make the change → run it again → watch it pass*.
Stuck? `make checkpoint STAGE=NN` jumps you to a known-good solution.

### 01 — Single node ⚙️
A KV store is just a dict behind HTTP: `POST /data`, `GET /data/{key}`. There's no failure to
fix yet — stage 01 is the **baseline smoke test**: start the node and confirm a write reads back,
so you know the foundation works before building on it.
```bash
make up STAGE=01         # shell A — single node on :5001
make incident STAGE=01   # shell B — ✅ write+read round-trip succeeds ("the store works")
```
🖥️ **One-window demo:** `make lab STAGE=01` → in the `control` pane: `nwrite hello world` then
`nread hello`; press Enter in the `incident` pane to run the smoke test.

Stage 01 is the one green baseline with no "before" state to break; from stage **02** onward,
each stage *starts* with a failing incident you then fix.

### 02 — Vertical scaling ⚙️
**Incident:** one node saturates under concurrent load — its single thread (the GIL) is the
ceiling, exactly the constraint Redis chose on purpose.
**Do:** first watch it choke with a single worker, then scale up — *same node*, more workers.
```bash
make checkpoint STAGE=02        # load this stage into kvstore/
make up STAGE=02 WORKERS=1      # shell A — one worker (one GIL)
make incident STAGE=02          # shell B — ❌ p95 over budget (CPU-bound requests serialize)
make down
make up STAGE=02                # shell A — 4 workers (the default)
make incident STAGE=02          # shell B — ✅ p95 drops
```
🖥️ **One-window demo:** `WORKERS=1 make lab STAGE=02` → run the `incident` pane (❌); tear down
(`make lab-down`), then `make lab STAGE=02` (4 workers) → `incident` pane (✅).

### 03 — Horizontal scaling + load balancing ⌨️ **code**
**Incident:** one box is a single point of failure and a capacity wall, so we go wide — **3
heterogeneous nodes** (one weak, two strong). But the simplest spread, **round-robin by turn**, is
blind to capacity: it bombards the weak node with its fair 1/3 share, the weak node queues, and the
global p95 tanks.
**Do (one line):** in `kvstore/load_balancer.py` → `AdaptiveStrategy.get_node`, return the
lowest-score node — `return min(nodes, key=node_stats.get_score)`. Adaptive steers traffic off the
weak node and the tail recovers.
```bash
make todo STAGE=03        # load the gapped code (raises NotImplementedError where you write)
make up STAGE=03         # shell A — 3 nodes (1 weak, 2 strong)
make incident STAGE=03   # shell B — ❌ adaptive can't be measured (NotImplementedError)
# …edit kvstore/load_balancer.py → AdaptiveStrategy.get_node, then restart…
make down ; make up STAGE=03
make incident STAGE=03   # shell B — ✅ adaptive p95 clearly below round-robin p95
```
🖥️ **One-window demo:** after implementing, `make todo STAGE=03 && make lab STAGE=03`; in the
`control` pane compare `nload round_robin 96 12` vs `nload adaptive 96 12` — adaptive steers away
from the weak node. (Restart the node panes after editing: `Ctrl-C` then `↑ Enter` in each.)

*Note:* the three nodes also have **separate** dicts — naive horizontal scaling splits your data.
That's exactly what motivates replication at stage 05.

### 04 — Rate limiting ⌨️ **code**
**Incident:** a flood overwhelms the node (no `429`s — every request gets in).
**Do (a few lines):** in `kvstore/rate_limiter.py` → `FixedWindowStrategy.is_allowed`, write the
fixed-window core (the metadata is pre-filled): reset the counter when the window expires, then
allow while `count < max` (incrementing), else reject.
```bash
make todo STAGE=04
make up STAGE=04         # shell A
make incident STAGE=04   # shell B — ❌ nothing blocked (no rate limiting in effect)
# …edit kvstore/rate_limiter.py → FixedWindowStrategy.is_allowed, then restart…
make down ; make up STAGE=04
make incident STAGE=04   # shell B — ✅ first N succeed, the rest get 429
```
🖥️ **One-window demo:** `make todo STAGE=04 && make lab STAGE=04`; press Enter in the `incident`
pane (❌), implement the gap, restart the node pane (`Ctrl-C`, `↑ Enter`), re-run incident (✅).

### 05 — Replication ⌨️ **code**  *(chapter boundary: coordinator + leader/followers appear)*
**Incident:** one copy is fragile. Reads in this system are served by the **follower tier**
(the read replicas, like Redis) — *never* the leader. Without replication the leader holds the
only copy, so the followers are empty and your data is **stranded**: unreadable now, and gone
if that node dies.
**Do (one line):** in `kvstore/node.py` → `replicate_to_follower`, write the single POST that *is*
replication (the try/except and result handling are pre-filled):
`resp = requests.post(f"{follower_url}/replicate", json={"key": key, "value": value, "version": version, "source": NODE_ID}, timeout=10)`.
```bash
make todo STAGE=05
make up STAGE=05         # shell A
make incident STAGE=05   # shell B — ❌ data is stranded on the leader; the read-tier is empty
# …edit kvstore/node.py → replicate_to_follower, then restart…
make down ; make up STAGE=05
make incident STAGE=05   # shell B — ✅ the write reaches the replicas; reads now succeed
```
🖥️ **One-window demo:** `make todo STAGE=05 && make lab STAGE=05`. In the `control` pane,
`kvwrite cart shoes` then `kvread cart` (❌ before you implement). Implement, restart the
`coordinator` pane (`Ctrl-C`, `↑ Enter`), and `kvread cart` succeeds. The `coordinator` pane
shows the leader + followers, so you can watch replication land.
*Show the stranding live (optional, drives the point home):* on the ❌ run the leader **did**
store the write — it's the only copy. With shell A's logs you can see the leader's port (the
coordinator spawns it); then from shell B compare the leader directly against the read path:
```bash
curl -s localhost:7001/data/<key>   # the leader HAS it (200 + value)
curl -s localhost:7000/read/<key>   # the coordinator read (follower tier) MISSES — stranded
```
*We are deliberately not doing leader failover here* — the point isn't "the leader died," it's
that data living on a single node is fragile and unreachable through the read path. Failover/
recovery come later (and even then this workshop recovers *followers*, not the leader).

*Note:* stage 05 runs a **weak quorum** (`W=1, R=1`) on purpose — that sets up the next stage.

### 06 — Synchronous replication ⚙️
**Incident:** a read *immediately* after an **update** returns the **old value**, not the new one —
because only *some* followers are synchronous, so the update acks before the slow async follower has
it, and the read can land on that lagging node.
**Do:** make **every follower synchronous** — raise `W` to `N`. The stage launches with `W=3, R=1`:
each write reaches all three followers before it returns, so any single read (`R=1`) is guaranteed
fresh. (It's still the overlap rule `W + R > N` — `3+1>3` — but the idea here is simply "all sync.")

*What the incident does (so you know what you're watching):* it writes `"old"`, waits 7s for
every follower (including the slow async one) to catch up, then updates to `"fresh"` and reads
**immediately**. With `W=1, R=1` the read lands on the async follower that still holds `"old"` —
every node has the key, but one is behind. This is different from stage 05 where the key was
**absent**; here it is **present but outdated**.

```bash
# feel the failure first — run against the WEAK stage-05 quorum:
make checkpoint STAGE=05 ; make up STAGE=05   # shell A: W=1, R=1
make incident STAGE=06                   # shell B: ❌ 4/4 reads returned "old" (stale)
make down
# now make every follower sync (05/06/07 share code; only W/R differ):
make checkpoint STAGE=06 ; make up STAGE=06   # shell A: W=3, R=1 (all followers sync)
make incident STAGE=06                   # shell B: ✅ 0/4 stale — every write reaches all followers
```
🖥️ **One-window demo:** `make lab STAGE=05` (weak quorum) → `incident` pane shows stale reads;
tear down, `make lab STAGE=06` (W=3,R=1, all sync) → `incident` pane is clean.

*Note:* you killed staleness by coupling the cluster's fate together — a write now needs **all
three** followers. That zero-failure-budget is exactly the trap stage 07 springs.

### 07 — Quorum & fault tolerance / CAP ⚙️  *(the payoff — connect it back to 06)*
**Incident:** stage 06's all-sync (`W=3=N`) is consistent but **brittle** — every ack you demand is
a node that must be alive, so **tolerable failures = N − W = 0**. One kill and writes go down
(`503`).
**Do:** switch to a **majority quorum** — `W=2, R=2`.

**The narrative:** `W=2, R=2` for `N=3` isn't arbitrary — it's the **majority** (`floor(N/2)+1`),
the one setting that does *both* jobs: it survives `floor(N/2)=1` failure **and** keeps `W+R>N`
(`4>3`, read/write sets overlap → reads stay fresh). All-sync `W=3` was the over-tuned trap:
consistent, but a zero failure budget. (Drop `R` back to 1 here and `W+R = 3 ≤ N` → stale reads
return — that's the general rule **W + R > N** doing its work.)

**The CAP moment to point out:** on the ❌ run, after the kill the incident shows **writes
refused (`503`) while reads still succeed**. Same cluster, same failure — the system *chose* to
sacrifice write-availability to preserve consistency (the **CP** corner). A Dynamo-style AP
system would instead accept the write and reconcile later. You pick the corner by how you set `W`.

```bash
# fail first — stage 06's all-sync quorum (W=3=N); one kill loses the write quorum:
make checkpoint STAGE=06 ; make up STAGE=06   # shell A — W=3, R=1 (all followers sync)
make incident STAGE=07                   # shell B — ❌ writes REFUSED (503) but reads still succeed (CP)
make down
# fix — W=2 is the majority: tolerates floor(N/2)=1 death and stays consistent:
make checkpoint STAGE=07 ; make up STAGE=07   # shell A — W=2, R=2
make incident STAGE=07                   # shell B — ✅ writes AND reads survive the failure
```
🖥️ **One-window demo (the CAP moment, by hand):** `make lab STAGE=07` (W=2,R=2). In the `control`
pane: `kvwrite cart shoes` → `kvkill 1` → `kvstatus` (one follower dead, writes still work — a
`kvwrite` succeeds) → `kvkill 2` → now `kvwrite` is **refused (503)** because the write quorum is
lost, while `kvread cart` still succeeds. Watch the `coordinator` pane log the quorum decision.
That's the CP choice made visible — no script needed.

*Scope caveat:* this is *follower* fault tolerance (quorum counts followers; the leader is assumed
alive). The leader remains a single point of failure this workshop doesn't solve.

*Talking point (load balancing ↔ quorum):* the coordinator reads from a fixed set of followers (the
highest-`R` ports), which is why staleness is reproducible. In a real Dynamo-style system the
coordinator instead reads from the `R` **fastest/closest** replicas and reconciles by version —
load-aware read routing. We pick deterministically *on purpose* so you can watch a stale read happen;
making it load-based would make the demo flaky. (This is also the client-side→server-side load-
balancing shift: the routing smarts now live in the coordinator, not the client.)

### 08 — Service discovery ⌨️ **code**  *(chapter boundary: registry + heartbeats appear)*
**Incident:** the registry never sees a node, so it can't detect the node's death — kills look
"alive."
**Do (one line):** in `kvstore/node.py` → `heartbeat_loop`, write the single POST that announces
the node is alive (the `while` loop, try/except and pacing are pre-filled):
`resp = requests.post(f"{REGISTRY_URL}/heartbeat", json={"node_id": NODE_ID, "port": NODE_PORT, "url": f"http://localhost:{NODE_PORT}", "role": NODE_ROLE}, timeout=2)`.
```bash
make todo STAGE=08
make up STAGE=08         # shell A
make incident STAGE=08   # shell B — ❌ killed node still shows "alive" (registry never saw it)
# …edit kvstore/node.py → heartbeat_loop, then restart…
make down ; make up STAGE=08
make incident STAGE=08   # shell B — ✅ a killed node is correctly reported "dead"
```
🖥️ **One-window demo:** `make todo STAGE=08 && make lab STAGE=08` → watch the `registry` and
`coordinator` panes side by side. `kvcrash 1` (an **unannounced** crash — it doesn't go through the
coordinator), then `kvstatus`: before you implement heartbeats the registry never saw the node so it
never marks it dead; after (restart the `coordinator` pane), the missed heartbeats are detected.

### 09 — Auto-recovery ⚙️  *(⭐ the hands-on finale — end the lab here in a 2-hour slot)*
**Incident:** a dead follower stays dead and the cluster runs degraded.
**Do:** enable `--auto-spawn`; the coordinator respawns the follower and **catches it up** from
the leader's snapshot.

> **This is the emotional high-note of the hands-on workshop:** the cluster *heals itself*. If you're
> tight on time (see the [2-hour core path](#2-hour-core-path)), make this the last thing attendees do
> with their own hands, then close with the [stage-10 demo](#7-the-finale-stage-10-a-5-minute-whole-system-demo).
```bash
# fail first — stage 08 has discovery but no auto-spawn, so a killed follower stays dead:
make checkpoint STAGE=08 ; make up STAGE=08   # shell A — registry (no auto-spawn) + coordinator
make incident STAGE=09                   # shell B — ❌ killed follower stays dead
make down
# fix — stage 09 turns on auto-spawn + catchup:
make checkpoint STAGE=09 ; make up STAGE=09   # shell A — registry auto-spawn + coordinator
make incident STAGE=09                   # shell B — ✅ killed follower is respawned AND has the data
```
🖥️ **One-window demo (watch self-healing):** `make lab STAGE=09`. In the `control` pane:
`kvwrite cart shoes` → `kvcrash 2` (unannounced crash) → `kvstatus` (dead) → wait ~5s → `kvstatus`
again: the registry auto-respawned it and the `coordinator` pane shows the catchup. `kvread cart`
confirms the revived follower has the data. (Compare with stage 08, where it would just stay dead.)

*This is **follower** recovery (replace + resync), not leader failover (that's Sentinel — out of
scope).*

### After each stage
```bash
make status      # ✅/⬜ ladder of resolved incidents
make down        # before moving to the next stage
```

---

## 7. The finale (stage 10): a 5-minute whole-system demo

By stage 09 attendees have **built the entire system** and watched it heal itself. Stage 10 is the
**synthesis** — you run it as a short live demo (not a hands-on lab), put the **edge gateway** in
front, and trace one request through *everything* they built. There is **no incident** for this
stage and nothing to grade: it's purely the working whole, driven by hand.

Run it once and drive it from the control pane:

```bash
make lab STAGE=10        # registry + coordinator + gateway panes, all visible
```

**The 4 beats (do these live in the `control` pane):**

1. **One request through the whole stack.** `kvwrite cart shoes` → narrate it: gateway (`:8000`) →
   coordinator (`:7000`) → leader (`:7001`) → followers replicate. Then `kvread cart` — point at
   `served_by` and `quorum_responses` in the JSON.
   *Say:* "The client is **dumb** now — it just hits the gateway. The smart routing it did back at
   stage 03 moved **server-side**: the coordinator decides which followers serve this read (the
   read quorum). That's the client-side→server-side load-balancing shift, made real."
2. **Protect — the edge sheds load.** `kvflood 15` → the first ~10 succeed, the rest come back **429**.
   *Say:* "That's the `rate_limiter.py` you wrote at stage 04 — now living on the gateway, at the edge."
3. **Survive + self-heal (the climax).** `kvwrite order paid` → `kvcrash 1` (an unannounced crash) →
   `kvstatus` (one follower dead, **writes still work** — the W=2 quorum holds) → wait ~5s →
   `kvstatus` again (the registry **auto-respawned** it; the `coordinator` pane shows catchup) →
   `kvread order` still returns `paid`.
   *Say:* "Detected the death → held quorum → respawned → caught up → never lost the write."
4. **The closing line.** "From a `dict` behind HTTP, you built a rate-limited, replicated,
   quorum-consistent, **self-healing** distributed key-value store."

> **Honest caveat to say out loud:** the gateway forwards to a *single* coordinator, so it isn't
> load-balancing across coordinators — in production you'd run several behind it. `gateway.py` even
> imports `load_balancer` but doesn't use it. The point of stage 10 is the **synthesis**, not new code.

---

## 8. Instructor guide — running the room

### 8.1 Pre-flight (do this *before* the session — ideally the day before)

1. **Build the container on good wifi.** `docker-compose up -d` pulls Ubuntu and installs
   dependencies; you don't want 60 people doing this on conference wifi at 09:00.
2. **Run the full regression suite** to prove the whole ladder is intact on your machine:
   ```bash
   docker-compose exec workshop bash -c 'cd build-kvstore && make validate'
   ```
   This boots every checkpoint, asserts each incident is **GREEN on its stage** and **RED on the
   "before" state**, and confirms ports are free between cases. Expect **16/16 cases pass**
   (~3.5 min). Re-run it after *any* edit to a coordinator/registry/node/incident or
   to `tools/up.sh`/`down.sh` — it is your correctness gate.
3. **Rehearse the human flow** end-to-end: `make start`, then walk `01 → 09` using
   todo/up/incident/checkpoint, and finish with the stage-10 demo (§7). The regression suite proves
   correctness mechanically; the rehearsal is about *pacing* and the couple of machine-dependent
   thresholds (see 8.4).

### 8.2 Pacing

There are 10 stages but only **4 require writing code** (`03, 04, 05, 08`) — budget the most
time there. The config/observe stages move fast and are where you narrate the concept. Give the
room a hard checkpoint at each **chapter boundary** (after 04, after 07): everyone runs
`make checkpoint STAGE=04` / `make checkpoint STAGE=07` so the whole room re-synchronizes regardless of who
fell behind.

<a id="2-hour-core-path"></a>
**The 2-hour core path.** You cannot run 10 stages hands-on in a 2-hour slot with a mixed-skill
room. Triage like this — put your minutes on the four code gaps, and **end the hands-on at stage 09**
(self-healing is the climax); close with the stage-10 demo:

| Bucket | Stages | How to run it |
|---|---|---|
| Quick framing | `01` | show, ~2 min |
| Fast config "aha" | `02`, `06`, `07` | run the incident, narrate — ~5 min each |
| **Hands-on code (the heart)** | **`03`, `04`, `05`, `08`** | the one-line gaps — most of your time |
| Hands-on climax | `09` | self-healing — the last thing they *do* |
| Synthesis | `10` | **5-min speaker demo** (§7) — no incident |

If you're even tighter, `08` (heartbeat) is the most cuttable code stage — demo it instead of having
the room write it.

### 8.3 Framing (the talking points that make it land)

- **The GIL = Redis's single thread for free.** Stage 02's single-thread ceiling is the exact
  constraint Redis embraces; you scale by running more instances.
- **Per-stage real-world anchors** (see the ladder table) — name-drop the real system each
  concept comes from so attendees map the toy to production.
- **"Follower recovery, not leader failover."** Stage 09 replaces and resyncs a *follower*;
  promoting a new leader (Sentinel/Raft) is explicitly out of scope — say so, so nobody thinks
  the demo is doing more than it is.
- **The honest quorum caveat (important).** For a rock-solid live demo, the quorum here is
  **deterministic and port-pinned**: the first `W` followers (by port) are the synchronous write
  set and the largest `R` (by port) are the read set, so overlap is guaranteed and reproducible.
  **Real systems count *any* W and *any* R acknowledgments** — the overlap is then probabilistic,
  which is what makes stale reads an *intermittent* bug in the wild. Put this on a caveat slide
  so the simplification is explicit.

### 8.4 The two timing-sensitive incidents

Almost everything is deterministic, with two machine-dependent exceptions:

- **`incident_02`** (vertical scaling) asserts a p95 latency budget (`P95_BUDGET_MS=300`). It
  passes comfortably on normal hardware. If it flakes on a slow laptop, widen it via the env var
  rather than weakening the suite: `P95_BUDGET_MS=500 make incident STAGE=02`.
- **`incident_03`** compares adaptive vs round-robin p95 (relative, not absolute), over 96 requests
  and taking the best of 3 trials to damp noise. It usually passes, but on a very quiet or very
  noisy machine the two can still occasionally invert (adaptive measuring slower). If its GREEN
  case flakes, just **re-run it** — it's a timing artifact, not a real regression
  (`bash tools/validate_ladder.sh 03`).

### 8.5 Foot-guns (these have cost real time — honor them)

- **Always clean up with `make down`.** It kills processes by script name *and* by port, so it
  catches orphaned `uvicorn --workers` workers (whose command line is just `python`). A plain
  `pkill -f node.py` misses those and they keep serving stale data.
- **Confirm ports are free between runs** if you suspect leftovers:
  `ss -ltn | grep -cE ':5001|:7000|:9000'` should print `0`.
- **Never `pkill -f coordinator.py` from a script whose own text contains that string** — it
  SIGKILLs itself. `make down` is the safe default; the regression suite already handles this
  correctly.
- **Zombie processes are handled — but recreate the container after pulling.** The container runs
  with `init: true` (PID 1 is `docker-init`/tini), which **reaps** the orphaned node subprocesses
  that pile up over many `up`/`down`/`lab` cycles — without it they accumulate as `<defunct>`
  zombies and eventually exhaust the PID table (`fork()` hangs). This only takes effect after
  `docker-compose up -d` **recreates** the container, so do that once after pulling these changes.
  If a long-lived container ever feels sluggish: `docker-compose restart workshop`.

### 8.6 Demoing with the tmux dashboard

For a live audience, prefer **`make lab STAGE=NN`** over the two-shell model — it projects the
whole system in one window (one pane per process) and lets you drive it by hand from the control
pane (see [§4.2](#42-the-tmux-dashboard--make-lab-stagenn-recommended-for-demos)). The highest-
impact moments to do *live* rather than via the incident script:

- **03 (load balancing):** compare `nload round_robin 96 12` vs `nload adaptive 96 12` — round-robin's
  blind 1/3 share piles onto the weak node and drags global p95; adaptive redistributes off it.
- **07:** `kvkill 1` (survives) then `kvkill 2` (writes refused, reads survive) — the CAP choice.
- **09:** `kvcrash 2` (unannounced), wait, `kvstatus` — the cluster respawns and catches up the follower itself.

Mouse mode is on, so you can click/scroll panes without teaching tmux keybindings. Tear down
between stages with `make lab-down`.

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `make up` fails with "address already in use" | a previous stage's process is still holding the port | `make down`, then retry |
| Reads return stale / wrong data for no reason | orphaned followers from a prior run on `7002–7004` | `make down`; confirm `ss -ltn \| grep -cE ':7000\|:9000'` is `0` |
| `NotImplementedError: STAGE NN: …` | you're on a code stage and the gap isn't filled | implement the function in `kvstore/`, or `make checkpoint STAGE=NN` to see the solution |
| An attendee is hopelessly behind | — | `make checkpoint STAGE=NN` jumps their `kvstore/` to a known-good stage instantly |
| `incident_02` fails on a slow machine | p95 budget too tight for that hardware | `P95_BUDGET_MS=500 make incident STAGE=02` |
| `incident_03` green flakes (adaptive ≥ round-robin) | timing noise in the relative p95 comparison | re-run it; not a real regression |
| `make: command not found` | you're on the host, not in the container | `docker-compose exec workshop bash` then `cd build-kvstore` |
| Lost all your edits | you ran `make start`/`make todo`/`make checkpoint` (they overwrite `kvstore/`) | expected — `kvstore/` is disposable; commit your own work elsewhere if you want to keep it |
| `make lab` edits don't take effect (code stage) | the service pane is still running your old code | in the relevant service pane (e.g. `coordinator`): `Ctrl-C`, then `↑ Enter` to relaunch |
| `make lab STAGE=05/08` boots the solution, not the gap | `make lab` is non-destructive on code stages and reused existing `kvstore/` | run `make todo STAGE=NN` first, then `make lab STAGE=NN` |
| `tmux not found` | rare; tmux missing in the container | `apt-get install -y tmux` (or use the two-shell model) |
| Stuck inside tmux | — | detach with `Ctrl-b` then `d`; re-attach `tmux attach -t kvlab`; kill all `make lab-down` |
| Container slow / `fork`/exec hangs after many runs | (only on a container created *without* `init: true`) zombie buildup | `docker-compose up -d` to recreate with the init, or `docker-compose restart workshop` |

---

## Appendix

### The reference labs (`labs/`)

Before the narrative restructure, the workshop shipped three standalone labs. They are **left
untouched** as a reference and still run independently:

- [`labs/scalability/`](labs/scalability/) — load balancing & rate limiting (nodes on `5001+`).
- [`labs/replication/`](labs/replication/) — single-leader replication & quorums (coordinator
  `6000`, leader `6001`, followers `6002+`).
- [`labs/distributed-kvstore/`](labs/distributed-kvstore/) — the full integrated system
  (registry `9000`, coordinator `7000`, gateway `8000`). `build-kvstore/checkpoints/10` is
  derived from this.

Each has its own `README.md` with step-by-step demos.

### Key files & directories

| Path | What it is |
|---|---|
| `build-kvstore/README.md` | Attendee-facing intro to the ladder |
| `build-kvstore/SPEC.md` | The full design + phase status (source of truth) |
| `build-kvstore/docs/stages.md` | The per-stage guide (condensed in §6 above) |
| `build-kvstore/docs/diffs/` | The build as one narrative arc — what changes between every stage and why (incl. the two chapter deep-dives) |
| `build-kvstore/docs/bugs-fixed.md` | Running log of bugs found & fixed during verification |
| `build-kvstore/tools/tmux_lab.sh` | The `make lab` dashboard (one pane per process + a control pane) |
| `build-kvstore/tools/kvplay.sh` | The control-pane helpers (`nwrite`/`nload`/`kvkill`/`kvspawn`/…) sourced by `make lab` |
| `build-kvstore/checkpoints/NN-*/` | Frozen, known-good snapshot of each stage |
| `build-kvstore/stages/{03,04,05,08}/` | Gapped starting points for the code stages (one core line each) |
| `build-kvstore/incidents/` | The black-box red→green incident scripts |
| `build-kvstore/kvstore/` | The working dir attendees edit (gitignored; seeded by `make start`) |

### Why decisions were made the way they were

See [`wiki/decisions/`](wiki/decisions/) (indexed in
[`wiki/decisions/INDEX.md`](wiki/decisions/INDEX.md)) — in particular the three
`build-kvstore` entries covering the incremental restructure, the checkpoint build approach, and
the regression suite.
