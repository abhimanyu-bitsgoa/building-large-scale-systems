# 2026-07-01 — Finalization pass: reconcile drifted copies + remove dead code

**Status:** accepted
**Scope:** consistency/cleanup across the whole `build-kvstore` ladder while finalizing the labs.
No behavior changes; validated 16/16.

## Context

A full read-through during finalization surfaced several places where checkpoint copies that are
*supposed* to be the same code had drifted, plus some dead weight. In a workshop where the
stage-to-stage diff is itself a teaching artifact, this drift produces noisy diffs and doubles
maintenance. Findings (from the review report):

- **The two coordinator families diverged.** `05-07/coordinator.py` (797 lines) and
  `08-10/coordinator.py` (675) implemented the *same* core in different styles. Worst offenders:
  `/write` (deeply nested vs guard-clause) and `/read` (**parallel** `ThreadPoolExecutor` in 05-07
  vs **sequential** in 08-10). This predates the Path B work; it was independent refactoring drift.
- **"Same file" claims that weren't true.** `rate_limiter.py` differed between 04 (224 lines) and 10
  (238) despite the gateway docstring calling it "the same module students wrote"; the 10 copy also
  carried a stale `TODO: [STUDENT EXERCISE]` block in a *solved* checkpoint. `load_balancer.py` had a
  readability cleanup at 03 (`return min(nodes, key=...)`) that never propagated to 04/10 (still the
  verbose `sorted(...)[0]`).
- **Dead weight.** The cluster-tier `client.py` (05-10, 226/266 lines × 6 copies) is not referenced
  by `LAB-MANUAL`, `up.sh`, `tmux_lab.sh`, `kvplay.sh`, or any incident — cluster interaction is all
  `kvplay`/curl. Only the 03/04 `client.py` is live (the `nload` load generator).
- **Minor.** `02-vertical/node.py` docstring said "stages 01-03" but stage 01 uses the separate
  51-line minimal node.

## Decision & changes

**#2 — reconcile the coordinators (the high-value one).** Standardized `/write` and `/read` on the
cleaner 08-10 style and made them **byte-identical** across both families (extracted the span from
08-10, stripped trailing whitespace, wrote the same block into both). Picked **sequential** `/read`
(parallelism isn't the lesson; clearer to read) and dropped the now-unused
`from concurrent.futures import ThreadPoolExecutor, as_completed` from the 05-07 coordinator. Result:
05-07 coordinator 797 → 716 lines; the inter-family gap shrank from 122 to 41 lines, and that
remaining 41 lines is exactly the *legitimate* discovery delta (`send_catchup_to_follower`,
`/node-died`, registry wiring, `initialize_cluster`, `SpawnRequest`/`NodeRequest`, catchup in
`/spawn`). So the 07→08 diff now shows discovery additions, not a gratuitous `/write`/`/read` rewrite.

  *Left as legitimate/benign deltas (documented, not "fixed"):* `/status` is richer at 05-07
  (`is_sync`/`is_read` flags — arguably useful for the sync-vs-async teaching point); `/spawn`
  differs because 08+ adds catchup; `initialize_cluster` differs because 08+ wires the registry.
  Forcing these identical would either lose teaching signal or add risk for no diff-cleanliness gain.

**#3 — kill the "same file" drift.** Copied the clean 04 `rate_limiter.py` over the 10 copy (now
identical; stale TODO gone), and propagated the clean 03 `load_balancer.py` (the `min()` version) to
04, `stages/04`, and 10. All solved copies now match.

**#4 — deleted the unused cluster-tier `client.py`** from checkpoints 05-10 and `stages/05`,
`stages/08` (8 files). Kept 03/04 `client.py` (used by `nload`).

**#5 — polish + dead-import sweep.** Fixed the `02-vertical/node.py` docstring to "stages 02-03"
(propagated to its identical 03 copies). Ran a stdlib AST dead-import scan across every lab `.py` and
removed the confirmed-unused imports: `Tuple` from the 05-07 coordinator (leftover from the /read
reconciliation), `HTTPException` + `datetime` from the registry (08-10), `sys` from the 03/04 client,
and `Response` from the 04 node. **Kept** the one intentional "unused" import — `requests` in
`stages/05-replication/node.py` — because the gapped file imports it for the student's
`replicate_to_follower` solution. The scan covers annotation usage, so every removal is NameError-safe.

## Alternatives considered

- **Unify into a single coordinator file across 05-10** (discovery gated by `--registry`). Elegant,
  but a much larger architectural change that would also rewrite the checkpoint model and the
  diffs narrative. Rejected as over-scope for a finalization pass; the surgical `/write`+`/read`
  reconciliation gets the bulk of the value at a fraction of the risk.
- **Keep parallel `/read` at 05-07.** Rejected — the divergence was the concrete complaint, and
  parallelism isn't part of any lesson.
- **Standardize `/status` on the leaner 08-10 shape.** Rejected — the richer 05-07 `/status` exposes
  the sync/async split that stage 05-07 is literally about.

## Verification

`bash tools/validate_ladder.sh` (in-container, background) → **16/16**, ladder invariant holds. Each
reconciled file compiled; the `/write`+`/read` span asserted byte-identical across families.

## Risks / notes

- The reconciliation used an anchor-based script (scratchpad) rather than a giant exact-match edit,
  to avoid whitespace-mismatch errors on a ~230-line block; verified by post-hoc byte-equality check.
- No linter is configured in the container, so the dead-import sweep used a self-contained stdlib
  `ast` scan (scratchpad) rather than `ruff`/`pyflakes` (avoids depending on container network
  access). Re-running it after the pass reports clean (only the intentional `stages/05` `requests`).
- `client.py` deletion is safe only because build-kvstore drives the cluster via `kvplay`/curl; if a
  future change wants an interactive cluster client, resurrect from git history rather than shipping
  an unreferenced copy per stage.
