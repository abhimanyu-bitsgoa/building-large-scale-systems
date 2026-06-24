# Stage-by-stage guide

The loop for every stage: **run the incident** (watch it fail) → **make the change** → **run it
again** (watch it pass). `⌨️ code` = you write code (start from `make gap STAGE=NN`); the rest are
config/observe. Stuck? `make reset STAGE=NN` jumps you to a known-good solution.

| | command |
|---|---|
| begin | `make start` |
| load a code-stage gap | `make gap STAGE=NN` |
| run the stage | `make up STAGE=NN` (separate shell) |
| check red→green | `make incident STAGE=NN` |
| rescue | `make reset STAGE=NN` |
| progress | `make status` |

---

## 00 — Single node
**Idea:** a KV store is a dict behind HTTP. `POST /data`, `GET /data/{key}`.
**Anchor:** Redis is an in-memory keyspace (we skip persistence).

## 01 — Vertical scaling
**Incident:** one node saturates under concurrent load — its single thread (the GIL) is the
ceiling, exactly the constraint Redis chose on purpose.
**Do:** scale the node up with `--workers`. *(config)*
**Anchor:** Redis is single-threaded; you run more instances to use more cores.

## 02 — Horizontal scaling
**Incident:** a single node is a SPOF and a capacity wall.
**Do:** run 3 nodes; the client spreads load across them. *(config)*
**Note:** independent nodes have *separate* dicts — naive horizontal scaling splits your data,
which is exactly what motivates replication (stage 05).

## 03 — Load balancing ⌨️ code
**Incident:** round-robin ignores capacity and tanks on the slow node.
**Do:** implement `AdaptiveStrategy.get_node` in `load_balancer.py` (pick the lowest-score node).
**Anchor:** power-of-two-choices / least-connections (Nginx, HAProxy, Netflix).

## 04 — Rate limiting ⌨️ code
**Incident:** a flood overwhelms the node.
**Do:** implement `FixedWindowStrategy.is_allowed` in `rate_limiter.py`.
**Anchor:** the classic Redis `INCR`+`EXPIRE` fixed-window limiter.

## 05 — Replication ⌨️ code
**Incident:** a write to the leader never reaches the followers (data isn't durable).
**Do:** implement `replicate_to_follower` in `node.py` (POST the write to `/replicate`).
**Anchor:** Redis primary–replica asynchronous replication.

## 06 — Quorum
**Incident:** a read right after a write is **stale** (W+R ≤ N).
**Do:** raise the read quorum `R` until `W + R > N`. *(config)*
**Anchor:** Dynamo/Cassandra tunable consistency. *(Read quorums are a leaderless idea — a
deliberate twist on our single-leader store so staleness is observable.)*

## 07 — Fault tolerance (CAP)
**Incident:** killing `floor(N/2)` followers with too-tight `W` → total write outage (503).
**Do:** lower `W` so the cluster tolerates `floor(N/2)` failures. *(config)*
**Anchor:** the CAP choice — when quorum is lost we reject writes (consistency over availability).

## 08 — Service discovery ⌨️ code
**Incident:** the registry never sees a node, so it can't detect its death.
**Do:** implement `heartbeat_loop` in `node.py` (POST to the registry every interval).
**Anchor:** Redis Cluster gossip / etcd / Consul heartbeats.

## 09 — Auto-recovery
**Incident:** a dead follower stays dead; the cluster runs degraded.
**Do:** enable `--auto-spawn`; the coordinator catches the new node up from the leader's snapshot.
*(config)*
**Anchor:** replacing a failed replica + full resync (Redis `PSYNC`). This is *follower* recovery —
not leader failover (that's Sentinel, out of scope).

## 10 — Full system + capstone
Put the **gateway** in front (rate limiting moves from the node to the edge — same
`rate_limiter.py`). Then play SRE: misconfigure what **we** built and run `make incident STAGE=10`
(the graded assessment) until it passes. Edit `kvstore/student_config.json`; the answer key is
`student_config_solution.json`.
