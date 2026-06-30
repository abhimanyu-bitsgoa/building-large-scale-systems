# Motivating Incidents — The Narrative Arc

**Purpose.** This is the *story* spine for the talk. Where [`real-world-systems.md`](real-world-systems.md)
answers *"what production system embodies this stage?"*, this report answers the question that comes
**first** in a presentation: *"why should anyone care about this stage at all?"* — by opening each
one with a **real outage or documented failure** from a planet-scale system.

Use it like this: **don't introduce a stage by naming its concept. Introduce it with the scar.**
Every layer we add to the KV store is something a real company added *after* it cost them an
outage, a data-loss event, or a front-page postmortem. Tell the failure first; let the room feel the
pain; *then* the fix (the stage) lands as inevitable instead of academic.

> **One honest framing for the whole talk (say it once, early):** the KV store you build is a
> *teaching model*, not a clone of any one system. The incidents below are the real-world motivation
> for each *concept* — they are not claims that our code reproduces those systems line for line.
> Where our model deliberately simplifies (e.g. quorum on a single leader, follower-only recovery),
> the per-stage **Caveat** says so. Honesty is part of the pitch.

The arc in one sentence: **a dict on one box → the same dict after it has survived a CPU meltdown, a
single-server collapse, a slow-node tax, a traffic flood, a data-loss event, a stale-read bug, a
zero-fault-budget stall, a discovery blackout, and a 3 a.m. page — which is to say, a real
distributed system.**

---

## Stage 01 — Single Node · *The origin story*

**The hook (say this):** *"Every database you've ever depended on started as a dictionary behind a
socket. Including the one most of this room has run in production."*

**What really happened.** In 2009, Salvatore Sanfilippo (antirez) was building **LLOOGG**, a
real-time web-analytics product. A single SQL database couldn't keep up with the write rate of a
live "who's on my site right now" feed. So he wrote a small in-memory data-structure server that was,
at its heart, a hash map behind a TCP socket. That throwaway tool became **Redis** — now one of the
most deployed datastores on earth. It began as exactly what Stage 01 is: `POST /data`, `GET
/data/{key}`, a dict behind a network endpoint.

**The lesson → why this stage exists.** You earn the right to talk about distribution by first
proving the data model on one box. Single-node is not a strawman to knock down — it's where every
real system *correctly* starts. Keep it boring on purpose; the simplicity is the control variable for
everything that follows.

**The arc (→ 02).** One box is wonderful right up to the first time it's busy. So let's make it busy.

---

## Stage 02 — Vertical Scaling · *The day one expensive request froze the planet*

**The hook (say this):** *"On July 2nd, 2019, a single regular expression took Cloudflare offline
worldwide. Not a DDoS. Not a bad deploy. One line of CPU-bound code that no other request could get
past."*

**What really happened.** Cloudflare pushed a WAF managed rule containing a regex that could
**catastrophically backtrack**. Each request that hit it burned CPU exponentially. Within minutes,
**CPU pegged at 100% across the fleet**, and because that CPU was the thing serving *everyone's*
traffic, global HTTP requests started failing with 502s for roughly half an hour. The fix was to
kill the rule and free the CPU — there was no horizontal trick that helped, because every core was
already busy doing the one expensive thing.

**The lesson → why this stage exists.** This is the single-thread ceiling made visible at planet
scale. One CPU-bound operation monopolizes the execution resource and **serializes every concurrent
request behind it** — exactly what our `--load-factor` Fibonacci does to a uvicorn worker, exactly
what Redis's single thread does during `KEYS *`, exactly what a GC pause does to a JVM node. The first
lever is *vertical*: give the box more parallel execution (more workers / more cores) so one slow
request can't hold the door shut for all the others.

**The payoff → scaling *up* is often the whole answer (the real motivation for this stage).** Be
honest about Cloudflare: it proves the ceiling is **real and brutal**, but it is *not* a "vertical
scaling cured it" story — the fix was to *kill the bad rule and free the CPU*; no amount of extra
compute out-runs an exponentially-backtracking regex. For the proof that *scaling up works*, look at
**Stack Overflow**: one of the busiest sites on earth (~half a billion page views a month) runs on a
*handful* of servers, with a single SQL primary that takes almost all the load — deliberately idling
around **5–10% CPU** for headroom. They scaled **up, not out, and never had to shard.** That is the
motivation for Stage 02: before you reach for distributed systems and all their pain, ask whether a
bigger box — or simply *using all of its cores* — would do. The everyday version of our `--workers`
fix is exactly that: `gunicorn`/`uvicorn --workers`, Node's `cluster` module, `nginx
worker_processes auto` — spend every core on the machine before you reach for a second machine.

**Caveat.** Cloudflare's meltdown was CPU exhaustion *across* many cores; our demo is one worker vs.
many — and, as above, its *fix* was removing the work, not adding compute. The shared structure —
*a CPU-bound task starving concurrent work* — is the real, transferable idea, not the core count.

**The arc (→ 03).** A bigger box has a bigger ceiling, but it's still a ceiling — and still one box.
Scaling up bought Stack Overflow everything; for others it eventually runs out of "bigger." What
happens when that box hits its wall, or simply dies?

---

## Stage 03 — Horizontal Scaling + Load Balancing · *The single server that became a national outage — then the tail-at-scale tax*

**The hook (say this):** *"For two years, the most famous image in tech was a whale being lifted by
birds — Twitter's 'Fail Whale.' It showed up every time one overloaded stack couldn't take the
spike."*

**What really happened.** Early Twitter ran a monolithic Rails app in front of a **single primary
MySQL** database. Every record-breaking moment — the 2010 World Cup, New Year's in Japan, a celebrity
death — drove a write/read spike the single primary couldn't absorb, and the whole site fell over.
The "Fail Whale" became a cultural meme precisely *because* the failure was so reliable: one box, one
point of failure, one capacity wall. Twitter's multi-year re-architecture into many services and
sharded/replicated storage was, in essence, the move from Stage 02 to everything after it.

**The modern echo (the bridge from Stage 02).** Stack Overflow scaled *up* and it was enough — but
vertical scaling has a hard edge, and **Figma** found it. For years all of Figma ran on a *single*
Postgres instance — **the largest box AWS would rent them.** That one machine carried the company to
millions of users (vertical scaling genuinely *works*) — until it ran out of room money couldn't buy:
Postgres `VACUUM` reliability problems and the **maximum IOPS RDS supports.** When "buy a bigger box"
has no bigger box left, you're out of vertical road and the only way forward is *more boxes.* That is
the exact moment Stage 03 begins.

**The lesson → why this stage exists.** A single node is two problems wearing one coat: a **capacity
wall** (it can only do so much) and a **single point of failure** (when it's gone, you're gone). The
first instinct is the right one: run *more* nodes. Stage 03 does exactly that — three independent
nodes, traffic spread by naive round-robin in the client.

**But notice the new pain (this is what going wide reveals):** three nodes with three *separate*
dicts means your data is now **split, not shared** — write `user:123` to node A and it's invisible
from node B. And blind round-robin sends equal traffic to unequal nodes. Going wide reveals two bills:
**replication** (data is split → paid at 05) and **load balancing** (round-robin is blind → paid
right now, in the second half of this stage).

**The arc (→ load balancing).** More nodes, but they're not equal — and round-robin doesn't know that.

### …and the second half of Stage 03: Load Balancing · *The tax you pay for your slowest node*

**The hook (say this):** *"At scale, your user's experience isn't decided by your average server. It's
decided by your worst one — and round-robin keeps feeding it traffic anyway."*

**What really happened.** Google's Jeff Dean and Luiz Barroso documented this in **"The Tail at
Scale"** (Communications of the ACM, 2013). When a request fans out across many machines, the slow
*tail* of any single machine — a GC pause, a hot disk, a noisy neighbor — dominates the latency the
user actually sees. A node that's fine 99% of the time still poisons your p99 *if your router is
blind to it*. Round-robin is blind to it: it deals requests like cards, 1-2-3-1-2-3, with no idea
that node 1 is a weak, single-worker box gasping under load. That's why production proxies — HAProxy
(`leastconn`), Nginx, Envoy (power-of-two-choices), Netflix's load balancers — moved *off* plain
round-robin toward routing that reacts to live load.

**The lesson → why this stage exists.** Spreading traffic isn't enough; you have to spread it
*toward capacity*. Stage 03 is the first code stage: implement `AdaptiveStrategy.get_node` to pick the
lowest-load node instead of the next one in line. In the dashboard, `nload round_robin 96 12` vs.
`nload adaptive 96 12` makes the weak node's "tax" appear and then vanish — the slow node stops
dragging p95 because adaptive routing stops over-feeding it.

**The arc (→ 04).** Now traffic flows to the healthy nodes. But what if *all* of them are healthy and
the problem is simply that there's **too much traffic** — some of it abusive?

---

## Stage 04 — Rate Limiting · *When your own clients DDoS you*

**The hook (say this):** *"The scariest flood isn't an attacker. It's ten thousand of your own
servers, all retrying at once, all politely hammering the one service they each need."*

**What really happened (two real shapes of the same flood):**

- **The outside flood — GitHub, Feb 28 2018.** GitHub absorbed what was then the **largest DDoS ever
  recorded — 1.35 Tbps** — via memcached amplification ("memcrashed"). Survival came from shedding
  the flood at the *edge* (routing through Akamai/Prolexic scrubbing) before it reached the
  application. The defense is a rate/volume gate in front of the store, not inside it.
- **The inside flood — AWS DynamoDB, Sept 20 2015 (US-EAST-1, ~5 hours, took down Netflix and
  others).** A brief blip caused DynamoDB's storage servers to re-request their membership data from
  an internal **metadata service**. The requests had grown large (Global Secondary Indexes inflated
  them), so they couldn't finish within the timeout — so the servers removed themselves and **retried,
  in a storm**, which overloaded the metadata service further. AWS broke the spiral by **pausing
  requests to the metadata service** (a rate limit!) to shed load, then adding capacity and raising
  the timeout. The flood here was *self-inflicted* — a retry storm.

**The lesson → why this stage exists.** A store with no intake valve will accept exactly enough load
to kill itself, from attackers and from its own clients alike. Stage 04 (second code stage)
implements the classic **fixed-window counter** — Redis's `INCR` + `EXPIRE` pattern — and returns
**HTTP 429** when a caller exceeds its budget. Discuss the known weakness (boundary bursts can allow
~2× at the window edge); that limitation is exactly why Cloudflare, Stripe, and others moved to
sliding-window and token-bucket variants.

**The arc (→ 05).** The store now survives load and abuse. But every byte still lives on one node.
Survive the *traffic* and you've still not survived the *machine*.

---

## Stage 05 — Replication · *The 300 GB that one command erased*

**The hook (say this):** *"On January 31st, 2017, a GitLab engineer ran a cleanup command on what they
thought was the replica. It was the primary. Three hundred gigabytes were gone in seconds — and the
backups didn't work."*

**What really happened.** During replication troubleshooting, an exhausted engineer ran `rm -rf` on
the PostgreSQL data directory of the **primary**, believing it was the secondary. ~300 GB vanished;
they stopped it seconds too late. Then the horror: **five different backup/replication mechanisms
were all silently broken or ineffective.** With no usable replica and no working backup, GitLab
restored from a ~6-hour-old staging snapshot and **permanently lost ~6 hours** of issues, merge
requests, comments, and ~5,000 projects' worth of data — narrated live to the internet on a public
livestream.

**The lesson → why this stage exists.** *The leader holding the only copy is the bug.* Replication is
what turns "one fragile copy" into "the write survives the machine." Stage 05 (third code stage)
implements `replicate_to_follower`: the leader POSTs every write to its followers, and — crucially in
our design — **reads are served by the followers.** So a write that *fails to replicate* is invisible:
the incident writes, waits, reads from the follower tier, and finds **nothing**. That "stranded data"
is the GitLab lesson in miniature: a copy that exists only on the leader is a copy you're one command
away from losing.

**The arc (→ 06).** Now the write reaches the followers. But our followers replicate *asynchronously*
— with deliberate, visible lag. So what does a user see if they read in that lag window?

---

## Stage 06 — Synchronous Replication · *The update that "didn't save" — but did*

**The hook (say this):** *"You change your privacy setting, hit save, the page reloads… and shows the
old setting. You didn't lose the write. You read a replica that hadn't caught up yet."*

**What really happened.** This is the everyday face of **replica lag**, and the engineers who run it
at scale have written about it at length. Facebook's **"Scaling Memcache at Facebook"** (NSDI 2013)
devotes real machinery to it: because reads hit replicas that trail the leader, users could **read
their own writes back as stale** — so Facebook added *leases* and cross-region *remote markers* purely
to stop users from seeing data older than what they just wrote. Every team that runs MySQL/Postgres
read replicas eventually hits the same wall and ends up routing post-write reads to the primary, or
waiting for the replica to catch up, to preserve **read-your-writes** consistency.

**The lesson → why this stage exists.** Async replication buys durability but not *freshness*. If a
write returns before the replicas have it, a fast follow-up read can serve the old value. Stage 06
takes the strong-but-blunt fix: make **every** follower synchronous — raise `W` to `N` so a write
only returns once *all* followers have it. *"Write to everyone ⇒ read from anyone."* Stale reads
disappear.

**Caveat.** Our staleness is engineered to be *reproducible* (the read tier is chosen by port, not by
"fastest replica") so the demo shows it every single run — a teaching device, not how Dynamo picks
replicas. Real systems see the same stale-read class non-deterministically.

**The arc (→ 07).** "Write to everyone" feels like the safe choice. Watch it become the dangerous one
the instant a single follower hiccups.

---

## Stage 07 — Quorum & Fault Tolerance · *The safety setting that stops all writes*

**The hook (say this):** *"The setting that guarantees no stale read also guarantees that the moment
one replica goes down, nobody can write anything. 'Wait for everyone' means 'wait for your weakest
link, forever.'"*

**What really happened.** Ask any team running Kafka with `acks=all` and
`min.insync.replicas` set equal to the replica count. It's the most consistent setting there is — and
it has a **zero-failure budget.** The instant one replica falls out of the in-sync set, the in-sync
count drops below the minimum, producers get `NotEnoughReplicas`, and **writes stall outright**. The
same trap lives in Postgres `synchronous_commit` with a single mandatory standby, and in any
`w: all` write concern. Teams escape it by requiring a **majority**, not everyone. This is the
**CAP** trade-off (Brewer) made operational: with `W = N` you've chosen consistency so hard that a
single partition or crash costs you availability.

**The lesson → why this stage exists.** Stage 06's all-sync is the "too hot" porridge. Stage 07 finds
"just right": a **majority quorum**, `W = 2, R = 2` over `N = 3`. The rule that makes it safe is the
spine of the whole workshop — **W + R > N** forces the read set and write set to overlap, so reads
stay fresh *and* the system now tolerates `floor(N/2)` failures. Kill one follower and watch the
**CAP moment** live: writes may be refused (503) to preserve consistency while reads still succeed —
the CP corner, chosen on purpose.

**Caveat.** We implement a `W+R>N` (Dynamo/leaderless) *rule* on top of a *single-leader* system, with
overlap engineered by port ordering. Pedagogically clean; not a faithful copy of how Cassandra or
DynamoDB coordinate. Say so.

**The arc (→ 08).** Quorum survives a dead follower — *but only if the system knows it's dead.* So
far, "dead" means a human noticed. How does the cluster find out on its own?

---

## Stage 08 — Service Discovery · *When the nervous system goes dark for 73 hours*

**The hook (say this):** *"In 2021, Roblox went down for seventy-three hours. The thing that broke
wasn't a game server or a database. It was the system whose only job is to tell every other system
who's alive."*

**What really happened.** **Roblox's October 2021 outage lasted 73 hours** and affected ~50 million
users. Root cause: a newly enabled **Consul** streaming feature under unusual load triggered a
pathological performance bug deep in **BoltDB**'s freelist, and the Consul cluster — the backbone of
**service discovery** for Roblox's entire fleet — seized up. It cascaded brutally for two reasons we
should call out: **one Consul cluster served many workloads** (so its failure was total), and the
**monitoring needed to diagnose it depended on Consul too** (so the team was flying blind). When
discovery dies, nothing can find anything.

**The lesson → why this stage exists.** Quorum (07) needs to know which nodes are alive. So far that
knowledge has been static. Stage 08 (fourth code stage) implements `heartbeat_loop`: every node POSTs
"I'm alive" to a central **registry** on an interval, and the registry marks a node dead when the
heartbeats stop. This is the nervous system — etcd, Consul, ZooKeeper, Eureka, Redis Cluster gossip
all do a version of it. Roblox is the cautionary tale for *how much rides on it.*

**The arc (→ 09).** Now the cluster *detects* death. But detection alone just means it knows it's
running wounded. Who heals it — and at what hour of the night?

---

## Stage 09 — Auto-Recovery · *The 3 a.m. page you design away*

**The hook (say this):** *"At Netflix's scale, machines don't occasionally fail — they fail
constantly, by the thousand. So Netflix wrote a program whose entire job is to kill their own servers
in production, on purpose, during business hours."*

**What really happened.** Netflix's **Chaos Monkey** (2011) deliberately terminates production
instances at random. The point is brutal and clarifying: if a single machine dying can hurt you, it
*will* hurt you at scale — so make recovery **automatic** and prove it works while engineers are awake
to watch, instead of discovering it doesn't at 3 a.m. Their Auto Scaling Groups replace a killed
instance with a fresh one with no human in the loop. Recovery that requires a human is, at planet
scale, the same as no recovery.

**The lesson → why this stage exists.** Detecting a dead follower (08) and then leaving it dead just
means the cluster runs degraded until someone wakes up. Stage 09 closes the loop: enable
`--auto-spawn`, and the dead follower is respawned and **caught up from the leader's snapshot** —
self-healing, no human. This is the emotional high note of the workshop: the cluster you built fixes
itself.

**Caveat (be precise here).** Stage 09 recovers **followers**, not the leader. Promoting a follower
when the *leader* dies is **leader election** (Sentinel, Raft/etcd, ZAB/ZooKeeper) and is explicitly
**out of scope.** Also worth a sentence: naïve catchup has its own failure mode — many replicas
resyncing from one leader at once (a "full-resync storm") can knock the leader over, which is why real
systems do partial/throttled resync. Don't oversell "automatic failover."

**The arc (→ 10).** Every layer now exists and each defends against a real outage. The last move is to
stand back and see them work *together.*

---

## Stage 10 — Full System · *Now you can read any postmortem*

**The hook (say this):** *"Pull up the postmortem for almost any outage of the last decade. You can
now name the layer that failed — because you built every one of them."*

**There is no incident for Stage 10 — that's the payoff.** Instead, trace one request end to end
through the stack you assembled, and notice that every layer is a fix for a story you just told:

| Layer (Stage 10) | The scar it came from |
|---|---|
| **Gateway + rate limiter** at the edge (429s under flood) | GitHub's 1.35 Tbps DDoS · DynamoDB's retry storm (04) |
| **Coordinator** routing by quorum | the slow-node tax of *The Tail at Scale* (03) |
| **Leader + followers**, replicated | GitLab's 300 GB and 6 hours lost (05) |
| **Quorum** `W+R>N`, survives a failure | Kafka's `acks=all` zero-fault stall (06→07) |
| **Registry + heartbeats** | Roblox's 73-hour discovery blackout (08) |
| **Auto-respawn + catchup** | Netflix killing its own servers to force self-healing (09) |

Run it live (`make lab STAGE=10`): write and read through the gateway, flood the edge to watch it shed
load with 429s, then `kvkill 1` and watch the cluster detect, respawn, catch up, and keep serving
fresh reads — **a request surviving, in two minutes, the same five failure classes that took down
GitHub, GitLab, AWS, Roblox, and Twitter.**

**Close the talk with this:** *"You started with a dict behind HTTP. You finished with a rate-limited,
load-balanced, replicated, quorum-consistent, self-healing distributed key-value store. The
difference between what you built and what runs at Netflix isn't the architecture — it's the years of
operational scars. And now you know where every scar came from."*

---

## Summary Table — the arc at a glance

| Stage | The real scar | What it proves you need | Hands the next stage a problem |
|---|---|---|---|
| 01 Single node | Redis was born as a dict behind a socket (antirez, 2009) | Prove the data model on one box first | One box gets busy |
| 02 Vertical scaling | Cloudflare regex pegs all CPUs (Jul 2 2019) — the ceiling is real; **Stack Overflow** scaled *up* and never had to shard | Use every core first (more workers) — scaling up is often enough | A bigger box is still one box |
| 03 Horizontal scaling + load balancing | Twitter's "Fail Whale" (single primary, ~2008–10) + **Figma** outgrows AWS's largest Postgres (2020→); "The Tail at Scale" (Dean & Barroso, 2013) | A node is a capacity wall *and* a SPOF → run several, then route to capacity (your slowest node sets p99) | Healthy nodes, but too much traffic |
| 04 Rate limiting | GitHub 1.35 Tbps DDoS (2018) · DynamoDB retry storm (2015) | Floods (external *and* self-inflicted) need an intake valve | Data still lives on one node |
| 05 Replication | GitLab deletes the primary, loses 6h (Jan 31 2017) | The leader's only copy is one command from gone | Async followers lag |
| 06 Sync replication | Replica-lag stale reads (Facebook memcache, NSDI 2013) | Async = durable but stale → wait for everyone | "Wait for everyone" is fragile |
| 07 Quorum / CAP | Kafka `acks=all` stalls on one lost ISR | `W+R>N` majority: fresh *and* fault-tolerant (CP choice) | Quorum needs to know who's alive |
| 08 Service discovery | Roblox 73-hour Consul/BoltDB outage (Oct 2021) | Heartbeats detect death; discovery is the nervous system | Detection without healing = degraded |
| 09 Auto-recovery | Netflix Chaos Monkey (2011) | Recovery must be automatic — machines fail constantly | (closes the loop) |
| 10 Full system | *no incident — the synthesis* | Every layer is a fix for a real outage | You can now read any postmortem |

---

## Sources (for the speaker — read more / cite on a slide)

- **Redis origin** — antirez, "A few things about Redis security" / Redis history; LLOOGG background:
  <http://oldblog.antirez.com/post/redis-manifesto.html> and Redis project history.
- **Cloudflare regex outage (Jul 2 2019)** — "Details of the Cloudflare outage on July 2, 2019":
  <https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019/>
- **Stack Overflow — vertical scaling as an end state (Stage 02)** — Nick Craver, "Stack Overflow: The
  Hardware — 2016 Edition" <https://nickcraver.com/blog/2016/03/29/stack-overflow-the-hardware-2016-edition/>
  and "The Architecture — 2016 Edition" <https://nickcraver.com/blog/2016/02/17/stack-overflow-the-architecture-2016-edition/>.
  (Redis "more cores don't help" — Redis benchmark docs:
  <https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/benchmarks/>.)
- **Twitter "Fail Whale" / scaling** — widely documented; see Twitter Engineering's "The Infrastructure
  Behind Twitter" series and contemporaneous coverage of the Rails→services re-architecture.
- **Figma — when vertical scaling runs out (Stage 03)** — Sammy Steele, "How Figma's Databases Team
  Lived to Tell the Scale" (Apr 2024): <https://www.figma.com/blog/how-figmas-databases-team-lived-to-tell-the-scale/>
- **Notion — sharding Postgres (Stage 03 corroboration)** — "Herding elephants: lessons learned from
  sharding Postgres at Notion" (Oct 2021): <https://www.notion.com/blog/sharding-postgres-at-notion>
- **The Tail at Scale** — Dean & Barroso, *Communications of the ACM*, Feb 2013:
  <https://research.google/pubs/the-tail-at-scale/>
- **GitHub 1.35 Tbps DDoS (Feb 28 2018)** — "GitHub survived the biggest DDoS attack ever recorded":
  GitHub Engineering / Wired coverage; <https://github.blog/2018-03-01-ddos-incident-report/>
- **AWS DynamoDB disruption (Sep 20 2015)** — "Summary of the Amazon DynamoDB Service Disruption in
  the US-East Region": <https://aws.amazon.com/message/5467D2/>
- **GitLab database incident (Jan 31 2017)** — "Postmortem of database outage of January 31":
  <https://about.gitlab.com/blog/postmortem-of-database-outage-of-january-31/>
- **Scaling Memcache at Facebook** — Nishtala et al., NSDI 2013 (leases, remote markers, read-after-
  write): <https://www.usenix.org/system/files/conference/nsdi13/nsdi13-final170_update.pdf>
- **CAP theorem** — Brewer (2000); Gilbert & Lynch proof (2002). Kafka durability/`acks`/`min.insync.replicas`
  documented in the Apache Kafka docs.
- **Roblox 73-hour outage (Oct 28–31 2021)** — "Roblox Return to Service 10/28–10/31 2021":
  <https://blog.roblox.com/2022/01/roblox-return-to-service-10-28-10-31-2021/>
- **Netflix Chaos Monkey / Simian Army (2011)** — "The Netflix Simian Army":
  <https://netflixtechblog.com/the-netflix-simian-army-16e57fbab116>

> **Companion doc:** [`real-world-systems.md`](real-world-systems.md) maps each stage to the
> production systems that embody its *pattern* (the "what"). This file is the "why" — pair them: open
> a stage with the incident here, then point to the systems there.
