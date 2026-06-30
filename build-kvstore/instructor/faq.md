# Workshop FAQ — anticipated questions (and honest answers)

**What this is.** The questions attendees actually ask — and the answers that keep the talk *honest*
about where the teaching model simplifies. Organized **per stage** so you can find the relevant Q&A
fast during a live session. Pairs with [`motivating-incidents.md`](motivating-incidents.md) (the
"why"), [`real-world-systems.md`](real-world-systems.md) (the "what"), and
[`slide-deck.md`](slide-deck.md) (the narration).

> Add new questions under the stage they belong to. Keep answers honest about the lab's
> simplifications — admitting a gap and explaining how production closes it is usually a *better* answer
> than pretending the model is complete.

---

## Stage 01 — Single node

_No questions logged yet._

---

## Stage 02 — Vertical scaling

_No questions logged yet._

---

## Stage 03 — Horizontal scaling + load balancing

_No questions logged yet._

---

## Stage 04 — Rate limiting

### Q: Is there a more recent example than GitHub's 2018 DDoS?

Yes — the "largest DDoS ever" number from GitHub (1.35 Tbps, 2018) has since been beaten more than
twentyfold. Three modern incidents, each making a different point:

- **HTTP/2 "Rapid Reset" (CVE-2023-44487), Aug–Oct 2023** — the best *teaching* example, because the
  mechanism **is** the lesson. Attackers open an HTTP/2 request and instantly cancel it
  (`RST_STREAM`), over and over: each request is nearly free for the attacker but forces real
  server-side work. **Google absorbed a record 398 million requests/second, Cloudflare 201M rps, AWS
  155M rps** — and the record attack came from a botnet of only **~20,000 machines**. That asymmetry —
  *cheap to send, expensive to serve* — is exactly why you shed load at the edge before the work
  happens. The defense is rate/connection limiting (cap concurrent streams and resets per connection).

- **The records kept falling (the "this is not solved" beat).** Cloudflare auto-mitigated **3.8 Tbps
  (Oct 2024)**, **7.3 Tbps (May 2025)**, and by **Q4 2025 a ~31 Tbps attack that lasted 35 seconds.**
  One-liner: *"GitHub's 2018 record has been beaten more than twentyfold — and these are now mitigated
  automatically, in seconds."*

- **AWS US-EAST-1, Dec 7 2021 — the modern self-inflicted flood** (complements the DynamoDB-2015
  retry-storm story). An automated scaling action triggered a surge of connection activity that
  overwhelmed AWS's internal network — they essentially **DDoSed themselves**, knocking out their *own*
  internal DNS and monitoring, cascading to Netflix, Disney+, Alexa, and Ring. Same "your own clients
  are the attacker" lesson as DynamoDB 2015, but bigger and more recent.

**How to use it:** keep the two-shape framing — swap the *external* flood to **Rapid Reset 2023** (with
the Tbps-records one-liner), keep **DynamoDB 2015** as the canonical *self-inflicted* flood with
**AWS 2021** as the "it happened again, bigger" beat.

### Q: If rate limiting protects the system, isn't the rate limiter itself a single box that gets overwhelmed?

**In our lab: yes — and that's an honest simplification.** The gateway (`:8000`) is a single process,
a real bottleneck and single point of failure; at Stage 04 the limiter even runs *on the single node
itself*. A real flood would flatten it. (The [`INSTRUCTOR-GUIDE.md`](INSTRUCTOR-GUIDE.md) already notes
the gateway forwards to one coordinator — same caveat.)

**In production: the rate-limit / edge layer is the *most* horizontally scaled part of the whole
system — precisely because it eats all the traffic.** It is the opposite of one box:

1. **Anycast + hundreds of POPs.** Cloudflare/Akamai/AWS announce the *same IP* from hundreds of cities
   (BGP anycast). Each client hits the nearest edge, so a flood is **geographically spread** across
   thousands of machines. That's how a multi-Tbps attack gets absorbed — never by one box, but across a
   global network.
2. **Work asymmetry is why even one edge node survives a lot.** Dropping or `429`-ing a request is O(1)
   and nearly free compared to *serving* it (a DB read/write). A little cheap work at the edge protects
   a lot of expensive work behind it — the entire reason the valve sits at the edge.
3. **Layered defense.** Volumetric L3/L4 floods (the multi-Tbps UDP stuff) get scrubbed at the
   *network* layer before they reach the app — the GitHub → Akamai/Prolexic move. Then L7 rate limiting
   at the edge. Then per-service limits deeper in. No single chokepoint.

**The deep part (and the honest catch):** horizontally scaling the limiter creates a hard new problem —
**distributed counting.**

- If each of 1,000 edge nodes keeps its *own* counter, a client capped at "100/min" can do 100/min
  *per node* → 100,000/min globally. The limit leaks.
- If they all share *one* central counter (a Redis they all `INCR`), **that central store becomes the
  new bottleneck/SPOF** — you've just moved the single box down one layer.
- Real systems escape this with **approximate counting**: local budgets (each node gets 1/N of the
  limit), "sloppy" counters, gossip/async aggregation. They trade *exactness* for *scalability* — the
  limit is enforced approximately so there's no single coordination point.

**Punchline:** rate limiting at scale isn't "one heroic box saving everyone." It's a planet-spanning,
anycast edge doing cheap O(1) work — and the genuinely hard engineering is *counting accurately across
that fleet without re-introducing the single bottleneck.* The lab shows the concept (a valve returning
429) on one box on purpose; production distributes the valve and pays for it in counting complexity.

**Sources for both answers:**
- [HTTP/2 Rapid Reset — Google Cloud](https://cloud.google.com/blog/products/identity-security/how-it-works-the-novel-http2-rapid-reset-ddos-attack) · [Cloudflare breakdown](https://blog.cloudflare.com/technical-breakdown-http2-rapid-reset-ddos-attack/) · [CISA CVE-2023-44487](https://www.cisa.gov/news-events/alerts/2023/10/10/http2-rapid-reset-vulnerability-cve-2023-44487)
- [Cloudflare 3.8 Tbps](https://blog.cloudflare.com/how-cloudflare-auto-mitigated-world-record-3-8-tbps-ddos-attack/) · [7.3 Tbps](https://blog.cloudflare.com/defending-the-internet-how-cloudflare-blocked-a-monumental-7-3-tbps-ddos/) · [2025 Q4 threat report (31.4 Tbps)](https://blog.cloudflare.com/ddos-threat-report-2025-q4/)
- [AWS US-EAST-1, Dec 7 2021 summary](https://aws.amazon.com/message/12721/) · [InfoQ postmortem](https://www.infoq.com/news/2021/12/aws-outage-postmortem/)

---

## Stage 05 — Replication

_No questions logged yet._

---

## Stage 06 — Synchronous replication

_No questions logged yet._

---

## Stage 07 — Quorum & fault tolerance

_No questions logged yet._

---

## Stage 08 — Service discovery

_No questions logged yet._

---

## Stage 09 — Auto-recovery

_No questions logged yet._

---

## Stage 10 — Full system

_No questions logged yet._
