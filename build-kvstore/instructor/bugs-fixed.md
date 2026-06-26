# Bugs fixed while building `build-kvstore/`

A running log of every bug corrected while deriving the checkpoints. Most of these are
**latent bugs in the original `labs/` code** that only surfaced under realistic (manual,
multi-second) timing. Each carries into the checkpoints as they are derived. Newest first.

> Severity: 🔴 breaks a workshop demo · 🟡 latent/no current impact · ⚪ cleanup.

---

## BUG-1 🔴 — Killed nodes resurrect themselves
- **Where:** `coordinator.py` `/kill` (KV coordinator → checkpoints 08/09/10). Root cause lives
  in the KV `node.py` `graceful_shutdown` SIGTERM handler.
- **Symptom:** `POST /kill/{id}` returns `stopped`, but a few seconds later the node is `alive`
  again. The coordinator's 2s health-check loop re-marks it alive.
- **Root cause:** `/kill` used `process.terminate()` (SIGTERM). The node's `graceful_shutdown`
  handler intercepts SIGTERM and the process survives; the health-check then resurrects it. The
  existing `assessment.py` only passed because its checks fire within the ~1s race window before
  the re-flip.
- **Fix:** `/kill` now uses `process.kill()` (SIGKILL). Killing a node simulates a **crash**, so
  it really dies; the registry then detects it via missed heartbeats (the point of stage 08). The
  replication coordinator (05/06/07) got the same `kill()` change for consistency/crash-semantics
  (its node had no shutdown handler, so it wasn't strictly broken there).
- **Verified:** checkpoint 08 keeps a killed follower dead (writes survive at W=2); checkpoint 07
  kills `floor(N/2)` and survives, then loses quorum (503) on the next kill.

## BUG-2 🔴 — Auto-respawned followers come up empty (no catchup)
- **Where:** `registry.py` `receive_heartbeat` + `coordinator.py` `/spawn` (checkpoints 08/09/10).
- **Symptom:** kill a follower with auto-spawn on → it respawns, but the revived node has **no
  data** (a read straight to it 404s), so the cluster runs degraded.
- **Root cause:** catchup was triggered by the registry **only for a brand-new `node_id`**. A
  SIGKILL'd node is never deregistered, so it stays in the registry marked `dead`; its same-id
  respawn is not "new" → catchup never fires.
- **Fix:** catchup moved to the **coordinator's `/spawn`** (it owns the leader and orchestrates
  membership), covering manual *and* auto respawn. The registry is now pure discovery; its
  orphaned `trigger_catchup` function was removed (⚪ dead-code cleanup).
- **Verified:** checkpoint 09 — kill → auto-respawn → the revived follower has the key via catchup.

## BUG-4 🔴 — `make down` left orphaned uvicorn workers holding the ports
- **Where:** `tools/down.sh` (cleanup for the `--workers` stages 01/02/03).
- **Symptom:** after a stage that uses `--workers > 1`, the ports (e.g. 5001) stayed occupied;
  the next `make up` couldn't bind and the *old* node kept serving — making later incidents fail
  for no apparent reason.
- **Root cause:** uvicorn spawns worker processes whose command line is just `python` (not
  `python node.py`), so `pkill -f node.py` never matched them; when the parent was killed they
  were orphaned and kept listening.
- **Fix:** `down.sh` now also kills whatever process is listening on each workshop port
  (via `ss -ltnp`), catching orphaned workers.
- **Verified:** after a `--workers` stage, `make down` frees all workshop ports.

## BUG-3 🟡 — `assessment.py reset_cluster()` reads a non-existent status key
- **Where:** `assessment.py` `reset_cluster()` (checkpoint 10).
- **Symptom:** none today — `reset_cluster` silently never respawns anything between scenarios.
- **Root cause:** it reads `status.get("nodes", [])`, but the coordinator `/status` returns
  `followers`, not `nodes` → always an empty list → the respawn loop is dead code. Harmless only
  because the one node-killing scenario (INC-4) runs **last**; it would bite if scenarios were
  reordered or one added before INC-4.
- **Fix:** read `status.get("followers", [])`.
- **Verified:** checkpoint 10 still scores 100/100 (behaviour-neutral for the current scenario
  order, since nothing is dead before INC-4).
