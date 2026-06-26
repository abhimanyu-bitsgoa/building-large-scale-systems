# 2026-06-26 — Stage 10 becomes a synthesis demo + take-home; correct the gateway load-balancer claim

## Context

Two issues with the end of the workshop, surfaced while prepping a **2-hour** lab slot:

1. **The CloudCart capstone (stage 10) was the mandatory finale, and it's weak.** Its auto-graded
   100 points (INC-0/1/3/4) are re-treads of stages 04/06/07; two of its five tickets (INC-2, INC-5)
   aren't even graded; the `<details>` hints hand over the answers; it uses an **N=5** cluster while
   the whole lab runs **N=3** (confusing); and it's a mode-switch to JSON editing. Ending a 3-hour
   (now 2-hour) room on a long graded config-edit is anticlimactic and time-risky.
2. **The docs claimed the load balancer "returns at the gateway" — it doesn't.** Reading
   `gateway.py`: it imports `LoadBalancer` but never instantiates it (the `load_balancer` global stays
   `None`); writes/reads are forwarded to a **single** coordinator. Only the `rate_limiter` actually
   runs at the edge. `SPEC.md` and `docs/diffs/README.md` asserted otherwise.

## Decision

**Stage 10 is now a 5-minute speaker-led whole-system demo; the hands-on workshop ends at stage 09
(self-healing).** The CloudCart capstone is demoted to an **optional take-home** (kept, not deleted).

- **The finale demo** (run `make lab STAGE=10`, drive from the control pane) has 4 beats:
  1. trace one `kvwrite`/`kvread` through gateway → coordinator → leader → followers;
  2. `kvflood` the gateway → 429s (rate limiter at the edge);
  3. `kvwrite` canary → `kvkill 1` (quorum holds) → auto-respawn + catchup → `kvread` still fresh;
  4. the closing line.
- **Stage 09 is flagged as the hands-on climax**, and a **2-hour core-path table** is added to the
  walkthrough pacing section (framing 00/02; fast config 01/06/07; code 03/04/05/08; climax 09; 10 =
  demo + take-home).

### "Demote, don't delete" (chosen over full removal)

The graded `assessment.py` + configs + INC-10 stay in the repo, so `make validate` remains **20/20**
and motivated attendees can still self-check. The walkthrough simply stops *featuring* the checker —
it presents `scenario_brief.md` as a reasoning exercise ("name the wrong knob, justify the fix") and
mentions the self-check grader with its N=5 caveat. Rejected alternative: deleting the grader (drops
validate to 18/18 and contradicts `CLAUDE.md`'s "only automated check" — more surface area, removes a
working artifact). The zero-risk demote addresses the "shallow/confusing" complaint without churn.

### Gateway load-balancer correction

Reframed `SPEC.md` and `docs/diffs/README.md` (the through-line note + the 09→10 section): at stage 10
the **rate limiter** returns to the edge; the **load balancer does not** (gateway forwards to one
coordinator; imports `LoadBalancer` unused). The load-balancing *responsibility* moved **server-side
into the coordinator's quorum routing** — the client-side→server-side migration from stages 02–04
(ties to `docs/load-balancing-client-vs-server.md`). The walkthrough beat-1 narration says this out
loud, with the honest "we're not balancing across coordinators here" caveat.

## Read-selection code left untouched (and why)

We considered making the coordinator pick the `R` followers for a read via the load balancer
("least-loaded") instead of the deterministic `get_read_followers` (highest-`R` ports). **Rejected
for the lab:** `W+R>N` makes *any* R-subset correct, so it's sound in theory, but the deterministic
opposite-ends selection (sync = lowest-`W` ports, read = highest-`R` ports) is what makes the stage-05
stale read **reproducible every run**. Load-aware reads would make staleness flaky. Kept as a
**stage-07 talking point** instead ("real systems read the R fastest replicas + reconcile by version;
we pick deterministically so staleness is observable").

## New helper

Added `kvflood [n]` to `tools/kvplay.sh` (cluster tier): fires n quick writes and prints status codes
so the gateway rate limiter's 429s are visible in beat 2. Also fixed the stale self-check path in
`scenario_brief.md` (`python labs/distributed-kvstore/assessment.py …` → `make incident STAGE=10`).

## Verification

`make validate` re-run → expect **20/20** (grader and ladder untouched; `kvflood` is additive and not
exercised by validate). Shell scripts pass `bash -n`.

## Files touched
- Edited: `build-kvstore/tools/kvplay.sh` (kvflood + kvhelp),
  `build-kvstore/checkpoints/10-full-system/scenario_brief.md` (+ working `kvstore/` copy) path fix,
  `build-kvstore/SPEC.md`, `build-kvstore/docs/diffs/README.md`, `build-kvstore/docs/stages.md`,
  `build-kvstore/README.md`, `WORKSHOP-WALKTHROUGH.md` (§7 rewrite, §09 climax note, §07 LB↔quorum
  talking point, 2-hour core-path table, TOC + ladder row), `wiki/decisions/INDEX.md`.
- Not changed (deliberately): `coordinator.py` `get_read_followers`, `assessment.py`,
  `instructor_config.json`, `student_config*.json`, `CLAUDE.md`.
