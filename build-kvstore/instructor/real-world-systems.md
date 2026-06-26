# Real-World Systems — Stage by Stage

Each stage of the KV-store workshop maps directly to battle-tested patterns in production infrastructure. This report connects what you're building to the systems that pioneered (or popularized) each concept.

---

## Stage 00 — Single Node: A Dict Behind HTTP

**Real-world example: Redis (single-instance mode)**

Redis at its core is an in-memory hash-map exposed over a TCP protocol (RESP). When you run `redis-server` on a single box, it is fundamentally a dictionary behind a network interface — exactly what Stage 00 builds over HTTP. Every `GET key` → hash lookup, every `SET key value` → hash insertion. Memcached follows the same model: an in-memory hash table behind a text/binary protocol.

**Why this matters:** Almost every caching layer in production (Instagram's cache tier, Twitter's timeline cache, GitHub's session store) started as "a dictionary behind a network endpoint." The simplicity is the point — you prove the data model works before worrying about scale.

> **Also see:** etcd v1 was a single-node key-value store behind HTTP/JSON before it became a distributed system. The "dict behind HTTP" pattern is the universal starting point.

---

## Stage 01 — Vertical Scaling: The Single-Thread Ceiling

**Real-world example: Redis's deliberate single-threaded design**

Redis famously runs your commands on **one thread**. Salvatore Sanfilippo (antirez) chose this deliberately: a single thread means zero lock contention, predictable latencies, and atomic operations for free. But it also means one CPU core is your ceiling — if your command is CPU-heavy (a large `SORT`, `KEYS *`, or a Lua script), every other client waits.

**How Redis scales vertically:** Redis 6.0+ introduced **I/O threads** (multi-threaded I/O for parsing and writing, but still single-threaded command execution). This is exactly analogous to Stage 01 running multiple `uvicorn` workers behind the GIL — the GIL serializes Python execution just like Redis serializes command execution, and you scale by running multiple workers/processes on the same box.

**Also see:**
- **Node.js** has the same single-thread model (the event loop). You scale vertically with the `cluster` module, which forks worker processes — same box, more cores.
- **Nginx** uses a multi-worker, single-threaded-per-worker model. The master process forks N workers (typically one per CPU core), each running an event loop.

### Deep Dive: Is the Fibonacci Load Factor a Real Analogy or a Shallow Trick?

**Short answer: it's structurally accurate.** The Fibonacci function itself is a toy, but what it *simulates* — a CPU-bound operation that monopolizes a single thread and serializes all concurrent requests behind it — is exactly what happens in production systems. The workshop's `--load-factor 28` flag produces a ~50–100ms compute spike per request. That's not arbitrary; it's calibrated to feel like a real per-request cost that a single thread can't parallelize.

**What the workshop is actually modeling:**

Every request to the node calls `simulate_cpu_load(LOAD_FACTOR)` — a naive recursive `fib(28)` — *before* touching the dict. Because Python's GIL ensures only one thread runs Python bytecode at a time, concurrent requests **queue behind the Fibonacci computation**. With 10 concurrent requests and 1 worker, the 10th request waits for 9 × ~80ms ≈ 720ms before it even starts. That's the choking.

This is **not** a pseudo-analogy. Here's why:

**1. Redis's `KEYS *` and `SORT` — the exact same choking**

Redis is single-threaded by design. When you run `KEYS *` on a database with millions of keys, it scans the entire keyspace **on the main thread**. Every other client command — `GET`, `SET`, `INCR` — waits. The documentation literally warns: *"KEYS should only be used in production environments with extreme care. It may ruin performance when it is executed against large databases."* This is the Fibonacci analogy made real: one expensive computation blocks all concurrent operations because they share a single execution thread.

Other Redis commands that exhibit this:
- `SORT` on large lists (CPU-bound comparison)
- `LRANGE 0 -1` on million-element lists (serialization cost)
- Lua scripts via `EVAL` (the entire script runs atomically on the main thread)
- `SAVE` (foreground persistence — blocks everything; production uses `BGSAVE` on a fork to avoid exactly this)

**2. Node.js event loop blocking — the JavaScript equivalent**

Node.js is single-threaded like Redis. If a request handler does something CPU-intensive — JSON parsing a 50MB payload, image resizing, bcrypt hashing, PDF generation — it blocks the event loop, and every other request queues behind it. The Node.js documentation calls this *"the danger of event loop blocking."*

Companies like PayPal and Netflix explicitly offload CPU-heavy work to worker threads (Node's `worker_threads` module) or external processes — the same pattern as Stage 01's multi-worker fix.

**3. Garbage collection pauses — the JVM "stop the world"**

In Java/JVM systems (Cassandra, Elasticsearch, Kafka, HBase), a full GC pause stops **all application threads** while the garbage collector scans and compacts the heap. During a GC pause:
- Cassandra stops processing read/write requests and may be marked dead by the gossip protocol.
- Kafka brokers miss heartbeats and trigger partition reassignment.
- Elasticsearch nodes miss cluster health pings.

A GC pause is structurally identical to the Fibonacci choke: a CPU-bound operation (GC scanning/marking) that serializes all productive work on the node. The difference is that GC is involuntary — you don't ask for it, it just happens. LinkedIn's engineering blog has documented how multi-second GC pauses in their Kafka brokers caused cascading partition leader elections.

**4. TLS handshake storms — CPU choking at the edge**

When Cloudflare or an Nginx proxy handles thousands of new TLS connections per second, the asymmetric cryptography (RSA/ECDSA key exchange) is pure CPU work. During traffic spikes, TLS handshakes can saturate a single core and queue incoming connections. Cloudflare moved to hardware crypto offload and multi-process `nginx` workers to parallelize — the exact same "vertical scaling" solution as Stage 01.

**5. Heterogeneous nodes in production — the Stage 02/03 weak node**

The workshop runs node-1 with `--workers 1` (weak) and nodes 2–3 with `--workers 4` (strong), all with the same `--load-factor 28`. This heterogeneity isn't contrived either:

| Real scenario | Why nodes differ | Effect |
|---|---|---|
| **Mixed-generation hardware** | Gradual fleet upgrades (old servers alongside new) | Old nodes have fewer cores, less cache — same workload takes longer |
| **Noisy neighbors** (cloud/VMs) | Co-tenants on the same physical host consume CPU | One VM is throttled while others run free |
| **Thermal throttling** | A server in a hot rack reduces clock speed | Same code, 30% slower |
| **GC pressure** (JVM services) | One node has a fuller heap, triggers more GC | Intermittently slower than peers |

Google's Borg scheduler, AWS's placement groups, and Netflix's Titus container scheduler all deal with this reality. Round-robin ignores it; adaptive routing (Stage 03) compensates for it — and that's exactly why real systems like Envoy and HAProxy default to least-connections rather than round-robin.

**The verdict:**

The Fibonacci function is a **synthetic stand-in**, but the phenomenon it produces — a CPU-bound task serializing concurrent requests behind a single-threaded execution model — is **identical in structure** to what Redis, Node.js, JVM-based datastores, and TLS-heavy proxies experience in production. It's not a metaphor; it's the same queueing behavior with a different function on the call stack. The GIL is Redis's single thread. The `--load-factor` flag is `KEYS *` or a GC pause. The multi-worker fix is `redis-server` × N instances.

---

## Stage 02 — Horizontal Scaling: More Nodes, Diverging Copies

**Real-world example: Early Memcached clusters / naive Redis multi-node**

Before Redis Cluster existed, teams ran multiple independent Redis instances. Each node held a *different subset* of data — there was no automatic data sharing. If you wrote `user:123` to node A, reading from node B returned nothing. The data was split, not replicated.

This is exactly what Stage 02 demonstrates: three nodes with separate dicts. The data diverges because there's no replication — each node is an island.

**How the real world solved it:**
- **Memcached** embraced this with **consistent hashing** (introduced by the Ketama algorithm at Last.fm) — the *client* decides which node owns which key, so the split is intentional and balanced. But if a node dies, its partition is gone.
- **Redis Cluster** (v3.0+) formalizes this with **hash slots** — 16,384 slots distributed across nodes. Each key hashes to a slot, each slot lives on one master. The split is now managed, not accidental.

> **The lesson Stage 02 teaches:** horizontal scaling without coordination just fragments your data. That pain motivates replication (Stage 05) and load balancing (Stage 03).

---

## Stage 03 — Load Balancing: Round-Robin vs. Adaptive Routing

**Real-world example: Nginx, HAProxy, and the "Power of Two Choices"**

| Strategy | Who uses it | How it works |
|---|---|---|
| **Round-robin** | Nginx (default), AWS ELB Classic | Requests are dealt like cards — 1, 2, 3, 1, 2, 3… Blind to node health or capacity. |
| **Least connections** | HAProxy, Nginx (`least_conn`), AWS ALB | Route to the node handling the fewest in-flight requests. Adapts to slow nodes. |
| **Power of two random choices** | Envoy proxy, Netflix Zuul 2 | Pick 2 random nodes, send to the one with fewer connections. Near-optimal with minimal state. |
| **Weighted round-robin** | Nginx (`weight`), Kubernetes Services | Like round-robin but nodes with more capacity get more turns. |

**The workshop's adaptive strategy** (pick the node with the lowest score based on active connections and latency) is closest to HAProxy's `leastconn` or Envoy's load-aware routing. The key insight is the same: a dumb round-robin sends equal traffic to a 1-worker node and a 4-worker node, so the weak node becomes the bottleneck that drags the global p95.

**Netflix's real-world story:** Netflix's Ribbon client-side load balancer (now replaced by Spring Cloud LoadBalancer) started with round-robin and moved to a zone-aware, weighted strategy that factors in active connections, server health, and zone proximity — the same evolution Stage 03 teaches.

---

## Stage 04 — Rate Limiting: Protecting the Store from Floods

**Real-world example: Redis-backed rate limiters (used by GitHub, Stripe, Cloudflare)**

The **fixed-window counter** pattern you implement in Stage 04 is the same one Redis's documentation recommends using `INCR` + `EXPIRE`:

```
INCR  user:123:rate_limit       → count
EXPIRE user:123:rate_limit 60   → reset after window
```

If `count > limit`, reject with **HTTP 429**.

**Who uses what:**

| Algorithm | Used by | Trade-off |
|---|---|---|
| **Fixed window** (Stage 04) | GitHub API, early Stripe | Simple. Allows burst at window boundary (2× limit if bursts straddle the reset). |
| **Sliding window log** | Slack API | Tracks every request timestamp. Precise but memory-heavy. |
| **Token bucket** | AWS API Gateway, Google Cloud | Smooth bursts. Tokens refill at a constant rate; each request consumes one. |
| **Leaky bucket** | Nginx (`limit_req`), Shopify | Requests queue and drain at a fixed rate. Smooths traffic like a funnel. |
| **Sliding window counter** | Cloudflare | Hybrid: interpolates between the previous and current fixed window. Near-precise with low memory. |

**Cloudflare's real-world story:** Cloudflare processes 50M+ requests/second. Their rate limiter uses a sliding-window counter backed by a distributed counting system. When traffic spikes (DDoS), the rate limiter is the first line of defense — exactly the "protecting the store from floods" role Stage 04 teaches.

---

## Stage 05 — Replication: Single-Leader (Primary–Replica)

**Real-world example: Redis primary–replica replication / MySQL replication / PostgreSQL streaming replication**

Redis replication works almost exactly like Stage 05:
1. One **leader** (primary) accepts all writes.
2. The leader **pushes** every write to its **followers** (replicas) asynchronously.
3. Followers serve **read traffic** — they are read replicas.

This is **single-leader replication** — the same pattern described in Chapter 5 of *Designing Data-Intensive Applications* (Martin Kleppmann).

**Who uses this pattern:**

| System | Leader | Followers | Async/Sync |
|---|---|---|---|
| **Redis** | Primary | Replicas (`REPLICAOF`) | Async by default (configurable `WAIT`) |
| **MySQL** | Source | Replicas (binlog replication) | Async by default, semi-sync optional |
| **PostgreSQL** | Primary | Standbys (WAL streaming) | Async or synchronous (per-standby) |
| **MongoDB** | Primary | Secondaries (oplog replication) | Configurable via write concern |
| **Kafka** | Partition leader | In-Sync Replicas (ISR) | Leader waits for ISR acks |

**Why the leader holds the only copy is dangerous (Stage 05's lesson):** In 2017, GitLab suffered a data loss incident when their only primary PostgreSQL node's data was accidentally deleted. Without up-to-date replicas, 6 hours of data were lost. Stage 05's "stranded data" incident is exactly this scenario in miniature.

---

## Stage 06 — Synchronous Replication: W = N, No Stale Reads

**Real-world example: PostgreSQL synchronous standby / MySQL semi-synchronous replication**

PostgreSQL's `synchronous_commit = on` with `synchronous_standby_names = '*'` makes the primary wait for **every** standby to confirm the write before returning to the client. This is exactly `W = N`:

- ✅ **No stale reads** — every replica has every committed write.
- ❌ **Zero fault budget** — if *any* standby is down or slow, writes stall.

**MySQL's semi-synchronous replication** is a practical middle ground: the primary waits for *at least one* replica to acknowledge — `W = 2` out of `N` replicas. This directly foreshadows Stage 07's quorum.

**Google Spanner's extreme version:** Spanner uses synchronous replication via **Paxos** across datacenters. Every write is synchronously replicated to a majority — but Spanner has the hardware (atomic clocks, TrueTime) to make the latency tolerable. For most systems, `W = N` is a trap — which is exactly what Stage 07 reveals.

---

## Stage 07 — Quorum & Fault Tolerance: W + R > N and CAP

**Real-world example: Amazon DynamoDB / Apache Cassandra tunable consistency**

This is the **Dynamo model**, from Amazon's [2007 Dynamo paper](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf). The core rule:

> **W + R > N guarantees overlap**: at least one node in the read set saw the latest write.

| System | Default N | Tunable W | Tunable R | Default consistency |
|---|---|---|---|---|
| **DynamoDB** (original) | 3 | Configurable | Configurable | Eventually consistent reads (R=1) or strongly consistent (R=N) |
| **Apache Cassandra** | 3 (typical RF) | `ONE`, `QUORUM`, `ALL` | `ONE`, `QUORUM`, `ALL` | Tunable per query |
| **Riak** | 3 | Tunable | Tunable | AP by default (tunable toward CP) |
| **Voldemort** (LinkedIn) | 3 | Tunable | Tunable | AP-leaning |

**The CAP moment Stage 07 reveals** is exactly the CP/AP trade-off:
- **CP (what Stage 07 does):** Refuse writes when quorum can't be reached → preserves consistency, sacrifices availability. **HBase, Google Spanner, etcd, ZooKeeper** make this choice.
- **AP (the alternative):** Accept writes even during partitions, reconcile later (last-writer-wins, vector clocks, CRDTs). **Cassandra (default), DynamoDB, Riak** make this choice.

**Cassandra's real-world example:** Instagram uses Cassandra with `QUORUM` writes and `QUORUM` reads (W=2, R=2, N=3) for their feed storage — exactly the `W + R > N` majority quorum. They tolerate one node failure without losing consistency or availability. When they need speed over freshness (e.g., suggested users), they drop to `R=ONE`.

---

## Stage 08 — Service Discovery: Heartbeats That Detect Death

**Real-world example: etcd + Kubernetes / Consul / ZooKeeper / Redis Cluster gossip**

| System | Discovery mechanism | Heartbeat model |
|---|---|---|
| **Kubernetes (via etcd)** | Nodes send heartbeats to the API server; the API server marks a node `NotReady` after the timeout (default 40s). | Push-based: kubelet → API server |
| **Consul** (HashiCorp) | Agents run on every node and gossip membership using the **Serf protocol** (SWIM-based). Health checks run locally. | Gossip: peer-to-peer, probabilistic |
| **ZooKeeper** | Clients maintain **ephemeral nodes** with session heartbeats. If the session times out, the node disappears — watchers are notified. | Session-based: client → ZK ensemble |
| **Redis Cluster** | Every node pings every other node; if a majority agrees a node is unreachable, it's marked `PFAIL → FAIL`. | Gossip: peer-to-peer, quorum confirmation |
| **Eureka** (Netflix) | Services register and send heartbeats every 30s. If 3 heartbeats are missed, the instance is evicted. | Push-based: service → registry |

**Stage 08's model** (nodes POST heartbeats to a central registry; the registry marks them dead after a timeout) is closest to **Eureka** or **Kubernetes's kubelet heartbeats**. It's the simplest correct design: push-based, centralized, with a configurable TTL.

**Netflix's real story:** Netflix's Eureka handles service discovery for 1000+ microservices. Each service instance sends a heartbeat every 30 seconds. If 3 consecutive heartbeats are missed (90s), the instance is evicted from the registry. During AWS outages, Eureka enters "self-preservation mode" — it stops evicting instances to avoid cascading failures when the problem is network-wide, not per-instance.

---

## Stage 09 — Auto-Recovery: Respawn + Catchup (Follower Recovery)

**Real-world example: Redis PSYNC resync / Kubernetes Pod auto-restart / Cassandra node repair**

**Redis's recovery flow** is almost identical to Stage 09:
1. **Detection:** Redis Sentinel monitors replicas via heartbeats.
2. **Respawn:** Sentinel can promote a new replica or restart the crashed one.
3. **Catchup:** The replica reconnects and issues `PSYNC` — if the replication backlog still has the missing data, it does a **partial resync** (just the delta). If too much was missed, it falls back to a **full resync** (the leader snapshots its entire dataset via `BGSAVE` and streams it to the replica).

Stage 09's "snapshot catchup" maps to Redis's full resync — the leader's entire state is copied to the new follower.

| System | Detection | Respawn | Catchup |
|---|---|---|---|
| **Redis Sentinel** | Heartbeat-based | Configurable (manual or auto) | `PSYNC` partial/full resync |
| **Kubernetes** | Liveness/readiness probes | Automatic Pod restart (kubelet) | Application-level (re-pull state from peers) |
| **Cassandra** | Gossip protocol | Manual (`nodetool`), or operator-managed | `nodetool repair` (Merkle-tree anti-entropy) |
| **Kafka** | ISR tracking by controller | Automatic (broker restart) | Follower fetches from leader's log from last offset |
| **Elasticsearch** | Cluster state via master node | Shard reallocation | Shard recovery (copy segments from primary) |

**Kubernetes' real-world story:** When a Pod dies (OOMKilled, crash, node failure), the kubelet restarts it automatically. For stateful workloads (StatefulSets), the new Pod mounts the same persistent volume and replays from its last checkpoint. This is the same "respawn + catchup" loop — the platform handles the resurrection, the application handles the state recovery.

> **The scope caveat (important):** Stage 09 recovers *followers*. Recovering the *leader* (promoting a follower to leader) is **leader election** — that's Redis Sentinel, Raft (etcd), or ZAB (ZooKeeper). This workshop explicitly stops short of that, and so should your mental model here.

---

## Stage 10 — Full System: Gateway + Whole-System Synthesis

**Real-world example: A modern production stack (Cloudflare → API Gateway → Application → Database cluster)**

Stage 10 assembles every piece into a production-like topology:

```
Client → Gateway (edge) → Coordinator → Leader + Followers
              ↑                              ↑
         Rate limiter                   Registry + heartbeats
```

This maps to real-world architectures:

| Workshop layer | Real-world equivalent | Example |
|---|---|---|
| **Gateway** (`:8000`) | Edge proxy / API gateway | Cloudflare Workers, AWS API Gateway, Kong, Nginx |
| **Rate limiter** (on gateway) | Edge rate limiting | Cloudflare Rate Limiting, AWS WAF rate rules |
| **Coordinator** (`:7000`) | Cluster coordinator / router | Redis Cluster's smart client, Cassandra coordinator node, MongoDB `mongos` |
| **Leader** (`:7001`) | Primary / write node | Redis primary, PostgreSQL primary, Kafka partition leader |
| **Followers** (`:7002–7004`) | Read replicas | Redis replicas, PostgreSQL hot standbys, Kafka ISR followers |
| **Registry** (`:9000`) | Service discovery | etcd, Consul, ZooKeeper, Eureka |
| **Auto-respawn + catchup** | Self-healing | Kubernetes + Redis PSYNC, Kafka ISR catch-up |

**A real system that looks like this:** **Redis in production at a company like Stripe or Instacart:**

1. Client hits **Cloudflare** (edge proxy with rate limiting).
2. Request reaches an **API Gateway** (Kong or custom) that routes to the appropriate service.
3. The service talks to **Redis Cluster**, where a **coordinator** (smart client) routes writes to the correct **primary** and reads to **replicas**.
4. **Redis Sentinel** monitors health via heartbeats and auto-promotes if a primary fails; replicas resync via `PSYNC`.
5. **Consul** or **Kubernetes** handles service discovery for the application tier.

**From a dict to a distributed system:** Stage 10 is the moment you zoom out and realize the toy you've been building has the same bones as the systems that run billions of requests per day. The difference is battle-hardening, edge cases, and years of operational pain — but the architecture is the same.

---

## Summary Table

| Stage | Concept | Real-world system(s) | Key pattern |
|---|---|---|---|
| 00 | Single node | Redis single-instance, Memcached | In-memory dict behind a protocol |
| 01 | Vertical scaling | Redis single-thread, Node.js event loop | Scale by forking workers, not by threading |
| 02 | Horizontal scaling | Memcached consistent hashing, Redis Cluster hash slots | Multiple nodes = split data without coordination |
| 03 | Load balancing | Nginx, HAProxy, Envoy (power-of-two-choices) | Adaptive > round-robin when nodes differ |
| 04 | Rate limiting | Cloudflare, GitHub API, Stripe (Redis `INCR`+`EXPIRE`) | Fixed-window counter; 429 at the edge |
| 05 | Replication | Redis `REPLICAOF`, PostgreSQL streaming, MySQL binlog | Single-leader → followers (async) |
| 06 | Sync replication | PostgreSQL `synchronous_commit`, MySQL semi-sync | W=N: consistent but zero fault budget |
| 07 | Quorum + CAP | DynamoDB, Cassandra (`QUORUM`), Riak | W+R>N; CP vs AP is a configuration knob |
| 08 | Service discovery | etcd/Kubernetes, Consul, Eureka, ZooKeeper | Push heartbeats → TTL-based death detection |
| 09 | Auto-recovery | Redis `PSYNC`, Kubernetes Pod restart, Kafka ISR | Respawn + snapshot catchup |
| 10 | Full system | Redis Cluster + Sentinel + edge proxy (production stack) | Every layer composes into one self-healing system |
