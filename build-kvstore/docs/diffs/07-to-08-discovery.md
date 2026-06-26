# Chapter 2 — 07 → 08: the cluster learns who's alive

The second big jump. After Chapter 1 you have a replicated cluster (05) with a tuned quorum (06)
that makes a deliberate CAP choice when nodes die (07). But notice the gap in that story: the
cluster *reacts* to death (a write quorum can't be met → `503`), yet nothing **detects** death as
a first-class fact. Through stage 07 the coordinator only *infers* liveness by polling each node's
health endpoint — a guess, made from the outside.

Stage 08 fixes the foundation: nodes **announce** they're alive, continuously, to a dedicated
discovery service. Death becomes the *absence of that signal*. This matters because **you cannot
recover a node until you can reliably detect its death** — so discovery (08) is the prerequisite
for auto-recovery (09). Like Chapter 1, the file list looks like a lot; the idea is small.

## What's new: `registry.py` (the discovery service)

A standalone service whose entire job is to track membership:

- **`POST /heartbeat`** — every node calls this on a timer. The registry records "node X was last
  seen at time T."
- **`prune_nodes`** — a background sweep that marks a node **dead** once its last heartbeat is older
  than the timeout. This is the core inversion: *silence*, not a failed poll, declares death.
- **`GET /nodes` / `GET /alive`** — the membership view everyone else reads. (Stage 08's incident
  asks the registry whether a killed follower shows up as `dead` — that's `/nodes`.)
- **`auto_spawn_node`** — present here but dormant; it's switched on at stage 09 with `--auto-spawn`.

## What's new: `catchup.py` (and how a revived node gets its data)

A node that (re)joins empty is useless. `catchup.py` is the helper that syncs a follower from the
leader's **snapshot** so it rejoins with the full dataset. It exists at stage 08 but does its real
work at stage 09, when respawned followers need to be caught up. (This is *follower* recovery — the
analog of Redis `PSYNC` — not leader failover, which is out of scope.)

## What changes: `node.py` starts talking

The node gains the other half of the heartbeat conversation:

| added at stage 08 | purpose |
|---|---|
| **`heartbeat_loop`** + a background thread | continuously POST "I'm alive" to the registry |
| **`REGISTRY_URL`** + `--registry` flag | where to send heartbeats |
| **`GET /snapshot`** | hand the leader's full dataset to a catching-up follower |
| **`POST /catchup`** | receive that dataset when reviving |
| **graceful deregister** (on SIGTERM) | a clean shutdown tells the registry, so it isn't mistaken for a crash |

## What changes: `coordinator.py` reacts to membership

The coordinator becomes registry-aware:

- **`send_catchup_to_follower`** and **`POST /catchup`** — orchestrate syncing a (re)joined follower
  from the leader.
- **`POST /node-died`** — a hook for reacting to a death the registry reports.
- **`initialize_cluster`** + `SpawnRequest`/`NodeRequest` — spawn the leader and followers wired to
  the registry, and accept structured spawn/kill requests (used by auto-spawn at stage 09).

> Design note: catchup is driven by the **coordinator's `/spawn`**, not by the registry, because a
> SIGKILL'd node is never deregistered — it lingers as `dead` and its same-id respawn isn't "new," so
> a registry-triggered catchup would never fire. The coordinator owns the leader and orchestrates
> membership, so it's the right place.

## The one line you write

All of that infrastructure serves a single idea: **a node stays in the cluster by repeatedly
telling the registry it's alive.** The gap at stage 08 is exactly that — the POST inside
`heartbeat_loop`. The loop, the pacing, and the error handling are provided; you write the
heartbeat itself. Before: the registry never sees the node, so a kill goes unnoticed. After: the
killed follower shows up as `dead` within the timeout — detection works, and stage 09 can build
recovery on top of it.

## Why this is the last foundational chapter

With discovery in place the system can finally close its own loop: detect a failure (08) → respawn
and catch up the replacement (09) → and only then dress it for production with an edge gateway and
the whole-system demo (10). Everything after this is either a config flip you observe or the
synthesis demo — the hard architecture is done.

← Previous chapter: **[04 → 05: from one node to a replicated cluster](04-to-05-replication.md)**.
