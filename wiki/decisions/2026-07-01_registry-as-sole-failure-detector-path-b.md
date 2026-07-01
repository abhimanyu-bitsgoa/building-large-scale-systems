# 2026-07-01 — Make the registry the sole failure detector (stages 08/09 redesign, "Path B")

**Status:** accepted
**Scope:** stages 05–10 coordinator/registry/node behavior + stage 08/09 incidents, control-pane
tooling, and the framing across LAB-MANUAL / docs / instructor docs. Validated green end-to-end.

## Problem

Stage 08 (service discovery) felt cosmetic: killing a node, the coordinator coped fine *without* the
registry, so attendees rightly asked "what is the registry even for?" Root cause, found by reading
the code:

1. **Two failure detectors.** The coordinator ran its own `health_check_loop` (polling every node's
   `/health` every 2s) *and* the registry detected death via heartbeat lapse. Redundant.
2. **`/kill` cheats.** `kvkill` → coordinator `/kill` marks the node dead *synchronously*, so the
   coordinator always knew about a death regardless of any detector.

So the registry was never on the critical path. Related dead code compounded the smell:
`HEARTBEAT_TIMEOUT` (unused in both coordinators), the coordinator's `/catchup` endpoint (never
called — the live catchup is the *follower's* `/catchup`, driven by `send_catchup_to_follower`), the
registry's `/alive` (no caller), a dead `/data-table` endpoint + its `node_data_cache`/`fetch_node_data`
(fed only by the loop), and `catchup.py` (imported nowhere — a duplicate of the coordinator's catchup).

## Decision

Adopt **Path B**: the registry becomes the *sole* failure detector; the coordinator owns recovery
*execution* only. Ownership split:

- **Detection → registry** (heartbeats → `prune_nodes` → **push** `/node-died` to the coordinator).
- **Recovery execution → coordinator** (`/spawn` respawns + `send_catchup_to_follower` catches up).
  Catchup deliberately stays in the coordinator: it needs the leader's snapshot, and a crashed node
  is never deregistered so a registry-triggered catchup wouldn't fire for a same-id respawn.

Concretely:

- **Removed `health_check_loop` from both coordinators.** Its only load-bearing job was marking nodes
  `alive` (nothing else set that status). Replaced with a **one-shot readiness probe**
  (`mark_nodes_ready` at startup, `mark_follower_ready` on `/spawn`) using the same `check_node_health`
  — reproduces the exact "alive iff `/health` 200" semantics but stops after startup, so it is not a
  continuous detector.
- **`/node-died` is now the coordinator's only way to learn of a crash** (push model), and it logs
  quorum impact (moved from the old loop).
- **Added a node-side `POST /crash`** (`os._exit`, skips graceful shutdown → no `/deregister`) to
  simulate an *unannounced* crash the coordinator is not told about. New `kvcrash <n>` control-pane
  helper hits the node directly (port `7001+n`); `kvkill` stays the *administrative* removal.

## The framing this enables (the pedagogical point)

Stages 05–07 never *detect* anything — the coordinator only knows about deaths **it performs itself**
via `/kill` (administrative removal). An unannounced **crash** (`kvcrash`) is invisible to it. So:

- 05–07: planned removal (the system is *told*). Quorum/consistency lessons unchanged.
- 08: the crash — coordinator goes blind → heartbeats/registry are introduced as the fix (detection).
- 09: auto-recovery builds on detection (registry triggers, coordinator respawns + catches up).

This maps to a real distinction (graceful decommission vs failure detection; `kubectl drain` vs a
kubelet going dark) and it makes the registry genuinely necessary rather than cosmetic. INC-08 was
rewritten from "kill via coordinator, check registry `/nodes`" to "crash out-of-band, assert the
**coordinator** discovers it via heartbeats" (red = still `alive`/blind; green = `dead`). INC-09 now
crashes rather than kills.

## Alternatives considered

- **Poll model** (coordinator polls registry `/alive` as source of truth) — conceptually purer
  ("coordinator asks the registry") and would have revived `/alive`, but a bigger change and it makes
  the stage-08 red state a totally dead cluster. Rejected in favor of the smaller push model; `/alive`
  deleted as dead code instead.
- **Delete the registry entirely** (coordinator does detection + recovery) — simplest, but drops a
  real distributed-systems concept from the capstone. Rejected.
- **Keep `catchup.py`** as a labeled reference — rejected; it duplicated the coordinator's catchup and
  invited "which one runs?" confusion.

## Files changed

- **05–07 coordinator** (`checkpoints/{05,06,07}` + `stages/05-replication`): removed
  `health_check_loop`/`fetch_node_data`/`node_data_cache`/`/data-table`/`previous_status`/
  `HEARTBEAT_TIMEOUT`; added `mark_nodes_ready`/`mark_follower_ready`; `/spawn` marks nodes ready.
- **08–10 coordinator** (`checkpoints/{08,09,10}` + `stages/08-discovery`): same loop→readiness swap;
  `/node-died` logs quorum; removed dead `/catchup` + `HEARTBEAT_TIMEOUT`; `/spawn` marks ready.
- **registry** (08–10 + stage): removed dead `/alive`.
- **node.py** (08–10 + gapped stage): added `/crash`.
- **incidents**: `incident_08_blind.py` rewritten (crash-gotcha); `incident_09_recovery.py` uses crash.
- **tools/kvplay.sh**: added `kvcrash`, relabeled `kvkill` as administrative.
- **deleted** `catchup.py` (all copies).
- **docs**: LAB-MANUAL stages 07 (foreshadow) / 08 (blind-coordinator gotcha) / 09 (kvcrash);
  `docs/stages.md` 08/09/10; `docs/diffs/07-to-08-discovery.md` + `diffs/README.md`; `instructor/SPEC.md`,
  `bugs-fixed.md`, `architecture.md` verb/framing fixes.

## Verification

`bash tools/validate_ladder.sh` inside the Docker container (foreground times out — run in background):
- `05 06 07` → **6/6** (confirms the readiness swap did not change 05–07 behavior at all).
- `08 09` → **4/4** (INC-08 green with heartbeats / red on the gap; INC-09 green with auto-spawn / red
  without). Full `02..09` ladder to be run as the final regression gate.

## Risks / notes

- **Startup ordering:** `mark_nodes_ready` runs synchronously before `uvicorn.run`, so `/status`
  reports followers `alive` as soon as the API serves (previously the loop flipped them a beat later).
- **Detection latency** for a crash is now heartbeat-timeout (5s) + prune interval (~1s); incidents
  wait accordingly (INC-08 12s, INC-09 18s).
- `previous_status` was removed as write-only-after-loop-removal; `/kill` and init no longer touch it.
- Left intentionally: the `_log_async_completion` cosmetic log; instructor-doc emoji (pre-existing
  style, out of scope).
