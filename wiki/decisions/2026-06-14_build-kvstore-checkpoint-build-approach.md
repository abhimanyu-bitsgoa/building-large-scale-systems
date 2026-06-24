# How the `build-kvstore/` checkpoint ladder was built (flag-gating + derive-by-subtraction)

**Date:** 2026-06-14
**Status:** accepted — complete: 11 checkpoints, 10 incidents, 4 code gaps, Makefile toolchain, all verified
**Related:** [restructure decision](2026-06-14_build-kvstore-incremental-restructure.md) ·
`build-kvstore/SPEC.md` · `build-kvstore/docs/bugs-fixed.md`

## Context

The restructure decision established *what* `build-kvstore/` is (11 stage checkpoints derived
by subtraction). This file records *how* the ladder was actually built and the cross-cutting
rule that decided, for every pair of consecutive checkpoints, whether the difference is **code**
or **config** — needed to avoid both excessive surgery and excessive duplication, and to honour
the user's stated priorities (reuse the lab code, prefer simpler/less code).

## Decision: the "flag-gating" rule

Two kinds of "absent feature", handled differently:

- **Genuine runtime knobs** → leave the code in, toggle via `up.sh`. These are real, documented
  config switches, so consecutive checkpoints can **share code** and differ only by flags:
  - `--auto-spawn` ⇒ `08` (discovery, off) ≡ `09` (auto-recovery, on) — same code.
  - `W`/`R` quorum ⇒ `05` (W=1,R=1, stale) ≡ `06` ≡ `07` (W=2,R=2) — same code.
  - `--rate-limit` ⇒ the scalability node carries the limiter flag-gated.
- **Structural features** → add/remove the code at a chapter boundary, because it lives in its
  own file/block: the **gateway** (10), the **registry + heartbeats + catchup** (08), **replication**
  (05), and the node's **rate-limit middleware** (04).

This makes the **code-distinct** checkpoints just: `00`, `01`(=02=03 node), `04`, `05`(=06=07),
`08`(=09), `10`. The rest differ by config or by which support files are present. Duplicate
checkpoint dirs are kept anyway so `make reset STAGE=NN` maps uniformly to `checkpoints/NN`.

## How each chapter was derived (by subtraction / reuse)

- **KV chapter `10→09→08`:** copied the full system to `10` (gateway imports made local;
  `load_balancer.py`/`rate_limiter.py` brought in). `09` = `10` minus the gateway + capstone.
  `08` = copy of `09` run without `--auto-spawn`.
- **Replication chapter `07/06/05`:** reused the **replication lab verbatim** (`coordinator.py`,
  `node.py`, `client.py`) with exactly two edits — `BASE_PORT 6000→7000` (port consistency) and
  `/kill`→`process.kill()` (crash semantics). The three stages share code; `up.sh` runs `05` at
  `W=1,R=1` (stale reads) and `06`/`07` at `W=2,R=2`. *Chosen over surgically trimming the KV
  coordinator* because it maximises reuse of code the user knows and needs no new logic.
- **Scalability chapter `04→00`:** `04` = full scalability lab set. `01/02/03` share one **trimmed**
  node (rate-limit code removed; load-sim + `--workers` kept). `00` is a fresh ~45-line **bare**
  node (just a dict + `/data` + `/health`) to make the opening "a KV store is a dict behind HTTP"
  land. `client.py`+`load_balancer.py` appear at `02`; `rate_limiter.py` returns at `04` (the
  limiter "graduates" to the gateway at `10`).

## Alternatives considered

- **Full line-by-line evolution of one `node.py`/`coordinator.py` across all 11 stages** — smoothest
  "watch it grow" diffs, but heavy authoring and a second structural rewrite. Deferred; the user
  said code stages can change later.
- **Flag-gate everything (no trims at all)** — even less code, but stage `00` would be the full
  258-line scalability node, undermining the opening hook. Rejected only for the bare node.

## Consequences / risks

- Two **chapter boundaries** (`04→05`, `07→08`) have chunky diffs; each gets a `docs/diffs/`
  explainer so the jump reads as "new chapter", not "rewrite".
- Intentional duplication across config-only checkpoints (accepted for the uniform reset mechanism).
- Verification surfaced **three latent bugs in the original labs** (see `docs/bugs-fixed.md`):
  killed nodes resurrecting, empty auto-respawns, and a dead `reset_cluster` key — all fixed and
  re-verified.

## Verification matrix (all on clean ports, inside the container)

| cp | verified |
| -- | -------- |
| 00 | bare dict RW round-trip |
| 01 | load-sim latency header; `--workers` |
| 02/03 | 3 nodes + client; **adaptive P95 < round-robin P95** |
| 04 | flood → first N succeed, rest **429** |
| 05 | write then immediate read **stale/404**, fresh after ~5s |
| 06 | immediate read **fresh** (W+R>N) |
| 07 | kill `floor(N/2)` survives; one more → **quorum loss 503** |
| 08 | killed follower **stays dead**, writes survive at W=2 |
| 09 | kill → **auto-respawn + catchup** (revived node has the data) |
| 10 | `assessment.py` = **100/100** (re-verified after every coordinator/registry edit) |

## Testing-harness lesson (recorded so it isn't rediscovered)

`pkill -f coordinator.py` matches the *test script itself* (its body contains `python
coordinator.py …`), which killed tests early and left polluted node processes on ports 7002–7004
serving stale data. Cleanup must run as a **separate** shell call using only bracketed patterns
(`[c]oordinator.py`, `[n]ode.py`, …) and no literal command names. See `SPEC.md` §12.
