# Slide Deck — *Deconstructing the Tenets of Planet-Scale Systems with Python*

**What this is.** A slide-by-slide blueprint for the full ~175-minute EuroPython tutorial. It tells
you *what goes on every slide* so you can build an image-heavy deck and drive the live labs from it.
This is the visual spine; the two source docs feed it:

- [`motivating-incidents.md`](motivating-incidents.md) — the **"why"** (the real outage that opens each stage). Hooks are pre-written to say out loud.
- [`real-world-systems.md`](real-world-systems.md) — the **"what"** (the production system each stage embodies; tables to put on slides).

Pair them with [`INSTRUCTOR-GUIDE.md`](INSTRUCTOR-GUIDE.md) (pacing, caveats, exercise answers) and the attendee [`../LAB-MANUAL.md`](../LAB-MANUAL.md) (the exact commands).

---

## Design rules for the deck (read once, apply to every slide)

1. **The slide is a backdrop, not a teleprompter.** Almost no prose. A headline of ≤6 words, one
   image, maybe one formula. The *talking* lives in your mouth and in the **Say** notes below — not on
   the wall.
2. **One idea per slide.** If a slide needs two thoughts, it's two slides (use builds/animations).
3. **Lead with the scar, not the concept.** Every stage opens on a *failure* — a real company, a real
   date, a real postmortem. The room feels the pain; *then* the fix lands as inevitable. Never open a
   stage by naming its concept.
4. **Show the system, not bullet points.** Prefer a diagram of boxes-and-arrows that *grows by one box
   per stage* over text. The audience should watch the architecture accrete.
5. **The terminal is a slide too.** On `[LIVE]` slides you switch to the tmux dashboard and *run the
   thing*. The slide just holds the question ("will the write survive?") while the terminal answers it.
6. **Honesty is part of the pitch.** Where the model simplifies, there's a **Caveat** slide. Say it
   out loud — it builds trust and it's where the real learning is.

**Per-slide legend used below:**
`Show` = the visual · `Text` = the literal words on the slide (keep tiny) · `Say` = your narration ·
`Do [LIVE]` = switch to the terminal and run this · `Caveat` = the honest footnote.

---

## Timing budget (~175 min, one break)

| Part | Slides | Time | Notes |
|---|---|---|---|
| **A. Open** | 1–6 | ~10 min | promise, framing, setup gate |
| **B. The Tenets (theory)** | 7–20 | ~40 min | the 40%-theory foundation |
| **C. The Ladder, part 1** | 21–43 | ~45 min | stages 00–04 (incl. 2 code stages) |
| **— BREAK —** | — | ~10 min | coffee; leave the setup-check slide up |
| **C. The Ladder, part 2** | 44–67 | ~55 min | stages 05–10 (incl. 2 code stages + climax) |
| **D. Close** | 68–73 | ~10 min | synthesis, scope honesty, resources |
| buffer / Q&A | — | ~15 min | always runs over; protect this |

**Cut list if you're behind** (from [`INSTRUCTOR-GUIDE.md`](INSTRUCTOR-GUIDE.md) §2): make stage **08**
a demo instead of a code stage; compress **00/02** to one slide each; end the *hands-on* on **09** and
keep **10** as a pure speaker demo. Never cut the scar slides — they're the talk.

---

# PART A — OPEN  ·  slides 1–6  ·  ~10 min

### Slide 1 — Title  ⏱ ~1m
- **Show:** Full-bleed. A faint world map criss-crossed with datacenter links, or a montage of the
  five logos you'll invoke (Cloudflare, Twitter, GitLab, Roblox, Netflix) greyed in the background.
- **Text:** *Deconstructing the Tenets of Planet-Scale Systems* — *with Python* · your name / handle ·
  EuroPython 2026.
- **Say:** "In the next three hours we're going to take the ideas that hold up Netflix, Cassandra,
  Kubernetes — and *build them*, in Python, on your laptop, one at a time."

### Slide 2 — The promise  ⏱ ~2m
- **Show:** Left: a one-line Python `dict` (`db = {}`). Right (greyed, "by 11:00"): the full end-state
  architecture. An arrow between them.
- **Text:** "From a `dict` behind HTTP → a self-healing distributed KV store."
- **Say:** "You'll start with a dictionary behind a socket — which, by the way, is *literally* how
  Redis was born. You'll finish with a rate-limited, replicated, quorum-consistent, self-healing
  cluster. Same bones as the real thing."

### Slide 3 — The end state (the payoff teaser)  ⏱ ~2m
- **Show:** The full topology diagram, *complete*, so they see where they're going:
  `Client → Gateway (:8000) → Coordinator (:7000) → Leader (:7001) + Followers (:7002–7004)` with
  `Registry (:9000)` to the side feeding heartbeats. Label nothing yet — just let it look intimidating.
- **Text:** none (full diagram).
- **Say:** "Don't worry about the boxes yet. By the end, you'll have *built every one* — and more
  importantly, you'll know which real outage each one exists to prevent."

### Slide 4 — One honest framing (say it once, early)  ⏱ ~1.5m
- **Show:** A "teaching model" stamp over a blueprint, not a photo of a real datacenter.
- **Text:** "A teaching model — not a clone of any one system."
- **Say:** Verbatim from [`motivating-incidents.md`](motivating-incidents.md) intro — "The KV store
  you build is a teaching model. The incidents are the real motivation for each *concept* — not a claim
  that our code reproduces those systems line for line. Where we simplify, I'll say so. Honesty is part
  of the pitch."

### Slide 5 — How a stage works (the loop)  ⏱ ~2m
- **Show:** A 3-beat cycle as a loop graphic: **① run the incident (it goes ❌)** → **② change one
  thing** → **③ run it again (it goes ✅)**. Inset: a screenshot of the tmux dashboard with its panes
  labelled (service panes · control pane · incident pane · scratch).
- **Text:** "incident ❌ → one change → incident ✅"
- **Say:** "Every stage is the same rhythm. A script breaks the system you have. You add one feature.
  The script passes. Four of the eleven stages you write code — *one line* each. The rest you run and
  watch."

### Slide 6 — Setup gate (leave this up during arrivals / the break)  ⏱ ~1.5m
- **Show:** Three big copy-paste commands, monospace, huge. A "🟢 are you green?" checkmark.
- **Text:**
  ```
  docker compose up -d
  docker compose exec workshop bash
  make start
  ```
- **Say:** "Everything runs inside one container — no ports touch your laptop, no dependency hell. Get
  to a shell and run `make start`. Thumbs up when you see the seed message." (Wait for the room.)

---

# PART B — THE TENETS (theory foundation)  ·  slides 7–20  ·  ~40 min

> This is the "40% theory." Keep it *visual and fast* — these are the load-bearing ideas the ladder
> will then make you *feel*. If you already have the Google Slides theory deck, this section is the
> spine to map onto it. Each slide plants a concept you'll cash in at a specific stage (noted as → SNN).

### Slide 7 — What does "planet-scale" even mean?  ⏱ ~2m
- **Show:** Orders-of-magnitude ladder: 1 user → 1K → 1M → 1B. Aligned beside it: 1 box → many boxes →
  many datacenters → many continents.
- **Text:** "Scale isn't a bigger box. It's a *different* problem."
- **Say:** "Every order of magnitude breaks an assumption that was fine at the last one. Today we walk
  up that ladder and watch each assumption snap."

### Slide 8 — The 8 Fallacies of Distributed Computing  ⏱ ~3m
- **Show:** All 8 as struck-through myths (Deutsch/Sun). Reliable network · zero latency · infinite
  bandwidth · secure network · fixed topology · one admin · zero transport cost · homogeneous network.
- **Text:** "Everything you assume about the network is false."
- **Say:** "These are from the '90s and they have aged perfectly. Every distributed bug is one of these
  fallacies coming to collect. Hold onto #1 — *the network is reliable* — we'll watch it fail at S05."

### Slide 9 — Latency numbers every programmer should know  ⏱ ~3m
- **Show:** Jeff Dean's latency table as a *log-scale bar chart* (L1 cache → main memory → SSD →
  same-DC round trip → cross-continent packet). Credit Jeff Dean.
- **Text:** "L1: 0.5 ns … CA→Europe→CA: ~150 ms."
- **Say:** "A network round trip is ~hundreds of thousands of times slower than a memory read. Once
  your data lives on *another machine*, every access pays this tax. That tax is why the rest of this
  talk exists." (→ S03 tail latency, → S05 replication.)

### Slide 10 — Two ways to scale  ⏱ ~2.5m
- **Show:** Left: one box growing taller (more CPU/RAM) = **vertical**. Right: many identical boxes =
  **horizontal**. A ceiling line over the tall box.
- **Text:** "Bigger box (vertical) vs. more boxes (horizontal)."
- **Say:** "Vertical is easy and has a hard ceiling — you run out of box. Horizontal is unlimited and
  hands you a *new* problem: coordination. We'll do both — S01 vertical, S02 horizontal — and feel the
  exact moment vertical stops working." (→ S01, → S02.)

### Slide 11 — The real enemy is *state*  ⏱ ~2.5m
- **Show:** Two columns. **Stateless** (web servers) — clone freely, a green "just add boxes." **Stateful**
  (databases) — a red "now what?" with copies that can disagree.
- **Text:** "Stateless scales by copy-paste. State is the hard part."
- **Say:** "If your service holds no data, scaling is trivial: stamp out more copies. The entire
  difficulty of distributed systems is what happens to *data* when there's more than one copy. That's
  what we spend the back half of today on."

### Slide 12 — The two things you do to data  ⏱ ~3m
- **Show:** Two diagrams side by side. **Replication** = same data on N nodes (copies). **Partitioning
  /sharding** = different data on different nodes (slices). A note: "today we do replication."
- **Text:** "Replicate (copies) · Partition (slices)."
- **Say:** "Two levers. *Replicate* for durability and read scale — keep copies. *Partition* to hold
  more than one box can — split the keyspace. We build replication end-to-end today; sharding I'll name
  but leave out of scope, and I'll be honest about that at the end." (→ S05–S09; scope note → close.)

### Slide 13 — Replication has three shapes  ⏱ ~2.5m
- **Show:** Single-leader (one writer, many read replicas) · multi-leader · leaderless (Dynamo-style
  quorum). Highlight **single-leader** + a dotted box around **leaderless quorum**.
- **Text:** "Single-leader · Multi-leader · Leaderless."
- **Say:** "We build *single-leader* — one node takes writes, others serve reads, like Redis or
  Postgres. But we'll borrow one idea from the *leaderless* world — the quorum rule — because it's the
  cleanest way to *see* consistency. That's a deliberate hybrid; flag for later." (→ S07 caveat.)

### Slide 14 — Consistency is a spectrum, not a switch  ⏱ ~3m
- **Show:** A slider from **Strong/Linearizable** (always fresh, expensive) → causal → **read-your-
  writes** → **Eventual** (cheap, can be stale). Mark the everyday one: *read-your-writes*.
- **Text:** "Strong ⟷ Eventual. Freshness costs."
- **Say:** "Consistency isn't on/off — it's a dial, and every notch costs latency or availability.
  The one users *notice* is read-your-writes: you hit save and the page shows the old value. We'll
  reproduce that exact bug live at S06."  (→ S06.)

### Slide 15 — CAP (and the part everyone forgets, PACELC)  ⏱ ~3m
- **Show:** The CAP triangle (C, A, P). Overlaid: "P is not optional." Then PACELC: *if Partition →
  choose C or A; **Else** → choose Latency or Consistency.*
- **Text:** "When the network splits: keep Consistency *or* Availability."
- **Say:** "Partitions *will* happen — fallacy #1. So CAP is really a single forced choice: when a
  partition hits, do you refuse writes (stay consistent, the **CP** corner) or accept them (stay
  available, **AP**)? At S07 we make that choice *live* — kill a node and watch writes get refused on
  purpose." (→ S07.)

### Slide 16 — The spine of the whole talk: **W + R > N**  ⏱ ~4m
- **Show:** Two overlapping sets. Write set (W nodes) on the left, read set (R nodes) on the right.
  Their **overlap** highlighted: "the freshest write is always in the read set." A big formula:
  **W + R > N**.
- **Text:** "W + R > N  ⇒  no stale reads."
- **Say:** "Remember this one rule and you've understood the back half of the talk. N copies. A write
  must land on W of them; a read must ask R of them. If W + R > N, the two sets are *forced* to overlap
  — so any read sees the latest write. This single inequality is the dial behind freshness *and* fault
  tolerance, and we tune it live three times." (→ S06 W=N, → S07 majority.)

### Slide 17 — Tail latency: your worst node sets your p99  ⏱ ~3m
- **Show:** A request fanning out to many nodes; one is slow; the *whole* response waits. Beside it: a
  latency histogram with a fat tail; mark p50 vs p99. Credit Dean & Barroso, "The Tail at Scale."
- **Text:** "Users feel your *slowest* server, not your average one."
- **Say:** "Average latency is a comforting lie. When a request touches many machines, the slow tail of
  *any one* of them dominates what the user sees. A blind router keeps feeding the weak node. We watch
  that tax appear — and then vanish — at S03." (→ S03.)

### Slide 18 — At scale, failure is the *normal* case  ⏱ ~3m
- **Show:** A wall of 10,000 server icons; a handful always red. Werner Vogels quote: "Everything
  fails, all the time."
- **Text:** "1 box: failure is an event. 10,000 boxes: failure is constant."
- **Say:** "If a machine fails once every three years, then across ten thousand machines something is
  failing roughly every few hours. So you can't *prevent* failure — you have to *detect* and *heal* it
  automatically. That's S08 and S09." (→ S08, → S09.)

### Slide 19 — Idempotency, retries & the self-inflicted flood  ⏱ ~2.5m
- **Show:** A client retrying a timed-out request; the server actually succeeded; now a retry storm
  spiral feeding itself.
- **Text:** "The scariest DDoS is your own clients retrying."
- **Say:** "Retries are necessary and dangerous. When everyone retries at once, your own fleet becomes
  the attacker. The valve for that is rate limiting — and the real example, AWS DynamoDB's 2015 retry
  storm, opens S04." (→ S04.)

### Slide 20 — The map: 11 rungs, 11 scars  ⏱ ~2.5m
- **Show:** The ladder 00→10 as rungs climbing up to the end-state diagram from slide 3. Each rung
  tagged with its company scar (Redis · Cloudflare · Twitter · Google · GitHub/AWS · GitLab · Facebook
  · Kafka · Roblox · Netflix · ✦). Mark the 4 ✏️ code rungs (03/04/05/08).
- **Text:** "Every rung is a fix for a real outage."
- **Say:** "Here's the whole climb. Each rung was added by some real company *after* it cost them an
  outage. We'll tell the failure first, then build the fix. Let's start at the bottom." → transition to
  the terminal.

---

# PART C — THE LADDER  ·  slides 21–67

> Pattern per stage: **scar slide** (the outage) → **concept slide** (the fix, as a diagram) →
> for ✏️ stages a **your-turn slide** (the one line to write) → **`[LIVE]` slide** (run it in the
> dashboard) → optional **caveat** → **arc slide** (hand the next stage its problem). The deck frames;
> the terminal proves. Drive the live parts from [`../LAB-MANUAL.md`](../LAB-MANUAL.md).

## Stage 00 — Single node · *the origin story*  ·  slides 21–23  ·  ~3m

### Slide 21 — Scar: Redis was born as a dict behind a socket  ⏱ ~1.5m
- **Show:** antirez / early Redis; "LLOOGG, 2009." A doodle: `{ }` behind a TCP plug.
- **Text:** "Every database you trust started as a dictionary."
- **Say:** Hook (verbatim): "Every database you've ever depended on started as a dictionary behind a
  socket — including the one most of this room has run in production." Tell the LLOOGG → Redis origin.

### Slide 22 — Concept: a KV store is two routes over a dict  ⏱ ~1m
- **Show:** `POST /data` and `GET /data/{key}` arrows into a Python `dict`. The *first box* of the
  architecture diagram appears.
- **Text:** "`POST /data` · `GET /data/{key}`"
- **Say:** "That's the whole data model. We keep it boring on purpose — it's the control variable for
  everything we add. You earn distribution by first proving the model on one box."

### Slide 23 — [LIVE] Stage 00 round-trip  ⏱ ~0.5m
- **Do [LIVE]:** `make lab STAGE=00` → in the control pane: `nwrite cart shoes` then `nread cart` →
  press **Enter** in the incident pane (✅).
- **Text (held):** "One box. It works. Now let's make it busy."
- **Arc:** "One box is wonderful right up until it's busy. Let's make it busy."

## Stage 01 — Vertical scaling · *the regex that froze the planet*  ·  slides 24–27  ·  ~6m

### Slide 24 — Scar: Cloudflare, July 2 2019  ⏱ ~2m
- **Show:** The Cloudflare status page / a CPU-pegged-at-100% graph. "Global 502s · ~30 min · one
  regex."
- **Text:** "One line of CPU-bound code took the web offline."
- **Say:** Hook (verbatim): "On July 2nd 2019, a single regular expression took Cloudflare offline
  worldwide. Not a DDoS, not a bad deploy — one CPU-bound line no other request could get past."

### Slide 25 — Concept: the single-thread ceiling (the GIL is our Redis-thread)  ⏱ ~2m
- **Show:** 10 requests queued behind one CPU-bound task on a single thread. Note: "Python GIL ≈
  Redis's one command thread ≈ a JVM GC pause."
- **Text:** "One CPU-bound op serializes everyone behind it."
- **Say:** "This is the single-thread ceiling. Our `--load-factor` Fibonacci does to a uvicorn worker
  exactly what `KEYS *` does to Redis or a GC pause does to a JVM node. The first lever is *vertical*:
  more workers so one slow request can't hold the door shut."

### Slide 26 — [LIVE] 4 workers vs. 1 worker  ⏱ ~1.5m
- **Do [LIVE]:** `make lab STAGE=01` → Enter in incident pane, note p95 (✅). Then `make lab-down` →
  `WORKERS=1 make lab STAGE=01` → Enter again → latency spikes. *Feel* the ceiling.
- **Text (held):** "Same code. 4 workers vs 1. Watch p95."

### Slide 27 — Caveat + arc  ⏱ ~0.5m
- **Caveat (say it):** "Cloudflare's meltdown was CPU exhaustion across *many* cores; ours is 1 vs 4.
  The shared structure — a CPU-bound task starving concurrent work — is the transferable idea, not the
  core count."
- **Arc:** "A bigger box has a bigger ceiling — but it's still a ceiling, and still *one box*. What
  happens when that box just dies?"

## Stage 02 — Horizontal scaling · *the Fail Whale*  ·  slides 28–30  ·  ~4m

### Slide 28 — Scar: Twitter's single primary  ⏱ ~1.5m
- **Show:** The actual Fail Whale image. "One Rails app, one MySQL primary, ~2008–10."
- **Text:** "The most famous image in tech was a capacity wall."
- **Say:** Hook (verbatim): "For two years the most famous image in tech was a whale lifted by birds —
  Twitter's Fail Whale. It showed up every time one overloaded stack couldn't take the spike."

### Slide 29 — Concept: more nodes — but now the bills come due  ⏱ ~1.5m
- **Show:** 3 nodes appear with *3 separate dicts*. Two red flags: "split, not shared" and "round-robin
  is blind to capacity."
- **Text:** "3 nodes · 3 separate dicts · blind round-robin."
- **Say:** "A node is two problems in one coat: a capacity wall *and* a single point of failure. So run
  three. But notice the new pain — three separate dicts means data is *split, not shared*, and blind
  round-robin feeds the weak node anyway. Stage 02 doesn't *solve* anything; it reveals the two bills:
  replication (05) and load balancing (03)."

### Slide 30 — [LIVE] watch the data split  ⏱ ~1m
- **Do [LIVE]:** `make lab STAGE=02` → `nload 40 10` (weak node drags p95); `nwrite a 1`, then
  `nread a` (may miss — data is split). Enter in incident pane (✅).
- **Arc:** "More nodes — but they're not equal, and round-robin doesn't know that."

## Stage 03 — Load balancing ✏️ · *the tail-at-scale tax*  ·  slides 31–35  ·  ~12m

### Slide 31 — Scar: "The Tail at Scale" (Dean & Barroso, 2013)  ⏱ ~2m
- **Show:** The fan-out diagram from the paper; one slow node poisoning the response. p99 histogram.
- **Text:** "Your p99 is decided by your worst node."
- **Say:** Hook (verbatim): "At scale, your user's experience isn't decided by your average server —
  it's decided by your *worst* one, and round-robin keeps feeding it traffic anyway."

### Slide 32 — Concept: spread toward *capacity*, not evenly  ⏱ ~2m
- **Show:** Round-robin (1-2-3-1-2-3, blind) vs adaptive (route to least-loaded). Table from
  [`real-world-systems.md`](real-world-systems.md): round-robin / least-conn / power-of-two / weighted.
- **Text:** "Round-robin is blind. Adapt to live load."
- **Say:** "Production proxies moved *off* plain round-robin — HAProxy `leastconn`, Envoy power-of-two
  — for exactly this reason. Spreading load isn't enough; you spread it *toward capacity*."

### Slide 33 — ✏️ Your turn: `AdaptiveStrategy.get_node`  ⏱ ~5m (incl. their coding)
- **Show:** The one blank function with its docstring; a hint: `min(nodes, key=<load score>)`.
- **Text:** "Return the lowest-load node. One line."
- **Say:** "Open `kvstore/load_balancer.py`. One line: pick the node with the lowest load score. Two
  minutes — go." (Walk the room.)
- **Do:** `make gap STAGE=03` (loads the blank); rescue is `make reset STAGE=03`.

### Slide 34 — [LIVE] the tax appears, then vanishes  ⏱ ~2.5m
- **Do [LIVE]:** `make lab STAGE=03` → `nload round_robin 40 10` vs `nload adaptive 40 10`. The weak
  node's tax shows under round-robin and disappears under adaptive. Enter in incident pane (✅:
  adaptive p95 < round-robin p95).
- **Text (held):** "round_robin vs adaptive — watch p95."

### Slide 35 — Arc  ⏱ ~0.5m
- **Arc:** "Now traffic flows to the healthy nodes. But what if they're *all* healthy and the problem
  is simply too much traffic — some of it abusive?"

## Stage 04 — Rate limiting ✏️ · *when your own clients DDoS you*  ·  slides 36–43  ·  ~12m

### Slide 36 — Scar A: GitHub, 1.35 Tbps (Feb 28 2018)  ⏱ ~1.5m
- **Show:** The GitHub traffic-spike graph; "memcrashed amplification · largest DDoS ever, then."
- **Text:** "1.35 Tbps. Shed it at the edge."
- **Say:** "The outside flood: GitHub absorbed the largest DDoS then recorded by shedding it at the
  *edge* before it reached the app."

### Slide 37 — Scar B: AWS DynamoDB retry storm (Sep 20 2015)  ⏱ ~2m
- **Show:** The self-feeding retry-storm spiral; "took down Netflix et al. · ~5 hours · US-EAST-1."
- **Text:** "The flood was self-inflicted."
- **Say:** Hook (verbatim): "The scariest flood isn't an attacker. It's ten thousand of your *own*
  servers all retrying at once." Tell the metadata-service / GSI-inflated-membership spiral; AWS broke
  it by *pausing requests* — a rate limit.

### Slide 38 — Concept: a fixed-window intake valve → 429  ⏱ ~2m
- **Show:** `INCR` + `EXPIRE` window; counter resets each window; over-limit → **HTTP 429**. The
  boundary-burst weakness drawn (2× at the edge).
- **Text:** "Count per window. Over budget → 429."
- **Say:** "Every store with no intake valve will accept exactly enough load to kill itself. The
  classic fix is a fixed-window counter — Redis `INCR`+`EXPIRE`. Note its known weakness: a burst
  straddling the boundary can sneak ~2× — which is why Cloudflare/Stripe moved to sliding-window."

### Slide 39 — ✏️ Your turn: `FixedWindowStrategy.is_allowed`  ⏱ ~5m
- **Show:** The blank with its three sub-steps as a comment: roll the window over → allow under limit
  (increment) → else reject.
- **Text:** "Reset on rollover · allow under limit · else reject."
- **Say:** "Open `kvstore/rate_limiter.py`. Reset the counter when the window rolls over, allow while
  under the limit, reject once it's hit." `make gap STAGE=04`.

### Slide 40 — [LIVE] watch the 429s appear  ⏱ ~1.5m
- **Do [LIVE]:** `make lab STAGE=04` → flood past the limit in the control pane; before the fix, no
  429s; after, the overflow comes back 429. Enter in incident pane (✅).

### Slide 41 — Arc  ⏱ ~0.5m
- **Arc:** "The store now survives load and abuse. But every byte still lives on *one node*. Survive
  the traffic and you've still not survived the *machine*." → transition to replication.

### Slide 42 — Section recap before the break  ⏱ ~0.5m
- **Show:** The architecture diagram so far: client → (round-robin) → 3 nodes, with a rate-limit valve.
  Greyed: everything from S05 on.
- **Text:** "You've scaled and shielded. Next: you keep the data alive."

### Slide 43 — BREAK  ⏱ ~10m
- **Show:** A 10-min countdown; leave slide 6 (setup commands) accessible. A teaser line.
- **Text:** "Back in 10. Up next: the 300 GB one command erased."

---

## Stage 05 — Replication ✏️ · *the 300 GB GitLab erased*  ·  slides 44–48  ·  ~12m

### Slide 44 — Scar: GitLab, Jan 31 2017  ⏱ ~2.5m
- **Show:** The "`rm -rf`" on the wrong host; the public livestream; "~300 GB gone · ~6 h lost · 5
  backups, all broken."
- **Text:** "He ran the cleanup on the primary. Backups didn't work."
- **Say:** Hook (verbatim): "On January 31st 2017, a GitLab engineer ran a cleanup command on what they
  thought was the replica. It was the primary. 300 GB gone in seconds — and the backups didn't work."

### Slide 45 — Concept: the leader's only copy *is the bug*  ⏱ ~2m
- **Show:** Leader → POST each write to followers; **reads served by followers**. The cluster topology
  (coordinator + leader + 3 followers) appears.
- **Text:** "Reads come from followers. A non-replicated write is invisible."
- **Say:** "Replication turns 'one fragile copy' into 'the write survives the machine.' Crucially in
  our design, *reads are served by followers* — so a write that fails to replicate is *invisible*. That
  stranded data is the GitLab lesson in miniature."

### Slide 46 — ✏️ Your turn: `replicate_to_follower`  ⏱ ~5m
- **Show:** The blank: POST `{key, value, version}` to the follower's `/replicate`; success on `200`.
- **Text:** "POST the write to the follower. Return on 200."
- **Say:** "Open `kvstore/node.py`. The leader POSTs each write to the follower's `/replicate` route."
  `make gap STAGE=05`.

### Slide 47 — [LIVE] the stranded write  ⏱ ~2m
- **Do [LIVE]:** `make lab STAGE=05` → `kvwrite order paid`, `kvstatus` (leader + 3 followers),
  `kvread order` *misses* before the fix (stranded on the leader); after the fix, it replicates and the
  read hits. Enter in incident pane (✅). Optional: contrast `localhost:7001/data/order` (leader has it)
  vs `localhost:7000/read/order` (follower tier didn't).
- **Text (held):** "Did the write reach the replicas?"

### Slide 48 — Arc  ⏱ ~0.5m
- **Arc:** "Now the write reaches the followers — but ours replicate *asynchronously*, with deliberate
  visible lag. What does a user see if they read inside that lag window?"

## Stage 06 — Synchronous replication · *the update that "didn't save" — but did*  ·  slides 49–52  ·  ~6m

### Slide 49 — Scar: replica-lag stale reads (Facebook memcache, NSDI 2013)  ⏱ ~2m
- **Show:** A UI: toggle a privacy setting → "Saved" → page reloads → *old value*. "read-your-writes."
- **Text:** "You hit save. It reloads. The old value."
- **Say:** Hook (verbatim): "You change a setting, hit save, the page reloads… and shows the *old*
  setting. You didn't lose the write — you read a replica that hadn't caught up." Facebook added leases
  and remote markers purely to stop this.

### Slide 50 — Concept: make every follower synchronous → W = N  ⏱ ~1.5m
- **Show:** The W+R>N slide returns; set **W = N** (all followers must ack before the write returns).
  "Write to everyone ⇒ read from anyone."
- **Text:** "W = N: a write waits for *every* follower."
- **Say:** "Async buys durability, not freshness. The strong, blunt fix: make every follower
  synchronous — raise W to N. Stale reads disappear."

### Slide 51 — [LIVE] no more stale reads  ⏱ ~2m
- **Do [LIVE]:** `make lab STAGE=06` (all-sync W=3,R=1) → `kvwrite order paid`, `kvread order` always
  fresh. Enter in incident pane (✅).
- **Caveat (say it):** "Our staleness is *engineered to be reproducible* — the read tier is chosen by
  port, not by 'fastest replica' — so the demo shows it every run. A teaching device; real systems hit
  the same class non-deterministically."

### Slide 52 — Arc  ⏱ ~0.5m
- **Arc:** "'Write to everyone' feels like the safe choice. Watch it become the dangerous one the
  instant a single follower hiccups."

## Stage 07 — Quorum & CAP · *the safety setting that stops all writes*  ·  slides 53–57  ·  ~8m

### Slide 53 — Scar: Kafka `acks=all` zero-fault budget  ⏱ ~2m
- **Show:** A producer getting `NotEnoughReplicas`; one ISR drops and writes stall. "min.insync.replicas
  = replica count."
- **Text:** "'Wait for everyone' = wait for your weakest link, forever."
- **Say:** Hook (verbatim): "The setting that guarantees no stale read also guarantees that the moment
  one replica goes down, *nobody can write*. The same trap lives in Postgres `synchronous_commit` and
  any `w: all`."

### Slide 54 — Concept: majority quorum — Goldilocks  ⏱ ~2m
- **Show:** Three porridge bowls: too cold (W=1, stale), too hot (W=N, stalls), just right (**W=2, R=2,
  N=3**). The overlap diagram with W+R=4 > N=3.
- **Text:** "W=2, R=2, N=3 · fresh *and* survives one failure."
- **Say:** "Majority quorum: W+R>N keeps reads fresh *and* now tolerates ⌊N/2⌋ failures. This is the
  conceptual peak of the talk."

### Slide 55 — [LIVE] the CAP moment  ⏱ ~2.5m
- **Do [LIVE]:** `make lab STAGE=07` → `kvwrite order paid`, `kvkill 1`, `kvstatus` (one dead, quorum
  holds), `kvwrite order shipped` still works, `kvread order` fresh. (Optionally show that with W=N this
  would 503.) Enter in incident pane (✅).
- **Text (held):** "Kill one. Do writes survive?"
- **Say:** "Watch the CAP choice live: with the quorum lost a system *refuses writes* (503) to preserve
  consistency — the CP corner, chosen on purpose, while reads still succeed."

### Slide 56 — Caveat: the honest hybrid  ⏱ ~1m
- **Show:** "W+R>N (Dynamo/leaderless rule) **on** a single-leader system; overlap engineered by port
  ordering."
- **Text:** "A leaderless *rule* on a single-leader *system*. On purpose."
- **Say (verbatim caveat):** "We implement a Dynamo-style quorum *rule* on top of a *single-leader*
  system, with overlap engineered by port ordering. Pedagogically clean; not a faithful copy of how
  Cassandra or DynamoDB coordinate. Saying so is the point."

### Slide 57 — Arc  ⏱ ~0.5m
- **Arc:** "Quorum survives a dead follower — but only if the system *knows* it's dead. So far 'dead'
  means a human noticed. How does the cluster find out on its own?"

## Stage 08 — Service discovery ✏️ · *73 hours in the dark*  ·  slides 58–62  ·  ~12m

### Slide 58 — Scar: Roblox, 73 hours (Oct 2021)  ⏱ ~2m
- **Show:** "73 hours · ~50M users · Consul streaming + a BoltDB freelist bug." The nervous-system
  going dark.
- **Text:** "The thing that broke was the system that says who's alive."
- **Say:** Hook (verbatim): "In 2021 Roblox went down for seventy-three hours. What broke wasn't a game
  server or a database — it was the system whose only job is to tell every other system who's alive."
  Note the two cascade multipliers: one Consul served everything, and *monitoring depended on Consul too*.

### Slide 59 — Concept: heartbeats + a registry  ⏱ ~2m
- **Show:** Each node POSTs "I'm alive" to a central **Registry (:9000)** on an interval; registry
  marks a node dead when beats stop. The registry box appears in the topology.
- **Text:** "Every node says 'I'm alive.' Silence = dead."
- **Say:** "Quorum needs to know who's alive. The nervous system: nodes heartbeat a registry on an
  interval; missed beats = dead. etcd, Consul, ZooKeeper, Eureka all do a version of this."

### Slide 60 — ✏️ Your turn: `heartbeat_loop`  ⏱ ~5m
- **Show:** The blank: each interval, POST `{node_id, port, url, role}` to the registry's `/heartbeat`.
- **Text:** "POST your identity to /heartbeat, every interval."
- **Say:** "Open `kvstore/node.py`. Each node POSTs its identity to the registry every interval."
  `make gap STAGE=08`.

### Slide 61 — [LIVE] death gets detected  ⏱ ~2m
- **Do [LIVE]:** `make lab STAGE=08` → before the fix, `kvkill 1` then `kvstatus` — the registry never
  even learned the node existed. After the fix, the killed follower is marked dead within the timeout.
  Enter in incident pane (✅).

### Slide 62 — Arc  ⏱ ~0.5m
- **Arc:** "Now the cluster *detects* death. But detection alone just means it knows it's running
  wounded. Who heals it — and at what hour of the night?"

## Stage 09 — Auto-recovery · *the 3 a.m. page you design away*  ·  slides 63–65  ·  ~8m

### Slide 63 — Scar: Netflix Chaos Monkey (2011)  ⏱ ~2m
- **Show:** The Chaos Monkey logo. "A program whose job is to kill your own servers in production,
  during business hours."
- **Text:** "Recovery that needs a human is, at scale, no recovery."
- **Say:** Hook (verbatim): "At Netflix's scale machines fail constantly, by the thousand. So Netflix
  wrote a program whose entire job is to kill their own servers in production, on purpose, during
  business hours — to prove recovery is automatic while engineers are awake to watch."

### Slide 64 — [LIVE] the cluster heals itself  ⏱ ~3.5m  ← emotional high note
- **Show (held):** "Kill a follower. Walk away. Watch it come back."
- **Do [LIVE]:** `make lab STAGE=09` (auto-spawn on) → `kvwrite order paid`, `kvkill 1`, `kvstatus`
  (degraded) → wait ~5s; the coordinator pane shows respawn + catch-up → `kvstatus` back to full →
  `kvread order` (the revived node has the data). Enter in incident pane (✅). Let the room *watch the
  coordinator pane*.
- **Say:** "Detecting death and leaving it is just an accurate map of the damage. Enable auto-spawn and
  the dead follower is respawned and caught up from the leader's snapshot — self-healing, no human.
  This is the cluster *you* built fixing itself."

### Slide 65 — Caveat: be precise about 'failover'  ⏱ ~1.5m
- **Show:** A clear line: "We recover **followers**. Promoting a follower when the *leader* dies =
  **leader election** (Raft/Sentinel/ZAB) — *out of scope*." A footnote: "naïve catchup → full-resync
  storms; real systems throttle."
- **Text:** "Follower recovery — *not* leader failover."
- **Say (verbatim caveat):** "Stage 09 recovers *followers*, not the leader. Promoting a follower when
  the leader dies is leader election — Sentinel, Raft, ZAB — and it's explicitly out of scope. Don't
  oversell 'automatic failover.'"
- **Arc:** "Every layer now exists, each defends against a real outage. The last move is to stand back
  and watch them work *together*."

## Stage 10 — Full system · *now you can read any postmortem*  ·  slides 66–67  ·  ~8m

### Slide 66 — [LIVE] the synthesis demo  ⏱ ~6m
- **Show:** The *complete* architecture diagram from slide 3 — now every box is one you built; the
  gateway joins at the edge.
- **Text:** "One request, through everything you built."
- **Do [LIVE]:** `make lab STAGE=10` → in the control pane:
  - `kvwrite cart shoes` / `kvread cart` — trace gateway (:8000) → coordinator (:7000) → leader →
    followers;
  - `kvflood 15` — hammer the edge, watch the rate limiter shed overflow as 429s;
  - `kvwrite order paid`, `kvkill 1` — quorum holds, then auto-respawn + catch-up;
  - `kvread order` — still fresh.
- **Say:** "A request surviving, in two minutes, the same five failure classes that took down GitHub,
  GitLab, AWS, Roblox, and Twitter."
- **Caveat (one line):** "The gateway forwards to a *single* coordinator, so it doesn't load-balance —
  that responsibility moved server-side into the coordinator's quorum routing. In production you'd run
  several coordinators behind the gateway. Stage 10 is the *synthesis*, not new code."

### Slide 67 — The scar → layer table  ⏱ ~2m
- **Show:** The table from [`motivating-incidents.md`](motivating-incidents.md) Stage 10: each layer
  beside the outage it came from (Gateway+limiter → GitHub/DynamoDB · Coordinator routing → Tail at
  Scale · Leader+followers → GitLab · Quorum → Kafka · Registry → Roblox · Auto-respawn → Netflix).
- **Text:** "Every box ↔ a front-page outage."
- **Say:** "Pull up the postmortem for almost any outage of the last decade. You can now *name the
  layer that failed* — because you built every one."

---

# PART D — CLOSE  ·  slides 68–73  ·  ~10 min

### Slide 68 — From a dict to a distributed system  ⏱ ~1.5m
- **Show:** The slide-2 before/after, now both *real* — the `dict` and the full cluster you built.
- **Text:** "You started with `{}`. You finished with a distributed KV store."
- **Say (the close, verbatim):** "You started with a dict behind HTTP. You finished with a
  rate-limited, load-balanced, replicated, quorum-consistent, self-healing distributed key-value store.
  The difference between this and what runs at Netflix isn't the architecture — it's years of
  operational scars. And now you know where every scar came from."

### Slide 69 — The one rule to keep  ⏱ ~1m
- **Show:** **W + R > N** big, with the overlap diagram.
- **Text:** "If you forget everything else: W + R > N."
- **Say:** "One inequality is the dial behind freshness *and* fault tolerance. Internalize it and the
  rest is detail."

### Slide 70 — What we *didn't* build (scope honesty)  ⏱ ~2.5m
- **Show:** Three greyed boxes labelled "out of scope": **leader election** (Raft/Sentinel) · **sharding
  /partitioning** (consistent hashing, hash slots) · **persistence** (we're in-memory only). A fourth:
  "deterministic staleness — a teaching device."
- **Text:** "Honest scope: no leader election · no sharding · no persistence."
- **Say:** "Three honest gaps. We replicate but don't *shard*, so we don't outgrow one box's worth of
  data. We recover followers but don't *elect* a new leader. And we're in-memory — no durability to
  disk. Each of those is a whole next workshop." (This is where the per-stage caveats land as a set.)

### Slide 71 — Where to go next  ⏱ ~1.5m
- **Show:** Book/paper covers: *Designing Data-Intensive Applications* (Kleppmann) · the Dynamo paper ·
  the Raft paper · "The Tail at Scale." QR codes.
- **Text:** "Read these. Re-read your incidents."
- **Say:** "DDIA is the single best next step — it's this talk, but rigorous and complete. The Dynamo
  and Raft papers fill the two gaps we left."

### Slide 72 — Sources / postmortems (cite the scars)  ⏱ ~1.5m
- **Show:** The sources list from [`motivating-incidents.md`](motivating-incidents.md) §Sources, as a
  wall of links/QR codes (Cloudflare, GitHub, AWS, GitLab, Facebook memcache, Roblox, Netflix).
- **Text:** "Every scar in this talk is a real, public postmortem."
- **Say:** "None of these are hypothetical. Go read them — they're the best systems-design literature
  there is, written in blood."

### Slide 73 — Thank you / take the repo home  ⏱ ~1.5m
- **Show:** The repo QR/URL; the session page; your contact. The ladder graphic faded behind.
- **Text:** "The cluster is yours. `make lab STAGE=10`."
- **Say:** "Everything you ran is yours to keep — `make start`, climb the ladder again, break it on
  purpose. Thank you." → Q&A.

---

## Appendix A — Asset checklist (what to source/draw)

> Prefer official postmortem screenshots / company status pages (most are public) or clean redraws.
> Verify licensing before the talk; when in doubt, redraw as a simple diagram. The **`motivating-
> incidents.md` §Sources** list has the primary URL for every incident below.

| Slide | Asset | Source idea |
|---|---|---|
| 1–3 | Title montage · `dict`→cluster before/after · full topology | redraw the topology from this repo (ports in `CLAUDE.md`) |
| 9 | Latency-numbers log-scale chart | "Jeff Dean's numbers every programmer should know" |
| 16, 54, 69 | **W + R > N** overlap diagram (reused) | redraw — two overlapping sets |
| 21 | antirez / early Redis | Redis history / LLOOGG |
| 24 | Cloudflare CPU-pegged graph / status | Cloudflare Jul 2 2019 postmortem |
| 28 | Fail Whale | Twitter — iconic, check usage |
| 31 | Fan-out tail-latency diagram | "The Tail at Scale," Dean & Barroso |
| 36–37 | GitHub 1.35 Tbps graph · DynamoDB retry-storm spiral | GitHub 2018 / AWS Sep 20 2015 postmortems |
| 44 | GitLab livestream / "300 GB" | GitLab Jan 31 2017 postmortem |
| 49 | "save → old value" UI mock | redraw (Facebook memcache NSDI 2013 is the cite) |
| 53 | Kafka `NotEnoughReplicas` | Kafka docs |
| 58 | Roblox 73h outage | Roblox return-to-service writeup |
| 63 | Chaos Monkey logo | Netflix Simian Army |
| 67 | scar→layer table | `motivating-incidents.md` Stage 10 table |

## Appendix B — Speaker cheat-sheet (slide ↔ command)

| Stage | Slides | Load | Live (dashboard) |
|---|---|---|---|
| 00 | 21–23 | (auto) | `make lab STAGE=00` → `nwrite` / `nread` |
| 01 | 24–27 | (auto) | `make lab STAGE=01`; then `WORKERS=1 make lab STAGE=01` |
| 02 | 28–30 | (auto) | `make lab STAGE=02` → `nload 40 10` |
| 03 ✏️ | 31–35 | `make gap STAGE=03` | `make lab STAGE=03` → `nload round_robin/adaptive 40 10` |
| 04 ✏️ | 36–43 | `make gap STAGE=04` | `make lab STAGE=04` → flood |
| 05 ✏️ | 44–48 | `make gap STAGE=05` | `make lab STAGE=05` → `kvwrite/kvstatus/kvread` |
| 06 | 49–52 | (auto) | `make lab STAGE=06` → `kvwrite/kvread` |
| 07 | 53–57 | (auto) | `make lab STAGE=07` → `kvkill 1` then write/read |
| 08 ✏️ | 58–62 | `make gap STAGE=08` | `make lab STAGE=08` → `kvkill 1`, `kvstatus` |
| 09 | 63–65 | (auto) | `make lab STAGE=09` → `kvkill 1`, watch respawn |
| 10 | 66–67 | (auto) | `make lab STAGE=10` → `kvwrite/kvread/kvflood/kvkill` |

Rescue any stage with `make reset STAGE=NN`; tear down with `make lab-down`. Full command reference:
[`../LAB-MANUAL.md`](../LAB-MANUAL.md). Pacing & caveats: [`INSTRUCTOR-GUIDE.md`](INSTRUCTOR-GUIDE.md).
