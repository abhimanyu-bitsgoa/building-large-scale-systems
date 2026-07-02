# `nload` restricted to the load-balancer stages + LAB-MANUAL stage-10 → `kvcrash`

**Date:** 2026-07-02
**Scope:** `build-kvstore/tools/kvplay.sh`, `build-kvstore/docs/stages.md`,
`build-kvstore/LAB-MANUAL.md`. Status: accepted.

## Problem (found live in a stage-01/02 dashboard)

On a node-tier stage without a load balancer (01 single-node, 02 vertical), the control-pane
`kvhelp` advertised `nload [reqs] [conc]` with the example *"on stage 02 with WORKERS=1 the GIL
chokes the tail"* — but running it failed hard:

```
nload 40 10
python: can't open file '/workspace/build-kvstore/kvstore/client.py': No such file or directory
```

Root cause: `nload` shells into `kvstore/` and runs `python client.py …`. **`client.py` only
ships in the load-balancer checkpoints (03/04)** — the 01/02 checkpoints contain only `node.py`.
So `nload` on 01/02 was dead: advertised in help, guaranteed to throw a traceback, and it would
do so in front of a room during a live demo. `LAB-MANUAL.md` already only used
`nwrite`/`nread`/`nhealth` on 01/02, confirming `nload` was never meant to be part of those stages.

## Decision

Treat `nload` as a **load-balancer-stages-only** helper (03/04):

1. **`kvplay.sh` — `kvhelp`:** removed the `nload` line (and its stage-02 example) from the
   no-`HAS_LB` node branch. 01/02 now list only `nwrite`/`nread`/`nhealth`.
2. **`kvplay.sh` — `nload()`:** inverted the guard. When `HAS_LB` is unset it now prints a friendly
   two-line message ("nload needs the load balancer — stages 03/04"; "on stage 02 the incident pane
   drives load") and `return 1`, instead of `cd`-ing into `kvstore/` and crashing on the missing
   `client.py`. The `HAS_LB` path (03/04) is unchanged.
3. **`docs/stages.md`:** the control-pane note listed `nload` under "01–04 (nodes)"; narrowed it to
   "03/04 also `nload`", with an explicit "01/02 are single-node — no `nload`" aside.

Rejected alternative: shipping `client.py` into the 01/02 checkpoints so `nload` works there. That
adds a multi-node load-balancer client to single-node stages it doesn't belong in, and the stage-02
GIL-choke story is already told cleanly by the incident pane. Removing the misleading affordance is
the simpler, correct fix and matches what LAB-MANUAL already taught.

## Also in this pass — LAB-MANUAL stage-10 `kvkill` → `kvcrash`

The [walkthrough reconciliation](2026-07-02_reconcile-walkthrough-to-current-ladder.md) flagged that
the stage-10 self-heal command disagreed across docs (`docs/stages.md` = `kvcrash`, `LAB-MANUAL` =
`kvkill`). Aligned `LAB-MANUAL.md`'s stage-10 finale to **`kvcrash 1`** so all three docs
(walkthrough, stages, lab manual) use the unannounced crash for the auto-respawn/self-heal beat —
consistent with the `kvkill` (planned, coordinator-told) vs `kvcrash` (unannounced, registry-detected)
distinction from the Path-B redesign.

## Risk / verification

- Tooling-only; no lab/service code, no assessment impact. `nload` on 03/04 is byte-for-byte the
  same command as before (only the surrounding guard moved).
- Verified live in the container: `bash -n kvplay.sh` clean; `kvhelp` on a no-`HAS_LB` node tier now
  shows no `nload`; `nload 40 10` there prints the guidance and exits 1 (no traceback).
