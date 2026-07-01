# Stage-by-stage guide

The loop for every stage: **run the incident** (watch it fail) → **make the change** → **run it
again** (watch it pass). `⌨️ code` = you write code (start from `make gap STAGE=NN`); the rest are
config/observe. Stuck? `make reset STAGE=NN` jumps you to a known-good solution.

| | command |
|---|---|
| begin | `make start` |
| load a code-stage gap | `make gap STAGE=NN` |
| run the stage | `make up STAGE=NN` (separate shell) |
| **play (any stage)** | `make lab STAGE=NN` — every process in its own tmux pane + a control pane to drive it by hand |
| check red→green | `make incident STAGE=NN` |
| rescue | `make reset STAGE=NN` |
| progress | `make status` |

> **`make lab` vs `make up`:** `make up` runs the stage in one shell (what the incident drives).
> `make lab` (any stage, **01–10**) is the *observe-and-play* view — every process gets its own
> pane so you watch them react, plus a control pane of helpers:
> - **01–04 (nodes):** `nwrite` / `nread` / `nhealth`, and `nload <strategy>` to fire load across
>   the cluster (compare `nload adaptive` vs `nload round_robin` on stage 03).
> - **05–10 (cluster):** `kvwrite` / `kvread` / `kvstatus`, plus `kvkill <n>` / `kvspawn` to crash
>   a follower and watch recovery yourself instead of only running the checker.
>
> Mouse mode is on (click a pane, scroll to read history). `WORKERS=1 make lab STAGE=02` demos the
> single-thread choke. Tear down with `make lab-down`.

> Want to see *what changes between stages and why* the system grows the way it does? Read
> [`diffs/README.md`](diffs/README.md) — the whole build as one narrative arc.

---

## 01 — Single node
**Idea:** a KV store is a dict behind HTTP. `POST /data`, `GET /data/{key}`.
**Anchor:** Redis is an in-memory keyspace (we skip persistence).

## 02 — Vertical scaling
**Incident:** one node saturates under concurrent load — its single thread (the GIL) is the
ceiling, exactly the constraint Redis chose on purpose.
**Do:** scale the node up with `--workers`. *(config)*
**Anchor:** Redis is single-threaded; you run more instances to use more cores.

## 03 — Horizontal scaling + load balancing ⌨️ code
**Incident (red):** one box is a SPOF and a capacity wall, so we run 3 *heterogeneous* nodes (one
weak, two strong). The simplest spread — **round-robin by turn** — is blind to capacity: it
bombards the weak node with its fair 1/3 share, the weak node queues, and the global p95 tanks.
**Do (green):** implement `AdaptiveStrategy.get_node` in `load_balancer.py` — **the file this stage
introduces** (pick the lowest-score node = latency + in-flight load). Adaptive steers traffic off
the weak node and the tail recovers. Compare `nload round_robin 96 12` vs `nload adaptive 96 12`.
**Note:** independent nodes also have *separate* dicts — naive horizontal scaling splits your data,
which is exactly what motivates replication (stage 05).
**Anchor:** power-of-two-choices / least-connections (Nginx, HAProxy, Netflix).
**Talk reference:** [`load-balancing-client-vs-server.md`](load-balancing-client-vs-server.md) —
client-side vs server-side load balancing (real systems + pros/cons), and how this lab moves from
one to the other.

## 04 — Rate limiting ⌨️ code
**Incident:** a flood overwhelms the node.
**Do:** implement `FixedWindowStrategy.is_allowed` in `rate_limiter.py`.
**Anchor:** the classic Redis `INCR`+`EXPIRE` fixed-window limiter.

## 05 — Replication ⌨️ code
**Incident:** a write to the leader never reaches the followers (data isn't durable).
**Do:** implement `replicate_to_follower` in `node.py` (POST the write to `/replicate`).
**Then observe (the hook into 06):** this stage runs a **weak quorum** (`W=1, R=1`, so `W+R ≤ N`).
The `R=1` read is served by an async follower lagging ~5s, so an update read straight back returns
the **old** value — a deterministic stale read. The win (data replicated, reads scale) comes with a
catch (stale reads), which motivates stage 06.
**Anchor:** Redis primary–replica asynchronous replication.

## 06 — Synchronous replication (no stale reads)
**Incident:** the stale read from stage 05 — a read right after an update lands on an async follower
that hasn't caught up.
**Do:** make **every follower synchronous** — raise `W` to `N` (launches `W=3, R=1`) so each write
reaches all followers before it returns. *(config)*
**Anchor:** synchronous replication / "write to everyone ⇒ read from anyone." *(Strong — but you'll
pay for it next stage: a write now needs every follower alive.)*

## 07 — Quorum & fault tolerance (CAP)
**Incident:** all-sync (`W=3=N`) tolerates **zero** failures — kill one follower and writes stop (503).
**Do:** switch to a **majority quorum** — `W=2, R=2`. It survives `floor(N/2)` failures *and* keeps
`W + R > N` so reads stay fresh. *(config)*
**Anchor:** Dynamo/Cassandra tunable consistency + the CAP choice (lost quorum → refuse writes to
keep consistency, the CP corner). The general rule: **W + R > N**; tune `W` along the CAP spectrum.

## 08 — Service discovery ⌨️ code
**Framing:** in 05-07 the coordinator only knew a node was gone because it removed it itself (an
administrative `/kill`). It has **no health loop** — an *unannounced crash* (`kvcrash`, a node dying
without going through the coordinator) is invisible to it. The registry adds the missing eyes.
**Incident:** crash a follower out-of-band; with no heartbeats the registry never saw the node, so the
coordinator keeps it `alive` and routes to a corpse.
**Do:** implement `heartbeat_loop` in `node.py` (POST to the registry every interval). Now the
registry detects the missed heartbeats and pushes `/node-died` to the coordinator.
**Anchor:** Redis Cluster gossip / etcd / Consul heartbeats (ephemeral membership).

## 09 — Auto-recovery
**Incident:** a crashed follower stays dead; the cluster runs degraded.
**Do:** enable the registry's `--auto-spawn`; on a detected crash it asks the coordinator to respawn
the follower, which then catches it up from the leader's snapshot. *(config)*
**Anchor:** replacing a failed replica + full resync (Redis `PSYNC`). This is *follower* recovery —
not leader failover (that's Sentinel, out of scope).

## 10 — Full system (synthesis demo)
Put the **gateway** in front (rate limiting returns to the edge — the same `rate_limiter.py`) and run
a 5-minute whole-system demo: `make lab STAGE=10`, then in the control pane trace one request end to
end (`kvwrite`/`kvread` → gateway → coordinator → leader → followers), shed load at the edge
(`kvflood`), and survive a crash (`kvcrash 1` → registry detects → auto-respawn + catchup → `kvread` still fresh).
*Note:* the gateway forwards to a single coordinator, so it doesn't load-balance — the routing
responsibility now lives server-side in the coordinator's quorum. There is **no incident** for this
stage: it's the synthesis of everything from 00–09, driven by hand.
