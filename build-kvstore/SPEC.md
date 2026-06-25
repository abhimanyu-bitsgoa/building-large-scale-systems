# SPEC — `build-kvstore/` incremental workshop

> Living source of truth for the narrative, incrementally-built distributed KV store.
> Status legend: ✅ done · 🚧 in progress · ⬜ not started.

## 1. Goal & scope

Turn the three disjoint labs into **one narrative system** built across ~11 stages (00→10),
from a single in-memory node to a Redis-/Dynamo-like distributed KV store. Each stage
transition is justified by a **red→green incident script** that breaks on the previous
checkpoint and passes on the next. Attendees work in one evolving directory and can
**reset to any checkpoint in one command**.

**Out of scope (now):** geo-distributed final project; git-tag checkpoints; the
faithful/random quorum rewrite (v1 keeps the deterministic port-pinned model).
**Untouched:** `labs/` stays as the reference. `build-kvstore/` is *derived* from it.

## 2. Design principles

- **Derive by subtraction.** `checkpoints/10` ≈ today's working system; earlier
  checkpoints are made by *removing* one feature at a time. Removing is safer than authoring.
- **Reuse lab code verbatim** where possible.
- **Black-box incident scripts** over HTTP, so one script is red before / green after an upgrade.
- **One working dir (`kvstore/`) + numbered checkpoints.** Attendees use 4 `make` verbs.
- **Never block on attendee code.** Every checkpoint is complete & runnable; `make reset` is the panic button.

## 3. Directory structure

```
build-kvstore/
  README.md  SPEC.md  Makefile  .gitignore
  kvstore/                 # evolving working dir (gitignored; seeded from checkpoints/00)
  checkpoints/00-…/ … /10-full-system/   # frozen, complete, known-good snapshots
  stages/                  # gapped starting points — only the 5 code stages (03,04,05,06,08)
  incidents/_harness.py + incident_01…10
  tools/up.sh down.sh status.py validate_ladder.sh snapshot.sh
  docs/diffs/              # per-stage "what changed & why" (esp. the two chapter boundaries)
  progress.json            # local scoreboard (gitignored)
```

## 4. Stage ladder

Ports: **00–04 → `5001+`** (single service tier); **05–10 → `registry 9000 / coordinator 7000 / gateway 8000`**
(so the final `assessment.py` runs unchanged). Port shifts coincide with the two architecture jumps.

| # | Checkpoint | Reuse source | Feature | Attendee action | Code gap |
|---|---|---|---|---|---|
| 00 | single-node | scalability `node.py` (trim) | KV behind HTTP | type/read together | — |
| 01 | vertical | + load-sim & `--workers` | single-thread ceiling (GIL≈Redis) | config | — |
| 02 | horizontal | + `client.py` (naive inline round-robin, no LB) | N nodes, dumb spread | config | — |
| 03 | load-balancing | + `load_balancer.py` (strategy pattern) | smart client-side LB | write `AdaptiveStrategy.get_node` | ✅ |
| 04 | rate-limit | + `rate_limiter.py` | protect the node | write `FixedWindow.is_allowed` | ✅ |
| 05 | replication | replication `coordinator.py`+`node.py` (trim quorum) | single-leader replication | write `replicate_to_follower` | ✅ |
| 06 | sync-replication | *same code as 05* | all followers sync (W=N) → no stale reads | config (raise W to N: W=3,R=1) | — |
| 07 | quorum + fault-tolerance | *same code as 05* | majority quorum (W+R>N) + CAP | config (W=2,R=2) | — |
| 08 | discovery | KV `registry.py` + node `heartbeat_loop` | heartbeats detect death | write `heartbeat_loop` | ✅ |
| 09 | auto-recovery | + auto-spawn + `catchup.py` | respawn + catchup | config + read | — |
| 10 | full-system | + `gateway.py`, `assessment.py`, configs | edge gateway + capstone | config-tune capstone | — |

4 code-gap stages (03 adaptive LB, 04 rate limiter, 05 replication, 08 heartbeat); the rest are
config/observe (06 became config — tune R; it shares code with 05/07). The rate limiter written at
04 is promoted to the gateway at 10 (gateway imports `load_balancer`/`rate_limiter` locally).

**Two chapter boundaries (chunky diffs, documented in `docs/diffs/`):** 04→05 (introduce
coordinator + leader/follower replication) and 07→08 (introduce registry + heartbeats).

## 5. Incident scripts

`incidents/_harness.py` exposes `report(stage, name, resolved, detail)` → prints a banner,
records into `progress.json`, exits `0` (green) / `1` (red). Each `incident_N.py` is black-box.

> Incidents **01–10** are red→green (table below). Stage **00** additionally has
> `incident_00_smoke.py`, a *baseline smoke test* (write+read round-trip on the single node)
> with **no RED counterpart** — nothing precedes it — so it is intentionally **not** part of
> `validate_ladder.sh` (which checks the 01–10 invariant). It just confirms the foundation works.

| Incident | Does | RED (prev) | GREEN (this) | Reuses |
|---|---|---|---|---|
| 01 choke | flood 1 node, measure p95 | p95 high | p95 low (workers) | new |
| 02 SPOF | load, kill a node | all fail | cluster serves | new |
| 03 imbalance | client `--strategy adaptive`, heterogeneous cluster | NotImpl / high p95 | p95 low | client driver |
| 04 flood | send > limit | no 429s | 429s | `run_rate_limit_test` |
| 05 durability | write, read other replica | miss | present | read/write |
| 06 stale | write then immediate read | stale | fresh | `run_stale_read_test` |
| 07 outage | kill floor(N/2), write | 503 | succeeds | `run_kill_nodes_test` |
| 08 blind | kill node, poll status | "alive" | "dead" | `/status` |
| 09 degraded | kill follower, wait | stays dead | respawned+data | spawn+read |
| 10 capstone | run assessment | n/a | score ≥ threshold | `assessment.py` |

`tools/status.py` renders the ladder from `progress.json`.

## 6. Makefile + tooling

Attendee verbs: `make start` · `make up STAGE=NN` · `make down` · `make incident STAGE=NN`
· `make reset STAGE=NN` · `make status`. Author verbs: `make validate` · `make snapshot`.
`tools/up.sh` is a per-stage `case` hiding multi-process startup. Everything runs inside the
existing Docker container (no host ports — `7000` collides with macOS Control Center on host).

## 7. Authoring method (derive by subtraction)

1. Scaffold skeleton. ✅
2. `checkpoints/10` from `labs/distributed-kvstore` + local `load_balancer.py`/`rate_limiter.py`;
   gateway imports made local. Verify `assessment.py` = 100. ✅
3. Subtract backward 09→05: remove gateway → 09; remove auto-spawn+catchup → 08;
   remove registry+heartbeats → 07; 07≡06 (config-only); remove quorum → 05. Verify each boots.
4. `checkpoints/04…00` from `labs/scalability` (node grows down to a bare dict). Verify each boots.
5. `incidents/01…10` (reuse `assessment.py` functions). 
6. Gapped `stages/` (03,04,05,06,08) with `raise NotImplementedError("STAGE N: …")` + per-stage README.
7. Flesh `up.sh`/tmux/`status.py`; rehearse twice.

## 8. Validation invariant (definition of done)

> For every N: `incident_N` exits **RED on `checkpoints/(N-1)`** and **GREEN on `checkpoints/N`**.

`tools/validate_ladder.sh` automates this. All-green ⇒ the ladder is provably correct.

## 9. Resolved decisions (2026-06-14)

1. Quorum: keep deterministic port-pinned for v1 + honest caveat slide.
2. Ports: 00–04 `5001+`, 05–10 KV `7000/8000/9000`.
3. Code stages: 03,04,05,06,08.
4. Boundaries 04→05 and 07→08 accepted as documented chapter breaks.
5. Docker-only; reuse current container.
6. `labs/` untouched.
7. Spec persisted here; stage count 11 (00–10).

## 10. Phase status

| Phase | Deliverable | Status |
|---|---|---|
| 0 | scaffold + spec + harness + Makefile | ✅ |
| 1 | `checkpoints/10` (verified 100) | ✅ |
| 2 | `checkpoints/09…05` (subtraction) | ✅ — 10/09/08/07/06/05 all built & verified |
| 3 | `checkpoints/04…00` | ✅ — built & verified (00 bare RW, 01 load-sim, 03 adaptive<RR, 04 429s) |
| 4 | `incidents/01…10` | ✅ — all 10 validated green on checkpoints, red on gaps |
| 5 | `stages/` gaps + per-stage guide | ✅ — 4 gaps (03/04/05/08) + `docs/stages.md` |
| 6 | Makefile/tools + end-to-end smoke | ✅ — start/gap/up/down/incident/reset/status all work |

**The build is complete:** 11 checkpoints, 10 incidents, 4 code gaps, the Makefile toolchain,
the per-stage guide, and the bug log — all verified inside the container. As of 2026-06-15,
`tools/validate_ladder.sh` is a **working regression suite** (`make validate`): it boots each
checkpoint via its own `up.sh`, asserts `incident_N` GREEN on `checkpoints/N` and RED on a
per-stage "before" state, and confirms ports free between cases — 20/20 cases pass. See
[`wiki/decisions/2026-06-15_build-kvstore-validate-ladder.md`].

As of 2026-06-25 the former "optional polish" is **done**: `docs/diffs/` now holds the full
narrative arc (`README.md`) plus the two chapter deep-dives (`04-to-05-replication.md`,
`07-to-08-discovery.md`); and `make lab STAGE=NN` (`tools/tmux_lab.sh` + `tools/kvplay.sh`) gives
the cluster stages (05–10) a per-service tmux dashboard with a control pane to kill/spawn nodes by
hand. The code-gap exercises (04/05/08) were also trimmed to a single core line each (boilerplate
pre-filled). See `wiki/decisions/2026-06-25_build-kvstore-tmux-diffs-gap-reduction.md`.

## 11. Replication chapter (05/06/07) — how it's built

`05/06/07` reuse the **replication lab** verbatim (`coordinator.py`, `node.py`, `client.py`),
with two edits: `BASE_PORT 6000→7000` (port consistency) and `/kill` → `process.kill()`
(crash semantics). The three stages share code and differ only by `W`/`R` in `up.sh`:
- **05** runs `W=1,R=1` → `W+R≤N` → immediate read is **stale (404)**, fresh after ~5s.
- **06** runs `W=2,R=2` → `W+R>N` → immediate read is **fresh**.
- **07** runs `W=2,R=2` → kill `floor(N/2)` survives; killing more → **quorum loss (503)**.
All three verified on clean ports.

## 12. Testing note (avoid two foot-guns)

Cluster verification runs inside the container. Two gotchas, both burned time once:
1. **`pkill -f` self-matches the test script.** A `bash -c` body that contains `python
   coordinator.py …` is itself matched by `pkill -f coordinator.py` (even bracketed
   `[c]oordinator.py`, because the literal `coordinator.py` still appears in the body). **Keep
   `pkill` in a *separate* shell call** that contains only bracketed patterns
   (`[c]oordinator.py`, `[n]ode.py`, `[r]egistry.py`, `[g]ateway.py`) and no literal command
   names — otherwise the cleanup SIGKILLs the test (exit 137/143) before it finishes.
2. **Leftover node processes pollute ports 7002–7004** between runs and serve *stale* data,
   masking real behavior. Always clean (call #1) and confirm `0 procs / ports free` before a run.
