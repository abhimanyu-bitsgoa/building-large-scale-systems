# The build, one diff at a time — what changes between stages and why

This is the story of the system you build. Each stage adds **one capability**, and every
addition is forced by a problem you can *watch* the previous stage fail at (the `make incident
STAGE=NN` check). Read this top to bottom and the eleven checkpoints should feel like a single
arc — a dict behind HTTP growing, one earned step at a time, into a fault-tolerant cluster —
not eleven unrelated programs.

Two of the steps are big enough to be **new chapters** (they add whole files and reshape the
node); those get their own deep-dives, linked below. The rest are small, and several add *no
solution code at all* — they're a config flip plus a new thing to observe.

> How to read a transition: each section says **what the diff is** (files added / changed /
> removed) and **why** (the problem it solves). "No code change" means the *checkpoint* code is
> identical to the previous one — the stage is about configuration and observation, not new code.

```
00 ─ 01 ─ 02 ─ 03 ─ 04 ║ 05 ─ 06 ─ 07 ║ 08 ─ 09 ─ 10
 a dict   one box, then  ║  one logical  ║  the cluster heals
 behind   many boxes     ║  store across ║  itself, then gets
 HTTP     + a balancer   ║  many boxes   ║  an edge + capstone
                         ║  (replication)║  (discovery)
        CHAPTER 1 boundary ↑           CHAPTER 2 boundary ↑
```

A through-line worth noticing before you start: **the load balancer and rate limiter appear in
Chapter 1 (stages 03–04), disappear at stage 05, and come back at stage 10.** That's not churn —
it's the architecture talking. In the single-node era those concerns live *on the node*; once we
become a replicated cluster the interesting problem moves inside (replication, quorum), and the
edge concerns return at the very end where they belong in a real system: on a **gateway** in
front of everything. See [04→05](#0405--chapter-1-from-one-node-to-a-replicated-cluster) and
[09→10](#0910--an-edge-and-the-capstone).

---

## 00 → 01 — find the ceiling of a single box

- **Diff:** `node.py` only. Adds a CPU-load simulator (`simulate_cpu_load`, a deliberately naive
  recursive Fibonacci) and a `--workers` flag.
- **Why:** Stage 00 is a key-value store in its purest form — a Python `dict` behind two HTTP
  routes. The first question any system faces is *how far does one box go?* The Fibonacci load is
  a stand-in for real CPU work (think a `KEYS *` scan or a big serialization in Redis); under
  concurrency a single worker serializes on Python's GIL and latency falls off a cliff. Adding
  workers is **vertical scaling** — and it has a hard ceiling, which is exactly what motivates the
  next step.
- **Anchor:** Redis executes commands on one thread on purpose; you run more instances to use
  more cores. The GIL gives us that same one-thread constraint for free.

## 01 → 02 — one box becomes many

- **Diff:** Adds `client.py` — and *only* `client.py`. There is **no load balancer yet**: the
  client spreads requests across the three nodes by **naive round-robin**, a single inline counter
  (`node = nodes[i % len(nodes)]`). `node.py` is unchanged in spirit — you just run three of it.
- **Why:** A single box is both a capacity wall *and* a single point of failure. The cure is
  **horizontal scaling**: run N nodes and spread requests across them. The simplest possible spread
  is round-robin by turn, so that's where we start.
- **The pain it sets up (stage 03):** the three nodes are *heterogeneous* — one weak (1 worker), two
  strong (4 workers). Round-robin is blind to that, so a third of the traffic piles onto the slow
  node and the tail latency suffers. Run `nload 40 10` and watch node-1 drag the global p95.
- **The other catch (sets up stage 05):** these three nodes have *separate* dicts. Horizontal
  scaling naively **splits your data** — a key written to node 1 isn't on node 2. Hold that thought;
  it's the whole reason replication exists.

## 02 → 03 — route by capacity, not by turn

- **Diff:** **`load_balancer.py` appears** — this is the stage that introduces it. It brings the
  strategy pattern (`RoundRobinStrategy`, `AdaptiveStrategy`, power-of-two, weighted, random), and
  `client.py` is rewired to route through a `LoadBalancer` selected with `--strategy` instead of its
  old inline counter.
- **The exercise:** in the gapped start (`make gap STAGE=03`) you implement the one line at the
  heart of `AdaptiveStrategy.get_node` — pick the node with the lowest score (latency + in-flight
  load).
- **Why:** Round-robin (stage 02) is blind: it sends an equal share to a node that's already
  drowning. Adaptive routing watches each node and steers away from the slow one. Compare
  `nload round_robin 40 10` vs `nload adaptive 40 10` on the heterogeneous cluster — the difference
  in p95 is dramatic and visible. (This is **client-side** load balancing; see
  [`load-balancing-client-vs-server.md`](../load-balancing-client-vs-server.md).)
- **Anchor:** least-connections / power-of-two-choices (Nginx, HAProxy, Netflix).

## 03 → 04 — protect the node from a flood

- **Diff:** `node.py` gains rate-limit integration; adds `rate_limiter.py` (fixed-window strategy).
- **The exercise:** implement the core of `FixedWindowStrategy.is_allowed` — reset the counter when
  the window rolls over, allow while under the limit, reject once it's hit.
- **Why:** Load balancing shares load; it doesn't *cap* it. A burst still overwhelms a node. A rate
  limiter sheds excess traffic so the node survives. Fixed-window is the simplest such algorithm —
  and its boundary-burst weakness is a teaching point that pays off in the stage-10 capstone
  (incident INC-1).
- **Anchor:** the classic Redis `INCR`+`EXPIRE` fixed-window limiter.

---

## 04 → 05 — **CHAPTER 1: from one node to a replicated cluster**

This is the first big jump, and it has its own deep-dive: **[04-to-05-replication.md](04-to-05-replication.md)**.

- **Diff (in brief):** the single-tier era ends. `load_balancer.py` and `rate_limiter.py` leave the
  working set (edge concerns — they'll return at stage 10). `node.py` is reshaped from a standalone
  store into a **leader-or-follower** with a `/replicate` endpoint and sync/async replication.
  A brand-new **`coordinator.py`** appears in front: it takes every write, applies it to the leader,
  waits for `W` follower acks, and answers reads from `R` followers. The client now talks to the
  coordinator, not to individual nodes.
- **Why:** stage 02 left us with N independent dicts — data split across boxes, no safety. **Single-
  leader replication** turns N boxes into *one logical store with N copies*: write once, it lands on
  every replica, so any node can serve it and a node dying doesn't lose data.
- **The exercise:** implement the core of `replicate_to_follower` — the one POST that *is*
  replication (the leader sending a write to a follower).

## 05 → 06 — make stale reads impossible

- **Diff:** **No code change.** `up.sh` flips the quorum from `W=1,R=1` to `W=2,R=2`.
- **Why:** This is the heart of the whole workshop: **W + R > N**. With `W=1,R=1` on 3 followers,
  a write waits for only one replica and a read consults only one — they can miss each other, so an
  immediate read after a write can return a *stale* value (you watch this happen at stage 05).
  Raising R until `W + R > N` forces the read set and the write set to overlap on at least one node,
  so a read is guaranteed to see the latest write.
- **Anchor:** Dynamo/Cassandra tunable consistency. (Read quorums are a leaderless idea; we layer
  them onto our single-leader store *on purpose* so staleness is observable — say so out loud, or a
  sharp attendee will ask "why not just read the leader?")

## 06 → 07 — what happens when nodes die (CAP)

- **Diff:** **No code change.** Same `W=2,R=2`. The stage is operational, not additive.
- **Why:** With `W=2` on 3 followers you can lose `floor(N/2)` followers and still assemble a write
  quorum — the cluster serves through the failure. Kill one more and the quorum can't be met: writes
  return `503`. That refusal is a **choice**: when consistency can't be guaranteed we reject the
  write rather than accept a split-brain one. That's the **C-over-A** corner of CAP, made concrete.
- **Try it by hand:** `make lab STAGE=07`, then in the control pane `kvkill 1` (survives) and watch
  `kvstatus`; the incident kills `floor(N/2)` for you.

---

## 07 → 08 — **CHAPTER 2: the cluster learns who's alive**

The second big jump, with its own deep-dive: **[07-to-08-discovery.md](07-to-08-discovery.md)**.

- **Diff (in brief):** a new **`registry.py`** (a discovery service: nodes POST heartbeats to it; it
  prunes ones that go silent and answers `/nodes` and `/alive`) and a new **`catchup.py`**. `node.py`
  grows a `heartbeat_loop`, a `/snapshot` endpoint, a `/catchup` endpoint and a graceful deregister.
  `coordinator.py` learns to drive catchup and to react to a reported death.
- **Why:** through stage 07 the coordinator only *guessed* at liveness by polling health. Real
  clusters use **push-based heartbeats**: each node continuously says "I'm alive," and absence of
  that signal — not a failed poll — is what declares it dead. This is the foundation everything after
  it stands on: you can't *recover* a node until you can reliably *detect* its death.
- **The exercise:** implement the core of `heartbeat_loop` — the one POST a node sends the registry
  to announce it's alive.
- **Anchor:** etcd / Consul / Redis Cluster gossip.

## 08 → 09 — detection becomes recovery

- **Diff:** **No code change.** `registry.py` runs with `--auto-spawn --spawn-delay 5`.
- **Why:** Detecting death (stage 08) just gives you an accurate map of the damage; the cluster still
  runs degraded. With auto-spawn, a follower that stops heartbeating past the delay is **respawned**,
  and the coordinator **catches it up** from the leader's snapshot so it rejoins with the full
  dataset. Detection + recovery = a cluster that heals itself.
- **The footgun (capstone INC-2):** too *aggressive* a spawn-delay respawns a node that was only
  briefly slow, creating a duplicate "ghost." The delay is a real tuning decision.
- **Anchor:** replacing a failed replica + full resync (Redis `PSYNC`). Note this is *follower*
  recovery — not leader failover (that's Sentinel/Raft, deliberately out of scope).

## 09 → 10 — an edge, and the capstone

- **Diff:** the biggest additive stage. Adds **`gateway.py`** (the public edge) and — returning from
  Chapter 1 — **`load_balancer.py`** and **`rate_limiter.py`**, now applied at the gateway instead of
  on the node. Also adds `assessment.py`, the `*_config.json` files, and `scenario_brief.md`.
- **Why:** A real system doesn't expose its coordinator to the world. The gateway is the front door:
  it rate-limits, then forwards to the coordinator. This is where the edge concerns from stages 03–04
  come home — **rate limiting moved from the node to the edge**, which is why those files "left" at 05
  and return here. The `rate_limiter.py` you wrote at stage 04 is the very one the gateway imports.
- **The capstone:** mode switch from *builder* to *SRE*. You now own a working system and a stack of
  incident tickets (`scenario_brief.md`, the CloudCart story). You fix them by **tuning
  `student_config.json`** — not by editing code — and `make incident STAGE=10` grades you with
  `assessment.py`. Every knob maps to something you built: rate-limit window (INC-1), spawn-delay
  ghost nodes (INC-2), quorum staleness (INC-3), write-quorum fragility (INC-4), over-provisioning
  (INC-5).

---

## The arc in one paragraph

You start with a dict behind HTTP (00) and find the single-box ceiling (01). You go wide with
many nodes and a balancer (02–04) — and discover that wide-but-independent means split, unsafe
data. So you make the nodes *one logical store* with single-leader replication (05), tune the
quorum so reads can't go stale (06), and decide what to do when nodes die (07). To recover from
death you must first detect it, so you add heartbeat-based discovery (08), then automatic respawn
and catchup (09). Finally you put a real edge in front — a rate-limiting gateway — and step into
the SRE's chair to debug the system you built (10). Eleven steps, one store, every step earned by
a failure you watched.
