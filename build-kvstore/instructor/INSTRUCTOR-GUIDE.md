# Instructor Guide

This is the instructor companion to [`../LAB-MANUAL.md`](../LAB-MANUAL.md) — the attendee-facing
manual. The manual has the clean, copy-paste flow attendees follow; this guide adds everything they
*don't* see: pre-flight, pacing, what to say at each stage, the exercise answers, the honest caveats,
and deep troubleshooting.

> **This folder (`instructor/`) is excluded from the attendee template.** Keep answers, the design
> spec, and the bug log here so they never ship to attendees.

## Running this from the development monorepo vs. the attendee template

In the attendee/template repo, the workshop **is** the repository root — the manual's commands
(`docker compose up -d`, `make start`, …) work as written. In this development monorepo the workshop
lives under `build-kvstore/`, so inside the container you first `cd build-kvstore` before any `make`.
Everything else is identical.

---

## 1. Pre-flight (do this before the session — ideally the day before)

Build the container on good wifi so 60 people aren't pulling images on conference wifi at 09:00:

```
docker compose up -d
```

Run the regression suite to prove the whole ladder is intact on your machine. It boots every
checkpoint, asserts each incident is **GREEN on its stage** and **RED on the "before" state**, and
checks ports are free between cases. Expect **18/18 cases pass** (~3.5 min):

```
docker compose exec workshop bash -c 'cd build-kvstore && make validate'
```

Rehearse the human flow end-to-end at least once: `make start`, then walk `00 → 09` with
gap/up/incident/reset, and finish with the stage-10 demo. The suite proves correctness mechanically;
the rehearsal is about *pacing* and the couple of machine-dependent timing thresholds.

Re-run `make validate` after **any** edit to a coordinator/registry/node/incident or to
`tools/up.sh` / `tools/down.sh` — it is your correctness gate.

---

## 2. Pacing

There are 10 stages but only **4 require writing code** (03, 04, 05, 08) — spend the most time there.
Everything else is a quick run-and-observe or a one-flag config change.

### The 2-hour core path

| Role | Stages | Time |
|---|---|---|
| Quick framing (just show it) | `00`, `02` | ~2 min each |
| Fast config "aha" (run the incident, narrate) | `01`, `06`, `07` | ~5 min each |
| **Hands-on code (the heart)** | **`03`, `04`, `05`, `08`** | most of your time |
| Hands-on climax | `09` | self-healing — the last thing they *do* |
| Synthesis | `10` | 5-min speaker demo — no incident |

If you're even tighter, `08` (heartbeat) is the most cuttable code stage — demo it instead of having
the room write it. End the hands-on portion on stage 09 (the cluster healing itself) and close with
the stage-10 demo.

---

## 3. Per-stage teaching notes

For the exact commands, follow the manual. Below is what to emphasize and where attendees stumble.

- **00 single node** — Anchor: Redis is an in-memory keyspace. Keep it to 2 minutes; it's just "a
  dict behind HTTP."
- **01 vertical scaling** — The point is the *ceiling*. Show 4 workers (fast) vs `WORKERS=1` (slow).
  Anchor: Redis is single-threaded on purpose; you run more instances to use more cores.
- **02 horizontal scaling** — Two takeaways to say out loud: independent nodes have **separate**
  dicts (motivates replication), and round-robin is **blind to capacity** (motivates the load
  balancer). 
- **03 load balancing (code)** — They implement `AdaptiveStrategy.get_node`: return the lowest-load
  node. Have them compare adaptive vs. round-robin under load in the dashboard. Anchor:
  least-connections / power-of-two-choices (Nginx, HAProxy).
- **04 rate limiting (code)** — They implement the core of `FixedWindowStrategy.is_allowed`. The
  classic boundary-burst weakness of fixed windows is a good discussion point. Anchor: Redis
  `INCR`+`EXPIRE`.
- **05 replication (code)** — They implement `replicate_to_follower` (POST to `/replicate`). Stress
  that **reads are served by followers**, so a non-replicated write is invisible. Anchor: Redis
  primary–replica replication.
- **06 synchronous replication (config)** — `W = N`. "Write to everyone ⇒ read from anyone." Set up
  the pain: a write now needs every follower alive.
- **07 quorum & fault tolerance (config)** — Majority quorum `W = 2, R = 2`. This is the conceptual
  peak. Make the **CAP** moment explicit: after killing a follower, writes may be refused (503) while
  reads still succeed — the system gives up write-availability to keep consistency (the CP corner).
  The rule: **W + R > N**; tune `W` along the CAP spectrum.
- **08 service discovery (code)** — They implement `heartbeat_loop` (POST to the registry). Anchor:
  etcd / Consul / Redis Cluster gossip.
- **09 auto-recovery (config)** — Enable auto-spawn; the coordinator catches the new node up from the
  leader's snapshot. This is *follower* recovery, **not** leader failover (that's Sentinel/Raft — out
  of scope). This is the emotional high note: the cluster heals itself.
- **10 full system (demo)** — Run `make lab STAGE=10` and drive it: trace one request through the
  whole stack (gateway → coordinator → leader → followers), flood the edge to show 429s, then kill a
  follower and watch it self-heal while reads stay fresh. Close with: "From a `dict` behind HTTP, you
  built a rate-limited, replicated, quorum-consistent, self-healing distributed KV store."

---

## 4. Honest caveats — say these out loud

- **Read selection is deterministic on purpose.** The coordinator picks read followers by port (the
  highest-R ports), not by "fastest replica." This is so stale-read demos are **reproducible** every
  run. In a real Dynamo-style system you'd read from the R fastest replicas and reconcile by version;
  we pick deterministically so staleness is observable. (Don't change this logic — it's a teaching
  device.)
- **The gateway doesn't load-balance.** It forwards to a *single* coordinator, so there's nothing to
  balance across — `load_balancer.py` ships alongside the gateway but the gateway doesn't use it. The load-balancing
  *responsibility* moved **server-side** into the coordinator's quorum routing. In production you'd
  run several coordinators behind the gateway. The point of stage 10 is the **synthesis**, not new
  code.

---

## 5. Exercise answers (code stages 03, 04, 05, 08)

Each gap is a single core line; the surrounding boilerplate is pre-filled. The **authoritative worked
solution** for any stage is its checkpoint — load it with:

```
make reset STAGE=NN
```

This overwrites the working copy with the correct, passing version (useful for an attendee who's
stuck, or to demo the answer). Brief descriptions:

- **03 — `AdaptiveStrategy.get_node`** (`load_balancer.py`): return the node with the lowest load
  score, e.g. `min(nodes, key=<load score>)`.
- **04 — `FixedWindowStrategy.is_allowed`** (`rate_limiter.py`): if the window has rolled over, reset
  the counter and window start; allow while the count is under the limit (incrementing it), otherwise
  reject.
- **05 — `replicate_to_follower`** (`node.py`): `POST` the `{key, value, version}` payload to the
  follower's `/replicate` endpoint and return success on `200`.
- **08 — `heartbeat_loop`** (`node.py`): on each interval, `POST` the node's identity
  (`node_id`, `port`, `url`, `role`) to the registry's `/heartbeat` endpoint.

After loading a code stage with `make gap STAGE=NN`, the gap raises a clear error until filled. Note
the code stages seed **non-destructively** where the dashboard is concerned — see troubleshooting.

---

## 6. Troubleshooting (the deep ones)

- **A stage won't start / "address already in use."** A leftover process from a previous stage holds
  the port. Always `make down` (or `make lab-down`) before switching stages. To confirm the cluster
  ports are free, check that this prints `0`:

  ```
  ss -ltn | grep -cE ':7000|:9000'
  ```

- **Reads return stale/garbage for no reason.** Orphaned followers from a prior run on `7002–7004`.
  `make down`, then re-launch.

- **Zombie processes pile up after many up/down cycles.** The container runs with `init: true`
  (docker-init/tini as PID 1) so orphaned subprocesses are reaped. If you ever disabled that, repeated
  cycles can exhaust the process table — recreate the container with `docker compose up -d`.

- **tmux shows `_` instead of `—`/emoji.** The dashboard sets UTF-8 (`LANG`/`LC_ALL` and `tmux -u`).
  If you launched tmux a different way, start it via `make lab` instead.

- **Stuck inside tmux.** Detach with `Ctrl-b` then `d`; re-attach with `tmux attach -t kvlab`; kill
  everything with `make lab-down`.

- **A code stage seems to "wipe" my work.** `make gap` / `make reset` overwrite `kvstore/`. The
  dashboard (`make lab`) preserves an existing `kvstore/` for code stages so it won't clobber a
  solution; `gap`/`reset` are the explicit "reset my working copy" commands.

---

## 7. Deeper references (instructor / author only)

- [`SPEC.md`](SPEC.md) — the full design and build spec (source of truth); ladder, ports, the quorum
  invariant, the validation invariant.
- [`HANDOFF.md`](HANDOFF.md) — continuation notes for anyone extending the workshop.
- [`bugs-fixed.md`](bugs-fixed.md) — the running bug log from building/verifying the labs.
- `../../WORKSHOP-WALKTHROUGH.md` — the exhaustive, narrated walkthrough (the comprehensive working
  artifact this guide is distilled from).
- `../../wiki/decisions/` — the decision log: *why* the workshop is shaped the way it is.
