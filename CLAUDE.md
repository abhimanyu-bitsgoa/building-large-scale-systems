# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A hands-on **distributed-systems teaching workshop** (used for a EuroPython tutorial). It is not a deployable product — it is a set of runnable labs that students start as multiple local processes and interact with to *observe* distributed-systems behavior (load balancing, replication quorums, failover). Code clarity and observable behavior matter more than production concerns.

## Persona

You are a thoughtful, distinguished programmer. Write code that is maintainable, correct, and non-complex. Prefer the simplest design that fully solves the task. Match the surrounding code's patterns, naming, and idioms.

## Working principles

- **Plan before you code.** Lay out the steps first. Deliberate multiple approaches and pick the best one for the context — don't grab the first that works.
- **No assumptions.** Don't assume how code or a task behaves without solid reasoning or having read it. If anything is unclear, ask.
- **One task at a time.** Finish and verify a task before starting the next.
- **Protect against breakage (top priority).** After any change, run the evals to confirm you haven't broken existing functionality (see **Environment & running** — the KV-store assessment is the only automated check). Decide up front how you will verify each task's correctness.
- **No gratuitous refactoring.** Don't refactor beyond what the task needs. If you see a compelling case, ask the user before proceeding.
- **Reuse before adding.** Search for existing functions, utilities, and patterns to reuse instead of writing new code. Flag anything not up to best practice.
- **Learn from history.** Before proposing or changing something, read `wiki/decisions/` to understand why things are the way they are. Don't repeat mistakes already identified and corrected; surface any conflict with that recorded knowledge to the user.

## Logging decisions

Maintain a decision log under `wiki/decisions/` so future agents and contributors understand *why* changes were made — it is the source the **Learn from history** principle reads from. Whenever you make a non-trivial change:

1. Add a file named `YYYY-MM-DD_short-kebab-slug.md` (e.g. `2026-05-28_adk-ollama-gemma4-fix.md`) in `wiki/decisions/`.
2. Document **in detail**: the rationale, the alternatives considered and their trade-offs, and the side effects/risks of the change. Write so that someone *new* to the codebase understands both *what* was done and *why*. Err on the side of over-explaining.
3. Add a row for it to `wiki/decisions/INDEX.md` (newest first) — **always update the index in the same change** as the new decision file, so the log stays discoverable.

Keep this folder current alongside your commits — one decision file per non-trivial change.

## Environment & running

Everything runs **inside a Docker container** so ports never touch the host:

```bash
docker-compose up -d                      # build + start the container
docker-compose exec workshop bash         # get a shell inside it
```

The container has a Python venv pre-activated at `/opt/venv` (so `python` works directly, deps from `requirements.txt` are installed). The repo is bind-mounted at `/workspace`. No ports are exposed to the host **by design** (avoids macOS AirPlay conflicts) — all interaction happens via shells *inside* the container.

There is **no build step, no linter, and no unit-test suite.** The only automated check is the KV-store assessment (below). Each lab component is a standalone FastAPI + uvicorn process started by hand in its own terminal (`docker-compose exec workshop bash` per terminal).

## The three labs (increasing complexity)

| Lab | Dir | Teaches |
| --- | --- | --- |
| Scalability | `labs/scalability/` | Load balancing strategies, fixed-window rate limiting, vertical vs horizontal scaling |
| Replication | `labs/replication/` | Single-leader replication, write/read quorums, sync vs async lag |
| Distributed KV Store | `labs/distributed-kvstore/` | Everything combined + service discovery, heartbeats, auto-failover, catchup |

They build on each other conceptually; the KV store is the capstone integration of the first two.

## Port conventions (memorize these — they're consistent across labs)

- **Scalability**: nodes on `5001`, `5002`, … (default `5000`)
- **Replication**: coordinator API `6000`, leader `6001`, followers `6002+`
- **KV Store**: registry `9000`, coordinator `7000` (spawns leader/followers on higher ports), gateway `8000`

## Core architectural concept: the quorum invariant

The replication and KV-store labs both hinge on one rule, and most of the code and exercises exist to demonstrate it:

> **W + R > N** guarantees no stale reads (the write set and read set are forced to overlap).

Where `N` = number of followers, `W` = follower acks required for a write, `R` = followers queried on read. The leader always writes first; **W and R count followers only.** Sync followers (the first W by port) replicate fast (~0.5s); the rest replicate async with deliberately visible lag (~5s) so students can *watch* stale reads happen when `W + R ≤ N`.

## Component topology (KV store — the full system)

```
Client → Gateway (rate limit, :8000) → Coordinator (quorum, :7000) → Leader + Followers
                                              ↕
                                        Registry (:9000, heartbeats + auto-spawn)
```

Key cross-file behaviors that require reading several files to understand:

- **The coordinator spawns nodes as subprocesses** (`coordinator.py` launches `node.py` with `--port`/`--id`). Killing a follower (`POST /kill/{node_id}`) and spawning (`POST /spawn`) manipulate these subprocesses. Spawn reuses the dead follower's port to keep topology predictable.
- **Service discovery is heartbeat-based** (`registry.py`). With `--auto-spawn`, the registry respawns followers whose heartbeats lapse after `--spawn-delay` seconds. An *aggressive* delay causes "ghost nodes" (a real exercise — INC-2).
- **Catchup** (`catchup.py`) syncs a newly spawned follower from the leader's snapshot — this is core system code, **not** a student solution file.

## Student-exercise structure (important when editing labs)

The labs are designed around fill-in exercises, so be careful what you treat as "incomplete":

- **`TODO: [STUDENT EXERCISE]` comments** mark intentional gaps (notably in `scalability/node.py` and `rate_limiter.py`). Don't "fix" these unless asked — they're the exercise.
- The KV-store mini-project (`scenario_brief.md`) frames 5 production incidents the student fixes **by editing config, not code**:
  - `student_config.json` — the broken starter config the student edits.
  - `student_config_solution.json` — the **answer key** (correct values + written justifications). Treat as a spoiler; do not surface it to students.
  - `instructor_config.json` — test scenarios/weights/expected values consumed by the assessment.
- **Assessment / the only automated check:**
  ```bash
  python labs/distributed-kvstore/assessment.py --config student_config.json
  ```
  It spins up the cluster with the given config and scores it out of 100 across incident scenarios (INC-0/1/3/4). This is how you "run tests" here — there is no pytest.

## Conventions

- Every service is FastAPI started via `uvicorn.run(...)` in a `main()` guarded by argparse; CLI flags (`--port`, `--followers`, `-W`/`--write-quorum`, `-R`/`--read-quorum`, etc.) are the configuration surface.
- `client.py` in each lab is the primary interactive entry point; `curl` against the documented endpoints is the manual alternative (see each lab's README API table).
- Each lab's `README.md` contains the authoritative, step-by-step demo sequences — consult them before changing run behavior.
