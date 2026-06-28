# Preparing Your EuroPython 2026 Tutorial — Full Report

## 0. The one mental shift that drives everything

**A talk is a performance you deliver; a tutorial is a learning experience you facilitate.** Your success metric isn't "did I explain quorums well?" — it's "did *they* watch a stale read happen on their own laptop and understand why?" Almost every tactic below follows from that shift: you spend your energy detecting silent struggle and keeping ~50 people *unblocked and in sync*, not on eloquent delivery. ([Trey Hunner's PyCon tutorial guide](https://treyhunner.com/2025/05/how-to-give-a-great-pycon-tutorial/) is the single best resource — read it end to end.)

This matters more for you than most tutorials because **EuroPython does not record tutorials** (deliberately, to keep the atmosphere relaxed). There's no "catch the video later" safety net — the in-room experience and your written, self-paced lab materials *are* the deliverable. Your existing `WORKSHOP-WALKTHROUGH.md` is exactly the right asset; make sure attendees can follow it without you.

---

## 1. The EuroPython 2026 facts that constrain your design

| Fact | Detail | Source |
|---|---|---|
| **Dates / city** | July 13–19, 2026, Kraków (ICE Kraków Congress Centre) | [ep2026](https://www.ep2026.europython.eu/) |
| **Tutorial days** | Mon–Tue, **July 13–14** (talks Wed–Fri, sprints weekend) | [FAQ](https://ep2026.europython.eu/faq/) |
| **Duration** | **180 min including a built-in 15-min coffee break** (~165 working min), plus **20 min setup** before the room officially starts | [Guidelines](https://ep2026.europython.eu/guidelines/) |
| **Attendees** | No pre-signup; first-come seating. Rooms range ~40 to ~100. **You cannot predict count or skill mix** | [FAQ](https://ep2026.europython.eu/faq/) |
| **Not recorded** | Tutorials are *not* livestreamed/recorded | [Guidelines](https://ep2026.europython.eu/guidelines/) |
| **AV** | HDMI + wired ethernet + Type-E power at podium; 1080p projector. Bring your own USB-C→HDMI adapter | [Guidelines](https://ep2026.europython.eu/guidelines/) |
| **Code display** | Font **≥24pt / ≥175% zoom**, **light theme**, avoid the lower third of the screen (cut off / blocked by heads) | [Guidelines](https://ep2026.europython.eu/guidelines/) |
| **TAs/helpers** | Allowed & encouraged — but you must add them in Pretalx and email the Programme Committee in advance | [Guidelines](https://ep2026.europython.eu/guidelines/) |
| **International audience** | Explicit instruction: don't speak fast, speak clearly; **no live captioning exists** | [Guidelines](https://ep2026.europython.eu/guidelines/) |
| **Speaker support** | Mentorship programme (4×1-hr mentor sessions incl. rehearsal) + on-site **Speaker Ready Room** to test setup | [Mentorship](https://ep2026.europython.eu/mentorship/) |

**Implications for you:** light-theme terminals at ≥24pt (dark themes wash out on weak projectors); slides accessible (≥18pt sans-serif, high contrast, **avoid red/green pairs** for color-blindness — ironic given red/green sticky notes, but that's physical paper, not slides); upload slides + the walkthrough to Pretalx Resources and put a QR code in the room since there's no recording.

---

## 2. Your top risks, ranked — and how to neutralize them

These are the failure modes a *tutorial* has that a talk doesn't. Ranked by how much they threaten *your specific* Docker-cluster workshop.

### Risk #1 — Docker setup + conference WiFi eats 30 minutes
50–60 laptops pulling/building images simultaneously over conference WiFi (estimated **<1 Mbps/attendee**) will fail. This is your single biggest risk.

- **Push the heavy download to *before* the conference.** Your tutorial description and a setup email (sent ~1–2 weeks out, then re-sent 2–3 times — people register late and ignore the first email) must instruct `docker-compose build` / `docker pull` at home so images are cached locally. EuroPython explicitly expects pre-conference setup instructions for exactly this reason.
- **Carry the image on USB sticks as the offline fallback.** `docker save` → attendees `docker load`, no network. For a multi-image stack, a [USB-hosted local Docker registry](https://github.com/meyskens/registry-usb) lets people pull from a thumb drive.
- **Ship a one-command verify script.** A `make check` / `verify.sh` that confirms Docker runs, the image exists, and a container boots gives attendees a binary green/red *before* they walk in, and gives you a fast triage signal. You already have `make validate` — add a lightweight "is my environment sane" check that's faster than the full assessment.
- **Bring your own 4G/5G hotspot** for the podium machine; never depend on venue WiFi for your own demo.

### Risk #2 — The room silently desyncs and you don't notice
In a talk, lost audience is invisible and harmless. In a tutorial it's a *failed* tutorial. ~20% of the room will be behind at any given moment no matter what.

- **Red/green sticky notes** (Software Carpentry's signature system): each laptop lid gets a green and a red sticky. Green = done/fine, red = stuck. It's discreet, lets people keep typing while flagged, and a glance reads the whole room's state. A wall of red corners means *slow down*.
- **Get 1–2 TAs minimum** (PyCon heuristic: ~2 per 20 attendees; for a 40–100 room, more). Their job is to catch people falling behind in the first exercise or two and **intervene before frustration sets in**. Register them in Pretalx now.
- **Git recovery checkpoints** — you already have this infrastructure (`make lab STAGE=NN`, the stage/checkpoint branches). Make it explicit to attendees: "if you're stuck or broke something, `git checkout stage-05` and you're back in sync with everyone." This is the highest-value technique for keeping a heterogeneous room converged, and your repo is already built for it.

### Risk #3 — Time runs away (or you finish early)
Tutorials are not rehearsable to a fixed length like talks — pace depends on the room. Real attendees run *much* longer than your solo rehearsal (one presenter's 60-min solo run took 80 min live).

- **Know your core path vs. skippable "cutting-room-floor" material in advance.** Your INC-2 (ghost nodes, unscored) and INC-5 (cost, advisory) are natural skip/stretch candidates; INC-0/1/3/4 are the scored core.
- **Plan a deliberately-skippable ~20–30 min stretch block** at the end for both fast finishers and timing slack.
- **Rehearse at realistic scale** — ideally a dry run with a few colleagues on *their* laptops, not just yours.

---

## 3. A concrete run-of-show (~175 min)

Best-practice cadence is a **~10-min hands-on exercise roughly every ~20 min** of new material — you should be stopping constantly. ⚠️ **One gentle flag:** your current plan front-loads ~50 min of theory. The research is emphatic that engagement craters after ~10–15 min of continuous lecture. I'd **distribute that 40% theory into the "teach" head of each lab loop** rather than delivering it as one upfront block. Here's an interleaved arc that still respects 40/60:

| Time | Segment | Mode |
|---|---|---|
| **−20 → 0** | Doors open. Setup help, hand out sticky notes, attendees run `verify.sh` | Setup window |
| **0:00–0:12** | **Cold open**: a real planet-scale outage story → why this matters. Framing + setup checkpoint ("run X, raise green sticky") | Hook |
| **0:12–0:30** | Theory: scalability (LB strategies, rate limiting, vertical vs horizontal) — ~15 min, then demo | I-do |
| **0:30–0:55** | **Lab 1 — Scalability.** Round-robin vs adaptive, the rate-limit choke. POE on each | We-do → you-do |
| **0:55–1:20** | Theory: single-leader replication + **W+R>N**; then **Lab 2 — Replication**: *watch* a stale read happen | I-do → you-do |
| **1:20–1:35** | ☕ **COFFEE BREAK** (at the seam, never mid-exercise) | Break |
| **1:35–2:00** | Theory: service discovery, heartbeats, failover/CAP; intro the capstone topology | I-do |
| **2:00–2:40** | **Capstone — KV-store incidents.** Fix INC-0/1/3/4 by editing config; score with `assessment.py` | You-do-together (pairs) |
| **2:40–2:55** | Stretch (INC-2/INC-5) for fast finishers + **wrap-up, next steps, CTA** | Buffer + close |

Put the coffee break at a *natural seam* between labs. End with an explicit "here's what you can now build / go read" — since there's no recording, the wrap-up is their takeaway.

---

## 4. Teaching technique — tuned for distributed systems

Your subject is *invisible behavior* (lag, quorum overlap, failover). The whole game is making it observable. Four techniques, in priority order:

1. **Predict-Observe-Explain (POE) on every fault/quorum demo.** Before you kill a node or run a stale read, make the room *commit to a prediction*: "W=1, R=1, N=3 — will this read be stale? A or B?" Then run it. Then explain the gap. The prediction commits them; the surprise cements the lesson far better than just showing the result. This doubles as a live comprehension check. Your incident framing is *built* for this.

2. **Make it visible: time-space diagrams + side-by-side log panes.** Teach replication/quorums with Lamport-style time-space diagrams (each node = a vertical lifeline, time flowing down, arrows = messages); show the write-set and read-set as overlapping/non-overlapping regions so `W+R>N` is something they can literally point at. An empirical study (ShiViz, 109 students) found interactive time-space diagrams produced *large* learning gains for system comprehension. Pair that with your **tmux dashboards** — one pane per node so replication lag is a thing they *see scroll*, not a number you assert. You already built `tmux_lab.sh` / `tmux_incident.sh` for exactly this; lean on them hard.

3. **Fault injection as a "game day."** Your `kill -9` / spawn exercises are textbook-correct teaching. Frame them as a game day: predict verbally → inject → observe → reset. Always have a clean reset (your checkpoints) so compounding failures don't derail the room.

4. **I-do / we-do / you-do (gradual release).** *I-do*: you run the cluster and narrate. *We-do*: the room runs the same commands in lockstep (spend real time here — it's pivotal). *You-do*: pairs fix the incident themselves. Lead each lab with a **worked example**, then fade the scaffolding (don't keep hand-holding experts — the "expertise-reversal effect" means worked examples *bore* people who already have the schema).

**Live-demo insurance (the demo gods are real):**
- **Record each demo with [asciinema](https://docs.asciinema.org/)** (markers at narration points, `--pause-on-markers`). Tiny text files, copy-pasteable, and the perfect terminal-demo fallback. Combined with your git checkpoints, that's a two-layer safety net.
- **Avoid typing live** — open and run pre-tested commands; talk *then* type *then* explain the result, not all at once. Typos propagate into 50 broken laptops.
- **Light theme, ≥24pt, keep output in the upper half, clear screen often, kill notifications.**

---

## 5. A credibility note specific to your content

Your own readiness notes flag that the lab's model is a **pedagogical hybrid** — `W+R>N` (a leaderless/Dynamo idea) bolted onto a single-leader system, with overlap engineered by port ordering; and there's **no leader failover/election** (auto-respawn only recovers *followers*). EuroPython's tutorial audience is highly international and includes people who run these systems in production — someone *will* ask. **Pre-empt it with one honest "what this models and what it doesn't" slide.** Saying "this is a teaching simplification; real Dynamo/Raft does X differently" *raises* your credibility rather than risking it, and it's the intellectually honest move. Don't let "automatic failover" in the outline overstate what the code does — call it "automatic follower recovery + catchup."

---

## 6. Pre-conference timeline (checklist)

**Now → 2 weeks out**
- [ ] Register your TA(s) in Pretalx; email the Programme Committee for their access.
- [ ] Write the setup instructions for your tutorial description (Docker install + pre-build/pull command).
- [ ] Build `verify.sh` / `make check` (fast environment sanity check, separate from full `assessment.py`).
- [ ] `docker save` your image(s) onto 2 USB sticks; test `docker load` on a clean machine.
- [ ] Record asciinema fallbacks for each demo + a slide-based backup of the whole flow.
- [ ] Consider booking a mentorship rehearsal session.

**1 week out**
- [ ] Send setup email #1 (and schedule re-sends). Include a short, hand-typeable URL.
- [ ] Dry run on a *different* machine over a constrained network. Time it with attendees if possible.
- [ ] Mark core vs. skippable content; finalize the stretch block.
- [ ] Upload slides + `WORKSHOP-WALKTHROUGH.md` to Pretalx Resources; make a QR code.

**Day before / day of**
- [ ] Re-send setup reminder. Test setup in the Speaker Ready Room.
- [ ] Arrive 20 min early; help early-setup stragglers; distribute red/green sticky notes.
- [ ] Bring: USB sticks, USB-C→HDMI adapter, 4G hotspot, power strip (Docker + multi-process drains laptops over 3 hrs — outlets matter).
- [ ] First slide = the prereqs URL; keep telling trickle-in arrivals to start setup.

---

## 7. Two repo items worth closing before Kraków

From your own readiness notes, these directly affect live delivery (your call on priority):
- **Scalability README Demo 2 worker/capacity labels are inverted** — would break the adaptive-vs-round-robin demo live (Lab 1, the very first hands-on). Worth fixing.
- **A fast `verify.sh`** doesn't exist yet — high value for Risk #1.

I can spin up either of those, draft the attendee-facing setup email, build the asciinema fallback script, or write the "what this models / what it doesn't" honesty slide — just say which.

---

**Sources** (full set): [Trey Hunner — PyCon tutorial guide](https://treyhunner.com/2025/05/how-to-give-a-great-pycon-tutorial/) · [EuroPython 2026 Guidelines](https://ep2026.europython.eu/guidelines/) / [FAQ](https://ep2026.europython.eu/faq/) · [Mercedes Bernard — 7 tips for a coding workshop](https://mercedesbernard.com/blog/7-tips-for-successful-coding-workshop/) · [Matt Burke — structuring a conference workshop](https://www.mattburke.dev/how-to-structure-a-workshop-for-a-tech-conference/) · [Software Carpentry — Live Coding is a Skill](https://carpentries.github.io/instructor-training/17-live.html) · [PLOS — Ten quick tips for live coding](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1008090) · [ShiViz time-space diagram study](https://www.cs.ubc.ca/~bestchai/papers/tosem20-shiviz.pdf) · [registry-usb](https://github.com/meyskens/registry-usb) · [asciinema](https://docs.asciinema.org/)
