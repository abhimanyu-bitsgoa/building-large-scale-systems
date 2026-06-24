# Build-a-KVStore (workshop)

Build a distributed key-value store from scratch — single-leader replication and snapshot
resync **like Redis**, tunable read/write quorums **like Dynamo** — and watch it survive
failures we inject ourselves. You start with a single in-memory dict behind HTTP and grow it,
one earned step at a time, into a fault-tolerant cluster with a gateway, service discovery,
heartbeats, and automatic recovery.

> See [`SPEC.md`](SPEC.md) for the full design. Everything runs **inside the Docker container**
> (`docker-compose exec workshop bash`).

## How a stage works

Every stage is motivated by an **incident** — a script that breaks the system you have and
only passes once you've added the next feature.

```bash
make start              # seed kvstore/ from checkpoint 00 (do this once)
make up STAGE=03        # start the system for this stage
make incident STAGE=03  # ❌ reproduce the incident…
#   …you add the feature in kvstore/ (or change config)…
make incident STAGE=03  # ✅ until it passes
make status             # see the ladder of resolved incidents
```

Fell behind or broke something? Jump straight to a known-good state:

```bash
make reset STAGE=03     # kvstore/ becomes the correct, working stage-03 code
```

## The ladder

| # | Stage | You learn |
|---|---|---|
| 00 | single node | a KV store is a dict behind HTTP |
| 01 | vertical scaling | the single-thread ceiling (the GIL gives us Redis's one thread for free) |
| 02 | horizontal scaling | more nodes, and why naive copies diverge |
| 03 | load balancing | round-robin vs adaptive routing |
| 04 | rate limiting | protecting the store from floods |
| 05 | replication | single-leader replication |
| 06 | quorum | `W + R > N` and stale reads |
| 07 | fault tolerance | quorum loss and the CAP tradeoff |
| 08 | service discovery | heartbeats that detect death |
| 09 | auto-recovery | respawn + catchup (follower recovery) |
| 10 | full system | gateway + the capstone |
