# 2026-06-26 — Finalize build-kvstore for templating: attendee/instructor split, self-containment, readability refactor

## Context

Goal: prepare `build-kvstore/` so it can be extracted into a **separate attendee template repo**
(GitHub "Use this template") with minimal work, while this monorepo stays the development source +
portfolio artifact. Three problems to solve: (1) attendee vs. instructor material was mixed together;
(2) the workshop wasn't self-contained (Docker setup lived at the monorepo root); (3) a lot of the
system code worked but read poorly for a teaching audience.

Executed in phases with the user approving each. The code-readability audit was produced by a
subagent and is the basis for the refactor below.

## Decisions & changes

### Phase 1 — Demarcation
- New `build-kvstore/instructor/` folder, **excluded from the attendee template**. Moved
  `SPEC.md`, `HANDOFF.md`, `bugs-fixed.md` into it; `docs/` now holds only attendee-relevant
  conceptual reading (`stages.md`, `diffs/`, `load-balancing-client-vs-server.md`).

### Phase 2 — Attendee manual + instructor guide
- New `LAB-MANUAL.md` (attendee), written to a strict rule: **every fenced block is a single command
  with no inline comments**, all explanation in prose before it — so GitHub "copy" yields a clean
  command. Covers setup → the loop → stages 00–10 → dashboard/play → cheat sheet.
- New `instructor/INSTRUCTOR-GUIDE.md`: pre-flight (`make validate`), 2-hour pacing, per-stage
  teaching notes + narration, exercise answers (via `make reset STAGE=NN`), caveats, troubleshooting.
- `README.md` reworked into a short landing page pointing at `LAB-MANUAL.md` (no longer links into
  the excluded `instructor/`).

### Phase 3 — Cleanup
- Replaced the 5 legacy 211-line per-stage checkpoint/stage READMEs (05/06/07/10, stages/05) — which
  still contained non-working `labs/…` commands — with short orientation stubs pointing at the manual.
  Remaining `labs/…` mentions are only the provenance lines in `instructor/SPEC.md`.

### Phase 4 — Template self-containment
- Added `build-kvstore/{Dockerfile, docker-compose.yml, requirements.txt, .gitignore}` (path-agnostic;
  compose mounts the workshop root at `/workspace`) so the template root *is* the workshop. Added
  `instructor/TEMPLATE.md` documenting the include/exclude lists, a one-command `rsync` extraction, and
  a post-extraction checklist.

### Phase 5 — Readability refactor (behavior-preserving; `make validate` stayed green throughout)
Propagation note: files are duplicated across checkpoints in md5-identical clusters; each change was
applied to one canonical file and `cp`-ed across its cluster, **preserving the `stages/` exercise
gaps** (the gapped functions were never touched).

- **gateway.py (H1):** removed the dead load-balancer integration (`load_balancer` was always `None`;
  the `/stats` branch would have `AttributeError`'d if enabled) + unused imports; kept the rate
  limiter. Updated the doc claims that said the gateway "imports but doesn't use" the LB — it no longer
  imports it; `load_balancer.py` still ships as the code students wrote.
- **catchup.py (M3a):** trimmed to just `perform_catchup` (nothing imports the module; the coordinator
  has its own `send_catchup_to_follower` with retries). Honest docstring; dropped unused helpers/CLI.
- **registry.py (L4):** merged the double `with lock` in `/heartbeat`.
- **client.py (M1, L1):** the stats line printed `allowed/rejected` counters that `get_stats()` never
  returns → now prints fields that exist; added `graduate` to the REPL help.
- **node.py (M2, L3):** removed the dead "legacy replication" branch in `store_data` (the coordinator
  always sends explicit sync/async lists — verified) and the heartbeat `if 200: pass` no-op.
- **down.sh/up.sh/tmux_lab.sh (M5, M6):** port-map comment; "keep in sync" cross-references.
- **coordinator.py cluster B (08/09/10):** M3 (unused `signal` + dead `WRITE_QUORUM`/`READ_QUORUM`
  constants), M4 (`get_status` leader ternary), L2 (`Optional` hint + alignment comment), **H2**
  (removed the phantom `--replication-delay`: it was plumbed into `start_cluster` and dropped — the
  spawn calls hardcode `1.0`), **H3** (flattened the ~90-line nested `write_data` into guard clauses
  and extracted the async-completion logger to module level).
- **coordinator.py cluster A (05/06/07):** L2 + M4 only.

## Deliberate skips (safety over completeness)

- **`LEADER_URL` removal (node.py):** set-but-unused in the 08/09/10 cluster, but its exact text is
  identical to where it is *actively read* in 05/06/07 (`/status`, startup print). Blind removal was
  risky for ~zero value, so it was left.
- **H3 flatten on cluster A coordinator:** cluster A's `write_data` is a genuinely different code path
  (different response keys — `sync_replicated_to` as resolved IDs + `async_queued` — and `timeout=60`).
  Reusing cluster B's flattened block would change A's behavior; a bespoke flatten is high-risk for the
  secondary path. The audit marked cluster-A H3 optional, and the shipped stage-10 system (cluster B)
  is flattened.
- **Wiring `catchup.perform_catchup` into the coordinator (M3b option b):** the coordinator's version
  has retry logic `perform_catchup` lacks, so wiring them would change behavior. Left as a reference.

## Verification

- `make validate` → **18/18**, ladder invariant holds (run repeatedly per cluster and once in full).
- All 65 Python files under `build-kvstore/` parse.
- Exercise gaps in `stages/{03,04,05,08}` confirmed intact after node.py propagation.

## Addendum (2026-06-27) — LAB-MANUAL rewrite

Reworked `LAB-MANUAL.md` after review, on user direction. Three changes, two of which revise Phase 2:

1. **Reversed the "single command per fenced block" rule.** The one-command-per-block style (chosen
   in Phase 2 for clean GitHub copy) read as visually fragmented. The manual now uses **grouped
   logical command blocks with `#` comments** (the `WORKSHOP-WALKTHROUGH.md` style).
2. **`make lab` is now the primary mode for every stage.** Each stage leads with `make lab STAGE=NN`
   (explore by hand in the dashboard's control pane) and positions the **incident pane / `make up` +
   `make incident`** at the end purely as the pass/fail check. Rationale: attendees learn more by
   poking the running system than by running the checker.
3. **gap/reset described explicitly per stage.** Surfaced after finding that **`make up STAGE=NN`
   does not seed** `kvstore/` — `up.sh` runs against whatever is already there, so e.g.
   `make start` (checkpoint 00) then `make up STAGE=01` fails (`node.py` rejects `--load-factor`/
   `--workers`). The manual now states the load step for every stage: `make gap STAGE=NN` for the
   ✏️ code stages (03/04/05/08), and notes `make lab` auto-seeds the run-and-explore stages
   (equivalent to `make reset STAGE=NN`, which is also given as the manual reload/rescue).

Accuracy checks done: every control-pane helper used in the manual exists in `kvplay.sh`; `nload` is
only used on stages 02/03 (stages 00/01 have no `client.py`, so stage 01's load demo runs via the
incident pane instead); `nload` strategy-arg form used only where `HAS_LB` is set (03), bare form on
02. `README.md` still points at `LAB-MANUAL.md`; no behavior/code changed, so `make validate` is
unaffected (still 18/18).

## Lesson recorded

Never run `make validate` in the foreground — the harness's 2-minute Bash timeout kills the host-side
`docker exec` but can leave the in-container cluster running, occupying ports and causing the *next*
validate's green cases to fail spuriously (observed once here). Always run it in the background.

## Follow-ups (not done; candidates for a separate tested task)
- Make the gateway load balancer real (route across multiple coordinators) so "the code graduates" is
  literally true. - Add real allowed/rejected counters to the rate limiter. - Flatten cluster-A
  `write_data` with a bespoke transform if cross-cluster consistency is wanted.
