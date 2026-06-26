# 2026-06-26 — Remove the stage-10 CloudCart capstone + `assessment.py`; keep stage 10 as a demo

## Context

This **supersedes** the earlier same-day decision
[`2026-06-26_stage-10-finale-demo-and-gateway-lb-correction.md`](2026-06-26_stage-10-finale-demo-and-gateway-lb-correction.md),
which *demoted* the CloudCart capstone to an "optional take-home" but kept all of its machinery in the
repo. On further review the machinery was judged not worth keeping for the workshop at all:

- **It was clunky and confusing.** Stage 10's "incident" was the odd one out: every other stage's
  incident probes the *running* `make up` system, but `incident_10_capstone.py` shelled out to
  `assessment.py`, which booted its **own** cluster on the **same ports** (`:7000/:8000/:9000`). Hence
  the "don't run the grader while `make lab STAGE=10` is up — port clash" advisory, which only existed
  to paper over that collision.
- **It was shallow.** `assessment.py` graded INC-0/1/3/4 — re-tests of what stages 04/06/07 already
  teach — and didn't grade two of the five tickets (INC-2 ghost node, INC-5 cost).
- **N mismatch.** The grader used an **N=5** cluster while the whole lab runs **N=3**, so its numbers
  never lined up with what attendees built.

The user's call: stage 10 is the **integration of the gateway** and the best *showcase* of the whole
KV store, so **keep the stage** — but **delete the assessment/capstone/CloudCart layer entirely** and
let stage 10 be a pure, hand-driven demo with **no incident**.

## Decision

**Stage 10 stays as the whole-system gateway demo (`make lab STAGE=10`) with no incident and no
grader.** The CloudCart capstone and its grader are removed from the workshop.

### Deleted (tracked)
- `incidents/incident_10_capstone.py`
- `checkpoints/10-full-system/assessment.py`
- `checkpoints/10-full-system/scenario_brief.md`
- `checkpoints/10-full-system/student_config.json`
- `checkpoints/10-full-system/student_config_solution.json`
- `checkpoints/10-full-system/instructor_config.json`
- (plus the git-ignored mirror copies in the working `kvstore/`)

**Kept** in checkpoint 10 — the demo system: `gateway.py`, `coordinator.py`, `node.py`,
`registry.py`, `catchup.py`, `client.py`, `load_balancer.py`, `rate_limiter.py`, trimmed `README.md`.
Verified that `tools/up.sh` (stage 10) and `tools/tmux_lab.sh` boot the demo from **CLI flags only** —
they never read the config JSONs — so deleting those does not affect the demo path.

### Validator (`tools/validate_ladder.sh`): 20 → **18 cases**
The stage-10 green/red pair was the **only** place `assessment.py` ran anywhere in the repo. Removed:
the two `run 10 …` lines, `10` from the default loop list, and the header clause describing
`10 red = broken student_config.json`. Stages 01–09 are independent cases, so nothing else changed.
This is the user's explicit "tune the validator so it doesn't count my script" ask.

### Tooling
- **`Makefile` `incident` target** now guards against a missing incident file: `make incident STAGE=10`
  prints *"Stage 10 is a demo — no incident. Run 'make lab STAGE=10'."* instead of erroring on an
  empty glob.
- **`tools/status.py`** renders stage 10 as a `🖥️ demo` row and **excludes it from the resolved
  count** (it can never "pass" — there's no incident), so the scoreboard reads e.g. `9/10` not a
  permanently-stuck `x/11`.
- **`tools/tmux_incident.sh`** (the "watch the servers react to an incident" view) now rejects stage 10
  with a pointer to `make lab STAGE=10`, since there's no incident to watch.

### Docs scrubbed
`SPEC.md`, `docs/stages.md` (§10), `docs/diffs/README.md` (the `09 → 10` section + ASCII arc + TOC
anchor), `docs/diffs/07-to-08-discovery.md`, `build-kvstore/README.md`, `docs/HANDOFF.md`,
`checkpoints/10-full-system/README.md` (file table + the "Student Mini-Project" section), and
`WORKSHOP-WALKTHROUGH.md` (removed the "CloudCart capstone — optional take-home" subsection; kept the
4-beat live demo; updated counts **20/20 → 18/18**, ladder/pacing rows, pre-flight re-run list, TOC).

## Alternatives considered

- **Keep it as a take-home (the prior decision).** Rejected: it left the port-clash advisory, the N=5
  confusion, and a shallow grader in the repo — exactly the clunk the user wanted gone. "Optional" did
  not remove the maintenance/confusion surface.
- **Deepen `assessment.py`** to grade all 5 tickets. Rejected: re-promotes a graded climax, the
  opposite of the goal, and adds surface to maintain.
- **Rewrite the tickets to N=3** so the grader matches the lab. Rejected: the tickets are written
  around "5 followers, lose 2" / "$60/hr"; not worth a rewrite for a feature being removed.

## Risks / side effects

- `make validate` now reports **18/18** instead of 20/20 — intended; every doc quoting the old count
  was updated.
- `labs/` and the root `CLAUDE.md` are a **separate, legacy** lab structure with their *own*
  `assessment.py`; they were deliberately **left untouched** (out of scope).
- Historical records were left as-is on purpose: prior decision files, and `docs/bugs-fixed.md`
  (which logs a since-removed `assessment.py` bug) — they document what happened and are not rewritten.

## Verification
- `make validate` → expect **18/18**, ladder invariant holds.
- `make lab STAGE=10` → demo still boots (registry/coordinator/gateway panes + control helpers).
- `make incident STAGE=10` → friendly "demo, no incident" line, exit 0.
- Repo-wide grep for `assessment|capstone|cloudcart|scenario_brief|student_config|instructor_config|INC-10`
  → only historical decision-log / `bugs-fixed.md` hits remain.
