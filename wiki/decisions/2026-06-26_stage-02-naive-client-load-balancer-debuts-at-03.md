# 2026-06-26 — Move the load balancer's debut from stage 02 to stage 03

## Context

In the scalability ladder, `client.py` **and** `load_balancer.py` both first appeared at
**stage 02** — fully implemented, every strategy included. But:

- Stage 02's incident never touches them: `incident_02` does its own inline round-robin over the
  three node URLs and only checks that ≥90% are reachable (the lesson is "more nodes = capacity +
  no SPOF").
- `checkpoints/02-horizontal` and `checkpoints/03-load-balancing` were **byte-identical**. So the
  02→03 step added *no visible artifact*; `make gap STAGE=03` merely gutted one method body, which
  reads as "it wiped my work for nothing."
- `make lab STAGE=02`'s `nload` helper let you run `nload adaptive` — **spoiling stage 03's
  punchline** before it was earned.

This broke the workshop's core "one earned step at a time" promise exactly at the load-balancing
stage. (See the prior discussion in the talk-readiness work and
[[2026-06-26_load-balancing-client-vs-server-reference-doc]].)

## Decision

Move the load balancer's **debut from 02 to 03**, so each transition adds something real:

| Transition | Before | After |
| --- | --- | --- |
| 01→02 | `client.py` + `load_balancer.py` appear | **`client.py` only** — naive inline round-robin (`node = nodes[i % len(nodes)]`), no strategy abstraction |
| 02→03 | identical checkpoints; gap guts a method | **`load_balancer.py` appears** (strategy pattern); `client.py` rewired to route via `LoadBalancer --strategy`; gap is still `AdaptiveStrategy.get_node` |

Stage 02 now teaches "more nodes, routed **dumbly**": with one weak node (1 worker) and two strong
(4 workers), naive round-robin sends a third of traffic to the slow node and drags the tail — the
*pain* that motivates stage 03. Stage 03 *introduces* the load balancer and you watch
`nload adaptive` beat `nload round_robin`.

## What changed

- **`checkpoints/02-horizontal/`**: removed `load_balancer.py`; replaced `client.py` with a naive
  version — inline round-robin counter, no `LoadBalancer` import, no `--strategy` arg. Keeps the
  metrics/`print_stats` so the per-node and global p95 are still visible (that's the observable).
- **`checkpoints/03-load-balancing/`** and **`stages/03-load-balancing/`**: unchanged — they
  already carry the full `load_balancer.py` and the `AdaptiveStrategy` gap. The change is purely
  that 02 no longer ships them, so 03 is where they *appear*.
- **`tools/up.sh`**: split the `02|03` case so each prints an honest message (02 = "naive
  round-robin … no load balancer yet"; 03 = "client.py --strategy (load_balancer.py)").
- **`tools/kvplay.sh`** + **`tools/tmux_lab.sh`**: `nload` is now tier-aware via a `HAS_LB` env var
  that `tmux_lab.sh` sets for the LB stages (03/04). With `HAS_LB`, `nload [strategy] [reqs] [conc]`;
  without it (stage 02), `nload [reqs] [conc]` runs the naive client and `kvhelp` shows the naive
  form. Stage 02's `client.py` genuinely has no `--strategy`, so this keeps the CLI honest.
- **Docs**: `docs/diffs/README.md` (through-line + 01→02 and 02→03 rewritten), `docs/stages.md`
  (§02/§03), `SPEC.md` (stage table), `README.md` (`make lab STAGE=02` example),
  `WORKSHOP-WALKTHROUGH.md` (cheat-sheet `nload` rows, §02 one-window demo, §8.6 demo list).

## Alternatives considered

- **Keep one shared `client.py`; ship a round-robin-only `load_balancer.py` at 02 that grows
  `AdaptiveStrategy` at 03.** Preserves the "client.py is identical everywhere" convenience, but
  keeps `load_balancer.py` present at 02 — exactly the "it already exists, nothing visibly changed"
  smell we set out to remove. Rejected.
- **Stage 02 `client.py` accepts `--strategy` but ignores it.** Avoids the `nload` branch, but is
  dishonest (an accepted-and-ignored flag) and reintroduces the abstraction at the CLI. Rejected in
  favor of the `HAS_LB` switch.

## Risk + how it was retired

The hazard is breaking the ladder invariant (gap RED / checkpoint GREEN) or the `nload` play
surface. Checked:

- `make validate` → **20/20**. INC-02 green now seeds the naive `02-horizontal` (no
  `load_balancer.py`) and still passes (it's reachability-based, independent of the client). INC-03
  still discriminates (gap RED, checkpoint GREEN).
- `incident_02` does not import `client.py`, so the simplified client cannot affect grading.

## Trade-off accepted

`client.py` now **differs between 02 and 03** (inline round-robin vs `LoadBalancer`-based), breaking
the previous "consistent client across the scalability stages" property. This is deliberate: the
divergence *is* the stage-03 lesson, it spans a single transition, and `docs/diffs` documents it.

## Files touched
- Edited: `build-kvstore/checkpoints/02-horizontal/client.py` (rewritten naive),
  `build-kvstore/tools/up.sh`, `build-kvstore/tools/kvplay.sh`, `build-kvstore/tools/tmux_lab.sh`,
  `build-kvstore/docs/diffs/README.md`, `build-kvstore/docs/stages.md`, `build-kvstore/SPEC.md`,
  `build-kvstore/README.md`, `WORKSHOP-WALKTHROUGH.md`, `wiki/decisions/INDEX.md`.
- Removed: `build-kvstore/checkpoints/02-horizontal/load_balancer.py`.
