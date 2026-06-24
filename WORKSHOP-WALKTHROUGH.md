# Workshop Walkthrough — Build-a-KVStore

The complete guide to running the **Building Large Scale Systems** tutorial, for both the
**instructor** (you, running the room) and the **attendees** (following along). It covers
setup, the run model, every stage, the capstone, and what to do when things go wrong.

> **What attendees build:** starting from a single in-memory dict behind HTTP, they grow a
> distributed key-value store — single-leader replication and snapshot resync *like Redis*,
> tunable read/write quorums *like Dynamo* — and watch it survive failures injected at each
> step. The system is built in **11 stages (00 → 10)**, each motivated by an **incident** that
> breaks the previous version and only passes once the next feature is added.

The primary workshop lives in [`build-kvstore/`](build-kvstore/). The original three labs under
[`labs/`](labs/) remain as a standalone reference (see [Appendix](#appendix)).

---

## Table of contents

1. [How the workshop works (the core idea)](#1-how-the-workshop-works-the-core-idea)
2. [One-time setup (instructor & attendees)](#2-one-time-setup-instructor--attendees)
3. [The command cheat sheet](#3-the-command-cheat-sheet)
4. [Ports & the two-shell model](#4-ports--the-two-shell-model)
5. [The stage ladder](#5-the-stage-ladder)
6. [Attendee guide — stage by stage](#6-attendee-guide--stage-by-stage)
7. [The capstone (stage 10)](#7-the-capstone-stage-10)
8. [Instructor guide — running the room](#8-instructor-guide--running-the-room)
9. [Troubleshooting](#9-troubleshooting)
10. [Appendix](#appendix)

---

## 1. How the workshop works (the core idea)

Every stage follows the same **red → green** loop:

```
make reset STAGE=NN       # load this stage into kvstore/ (use `make gap` for code stages)
make up STAGE=NN          # start the system               (in shell A — it keeps running)
make incident STAGE=NN    # ❌ reproduce the incident       (in shell B) — watch it FAIL
   …you add the next feature (write code) or change config…
make incident STAGE=NN    # ✅ run it again — watch it PASS
make status               # see the ladder of resolved incidents
```

Two kinds of stage:

- **⌨️ Code stages — `03, 04, 05, 08`.** You implement a missing function. Start from the
  gapped code with `make gap STAGE=NN` (it drops a `raise NotImplementedError(...)` where your
  code goes).
- **⚙️ Config / observe stages — `00, 01, 02, 06, 07, 09, 10`.** No code to write; load the
  stage with `make reset STAGE=NN`, then launch and observe (the corrected configuration is
  baked into the launcher).

**The panic button:** at any time, `make reset STAGE=NN` overwrites the working directory with
the known-good, complete code for stage `NN`. Nobody can get permanently stuck.

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
make help          # prints the workshop commands
make start         # seed the working dir from checkpoint 00 (do this once)
```

> **Editing files:** the repo is bind-mounted, so you can edit files in
> `build-kvstore/kvstore/` with your **normal editor on your host machine** and run them in the
> container shell — changes are shared live. Or use `nano`/`vim` inside the container.

---

## 3. The command cheat sheet

Run all of these from inside the container, in the `build-kvstore/` directory.

| Command | What it does |
|---|---|
| `make start` | Seed the working dir `kvstore/` from checkpoint 00. **Run once at the beginning.** |
| `make gap STAGE=NN` | Load the **gapped** starting point for a code stage (`03/04/05/08`) into `kvstore/`. |
| `make up STAGE=NN` | Start this stage's process(es). **Blocks the terminal** — run it in its own shell. |
| `make down` | Stop **all** workshop processes (safe to run between every stage). |
| `make incident STAGE=NN` | Run this stage's red→green check. Exit `0` = ✅ resolved, `1` = ❌ active. |
| `make reset STAGE=NN` | Overwrite `kvstore/` with the known-good code for stage `NN` (the rescue). |
| `make status` | Show the ladder of resolved incidents (reads `progress.json`). |
| `make validate` | **Author/instructor only.** Run the whole regression suite (~3.5 min). |

`STAGE` is always a two-digit number (`00`, `01`, … `10`).

---

## 4. Ports & the two-shell model

`make up` runs the system in the **foreground** so attendees can see the logs — it does not
return until you stop it. So you always work with **two container shells**:

- **Shell A** — runs `make up STAGE=NN` (the system; leave it running).
- **Shell B** — runs `make incident STAGE=NN`, edits code, runs `make status`.

Open a second shell the same way: `docker-compose exec workshop bash`, then `cd build-kvstore`.

**Ports shift once, at the architecture jump from a single service to a cluster:**

| Stages | Ports |
|---|---|
| `00`–`04` (single-service tier) | nodes on `5001`, `5002`, `5003` |
| `05`–`10` (cluster tier) | registry `9000`, coordinator `7000`, gateway `8000` |

**Always run `make down` before starting a different stage** — it stops every process *and*
frees the ports (including orphaned `uvicorn` workers that a plain process-name kill would
miss). Leftover processes serving stale data on `7002–7004` are the #1 cause of confusing
behavior.

---

## 5. The stage ladder

| # | Stage | Type | You learn | Real-world anchor |
|---|---|---|---|---|
| 00 | single node | ⚙️ | a KV store is a dict behind HTTP | Redis in-memory keyspace |
| 01 | vertical scaling | ⚙️ | the single-thread (GIL) ceiling | Redis is single-threaded on purpose |
| 02 | horizontal scaling | ⚙️ | more nodes; why naive copies diverge | sharding splits your data |
| 03 | load balancing | ⌨️ | round-robin vs adaptive routing | power-of-two / least-connections (Nginx, HAProxy) |
| 04 | rate limiting | ⌨️ | protecting the store from floods | Redis `INCR`+`EXPIRE` fixed window |
| 05 | replication | ⌨️ | single-leader replication | Redis primary–replica async replication |
| 06 | quorum | ⚙️ | `W + R > N` and stale reads | Dynamo/Cassandra tunable consistency |
| 07 | fault tolerance | ⚙️ | quorum loss & the CAP tradeoff | consistency-over-availability choice |
| 08 | service discovery | ⌨️ | heartbeats that detect death | Redis Cluster gossip / etcd / Consul |
| 09 | auto-recovery | ⚙️ | respawn + catchup (*follower* recovery) | Redis `PSYNC` resync |
| 10 | full system | ⚙️ | edge gateway + the SRE capstone | the whole thing, misconfigured |

The two **chapter boundaries** — where the code jumps rather than nudges — are **04 → 05**
(introduce the coordinator + leader/follower replication) and **07 → 08** (introduce the
registry + heartbeats). Flag these to the room as "new chapter," not "rewrite."

---

## 6. Attendee guide — stage by stage

Begin once with `make start`. **Then every stage starts by loading its code into the working
directory `kvstore/` — before you `make up`:**

- **Code stages (`03`, `04`, `05`, `08`):** `make gap STAGE=NN` (loads the gapped code you complete).
- **All other stages:** `make reset STAGE=NN` (loads that stage's ready-to-run code).

`make up STAGE=NN` runs *that stage's* launch command against whatever is in `kvstore/`, so
skipping the load step runs a new stage's command against old code and errors out. The per-stage
loop is then *run the incident → watch it fail → make the change → run it again → watch it pass*.
Stuck? `make reset STAGE=NN` jumps you to a known-good solution.

### 00 — Single node ⚙️
A KV store is just a dict behind HTTP: `POST /data`, `GET /data/{key}`. There's no failure to
fix yet — stage 00 is the **baseline smoke test**: start the node and confirm a write reads back,
so you know the foundation works before building on it.
```bash
make up STAGE=00         # shell A — single node on :5001
make incident STAGE=00   # shell B — ✅ write+read round-trip succeeds ("the store works")
```
Stage 00 is the one green baseline with no "before" state to break; from stage **01** onward,
each stage *starts* with a failing incident you then fix.

### 01 — Vertical scaling ⚙️
**Incident:** one node saturates under concurrent load — its single thread (the GIL) is the
ceiling, exactly the constraint Redis chose on purpose.
**Do:** the launcher scales the node up with `--workers 4`. Run it and watch the p95 latency
drop.
```bash
make reset STAGE=01      # load this stage into kvstore/
make up STAGE=01         # shell A — single node with load-sim + 4 workers
make incident STAGE=01   # shell B — ✅ p95 under budget with workers
```

### 02 — Horizontal scaling ⚙️
**Incident:** a single node is both a single point of failure and a capacity wall.
**Do:** run 3 nodes; the client spreads load across them.
```bash
make reset STAGE=02      # load this stage into kvstore/
make up STAGE=02         # shell A — 3 nodes on :5001-:5003
make incident STAGE=02   # shell B
```
*Note:* the three nodes have **separate** dicts — naive horizontal scaling splits your data.
That's exactly what motivates replication at stage 05.

### 03 — Load balancing ⌨️ **code**
**Incident:** round-robin ignores node capacity and tanks on the slow node.
**Do:** implement `AdaptiveStrategy.get_node` in `kvstore/load_balancer.py` — pick the
lowest-score (least-loaded) node.
```bash
make gap STAGE=03        # load the gapped code (raises NotImplementedError where you write)
# …edit kvstore/load_balancer.py → AdaptiveStrategy.get_node…
make up STAGE=03 ; make incident STAGE=03    # ✅ adaptive p95 < round-robin p95
```

### 04 — Rate limiting ⌨️ **code**
**Incident:** a flood overwhelms the node (no `429`s — every request gets in).
**Do:** implement `FixedWindowStrategy.is_allowed` in `kvstore/rate_limiter.py`.
```bash
make gap STAGE=04
# …edit kvstore/rate_limiter.py → FixedWindowStrategy.is_allowed…
make up STAGE=04 ; make incident STAGE=04    # ✅ first N succeed, the rest get 429
```

### 05 — Replication ⌨️ **code**  *(chapter boundary: coordinator + leader/followers appear)*
**Incident:** a write to the leader never reaches the followers — the data isn't durable.
**Do:** implement `replicate_to_follower` in `kvstore/node.py` — POST the write to the
follower's `/replicate`.
```bash
make gap STAGE=05
# …edit kvstore/node.py → replicate_to_follower…
make up STAGE=05 ; make incident STAGE=05    # ✅ data written to the leader propagates
```
*Note:* stage 05 runs a **weak quorum** (`W=1, R=1`) on purpose — that sets up the next stage.

### 06 — Quorum ⚙️
**Incident:** a read *immediately* after a write is **stale**, because `W + R ≤ N`.
**Do:** raise the read quorum so `W + R > N`. The stage launches with `W=2, R=2` (N=3 ⇒
`4 > 3`).
```bash
# feel the failure first — run the stale-read check against the WEAK stage-05 quorum:
make reset STAGE=05 ; make up STAGE=05   # shell A: W=1, R=1
make incident STAGE=06                   # shell B: ❌ stale read
make down
# now the corrected quorum (05/06/07 share code; only W/R differ):
make reset STAGE=06 ; make up STAGE=06   # shell A: W=2, R=2
make incident STAGE=06                   # shell B: ✅ fresh read
```

### 07 — Fault tolerance / CAP ⚙️
**Incident:** with too-tight `W`, killing `floor(N/2)` followers causes a total **write outage**
(`503`). With `W=2` and `N=3`, the cluster tolerates 1 follower loss and keeps serving.
```bash
make reset STAGE=07      # load this stage into kvstore/
make up STAGE=07         # shell A — W=2, R=2
make incident STAGE=07   # shell B — ✅ survives floor(N/2) kills at W=2
```
*Experiment (see the outage):* stop, then launch the cluster manually with a too-tight quorum
and re-run the incident:
```bash
make down
cd kvstore && python coordinator.py --followers 3 --write-quorum 3 --read-quorum 2   # shell A
make incident STAGE=07    # ❌ killing one follower now loses write quorum → 503
```

### 08 — Service discovery ⌨️ **code**  *(chapter boundary: registry + heartbeats appear)*
**Incident:** the registry never sees a node, so it can't detect the node's death — kills look
"alive."
**Do:** implement `heartbeat_loop` in `kvstore/node.py` — POST to the registry every interval.
```bash
make gap STAGE=08
# …edit kvstore/node.py → heartbeat_loop…
make up STAGE=08 ; make incident STAGE=08    # ✅ a killed node is correctly reported "dead"
```

### 09 — Auto-recovery ⚙️
**Incident:** a dead follower stays dead and the cluster runs degraded.
**Do:** the launcher enables `--auto-spawn`; the coordinator respawns the follower and **catches
it up** from the leader's snapshot.
```bash
make reset STAGE=09      # load this stage into kvstore/
make up STAGE=09         # shell A — registry auto-spawn + coordinator
make incident STAGE=09   # shell B — ✅ killed follower is respawned AND has the data
```
*This is **follower** recovery (replace + resync), not leader failover (that's Sentinel — out of
scope).*

### After each stage
```bash
make status      # ✅/⬜ ladder of resolved incidents
make down        # before moving to the next stage
```

---

## 7. The capstone (stage 10)

Stage 10 puts an **edge gateway** in front of the cluster (rate limiting moves from the node to
the gateway — the *same* `rate_limiter.py` you wrote at stage 04). Then attendees play **SRE**:
they inherit a **misconfigured version of the system they just built** and fix it by editing
config — not code.

```bash
make reset STAGE=10              # load the full system into kvstore/
make up STAGE=10                 # shell A: registry :9000 + coordinator :7000 + gateway :8000
cat kvstore/scenario_brief.md    # the 5 CloudCart incident tickets
nano kvstore/student_config.json # fix W, R, followers, rate-limit window, auto-spawn delay
make incident STAGE=10           # shell B: the graded assessment — iterate until the score passes
```

The assessment scores out of 100 across the incident scenarios. The answer key (with written
justifications) is `kvstore/student_config_solution.json` — **instructors should not surface
this to attendees**; it's the spoiler.

The five incidents map to specific config parameters:

| Parameter | Incident | The lesson |
|---|---|---|
| `rate_limit_window` | INC-1 | window so short it resets between bursts → sustained floods get through |
| `auto_spawn_delay` | INC-2 | respawn so aggressive a network blip spawns a "ghost" duplicate node |
| `read_quorum` (R) | INC-3 | `W + R ≤ N` → stale cart data |
| `write_quorum` (W) | INC-4 | `W` too high → one node loss kills all writes |
| `followers` (N) | INC-5 | over-provisioned → over budget |

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
   "before" state**, and confirms ports are free between cases. Expect **20/20 cases pass**
   (~3.5 min). Re-run it after *any* edit to a coordinator/registry/node/incident/assessment or
   to `tools/up.sh`/`down.sh` — it is your correctness gate.
3. **Rehearse the human flow** end-to-end: `make start`, then walk `00 → 10` using
   gap/up/incident/reset. The regression suite proves correctness mechanically; the rehearsal is
   about *pacing* and the couple of machine-dependent thresholds (see 8.4).

### 8.2 Pacing

There are 11 stages but only **4 require writing code** (`03, 04, 05, 08`) — budget the most
time there. The config/observe stages move fast and are where you narrate the concept. Give the
room a hard checkpoint at each **chapter boundary** (after 04, after 07): everyone runs
`make reset STAGE=04` / `make reset STAGE=07` so the whole room re-synchronizes regardless of who
fell behind.

### 8.3 Framing (the talking points that make it land)

- **The GIL = Redis's single thread for free.** Stage 01's single-thread ceiling is the exact
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

- **`incident_01`** asserts a p95 latency budget (`P95_BUDGET_MS=300`). It passes comfortably on
  normal hardware. If it flakes on a slow laptop, widen it via the env var rather than weakening
  the suite: `P95_BUDGET_MS=500 make incident STAGE=01`.
- **`incident_03`** compares adaptive vs round-robin p95 (relative, not absolute) — robust, but
  it's the other one that depends on the machine.

### 8.5 Foot-guns (these have cost real time — honor them)

- **Always clean up with `make down`.** It kills processes by script name *and* by port, so it
  catches orphaned `uvicorn --workers` workers (whose command line is just `python`). A plain
  `pkill -f node.py` misses those and they keep serving stale data.
- **Confirm ports are free between runs** if you suspect leftovers:
  `ss -ltn | grep -cE ':5001|:7000|:9000'` should print `0`.
- **Never `pkill -f coordinator.py` from a script whose own text contains that string** — it
  SIGKILLs itself. `make down` is the safe default; the regression suite already handles this
  correctly.

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `make up` fails with "address already in use" | a previous stage's process is still holding the port | `make down`, then retry |
| Reads return stale / wrong data for no reason | orphaned followers from a prior run on `7002–7004` | `make down`; confirm `ss -ltn \| grep -cE ':7000\|:9000'` is `0` |
| `NotImplementedError: STAGE NN: …` | you're on a code stage and the gap isn't filled | implement the function in `kvstore/`, or `make reset STAGE=NN` to see the solution |
| An attendee is hopelessly behind | — | `make reset STAGE=NN` jumps their `kvstore/` to a known-good stage instantly |
| `incident_01` fails on a slow machine | p95 budget too tight for that hardware | `P95_BUDGET_MS=500 make incident STAGE=01` |
| `make: command not found` | you're on the host, not in the container | `docker-compose exec workshop bash` then `cd build-kvstore` |
| Lost all your edits | you ran `make start`/`make gap`/`make reset` (they overwrite `kvstore/`) | expected — `kvstore/` is disposable; commit your own work elsewhere if you want to keep it |

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
| `build-kvstore/docs/bugs-fixed.md` | Running log of bugs found & fixed during verification |
| `build-kvstore/checkpoints/NN-*/` | Frozen, known-good snapshot of each stage |
| `build-kvstore/stages/{03,04,05,08}/` | Gapped starting points for the code stages |
| `build-kvstore/incidents/` | The black-box red→green incident scripts |
| `build-kvstore/kvstore/` | The working dir attendees edit (gitignored; seeded by `make start`) |

### Why decisions were made the way they were

See [`wiki/decisions/`](wiki/decisions/) (indexed in
[`wiki/decisions/INDEX.md`](wiki/decisions/INDEX.md)) — in particular the three
`build-kvstore` entries covering the incremental restructure, the checkpoint build approach, and
the regression suite.
