# Fix WORKSHOP-WALKTHROUGH.md: load each stage into `kvstore/` before `make up`

- **Date:** 2026-06-24
- **Status:** accepted
- **Change / commit(s):** branch `europython-lab-design` (PR into `europython-branch` pending)

## Context

The walkthrough's per-stage instructions went straight to `make up STAGE=NN` for the
config/observe stages (01, 02, 06, 07, 09, 10) without first loading that stage's code into the
working directory `kvstore/`. But `make up STAGE=NN` runs *that stage's* launch command against
**whatever is currently in `kvstore/`**. An attendee who ran `make up STAGE=01` while `kvstore/`
still held the stage-00 node hit:

```
node.py: error: unrecognized arguments: --load-factor 30 --workers 4
```

— because the bare stage-00 node has only `--port`/`--id`, while the stage-01 node adds
`--load-factor`/`--workers`. The code stages (03/04/05/08) were already correct because they
told the attendee to run `make gap STAGE=NN` first (which loads that stage's code).

## Decision

Document the rule explicitly and uniformly: **every stage starts by loading its code into
`kvstore/` before `make up`** — `make gap STAGE=NN` for the 4 code stages, `make reset STAGE=NN`
for the rest. Updated §1 (the core loop), the §6 intro, and the per-stage command blocks for
01, 02, 06, 07, 09, and the §7 capstone (10).

## Alternatives considered

- **Leave it; rely on attendees inferring `reset`/`gap`.** Rejected — the natural
  `make up STAGE=NN` silently runs against stale code and fails confusingly.
- **Change the tooling so `make up` auto-loads the checkpoint.** Rejected — that would clobber an
  attendee's in-progress code on the code stages (their `make gap` work) and alters the author's
  design. Docs, not tooling, are the right fix.

## Side effects & risks

- `build-kvstore/README.md`'s "How a stage works" carries the same idealization (shows
  `make up STAGE=03` without a preceding `make gap`). Left to the author; noted here.
- For stages that share code (05/06/07), `make reset STAGE=NN` is technically redundant between
  them but harmless, and keeping the load step uniform is less error-prone than special-casing.

## Verification

In-container on 2026-06-24: `make reset STAGE=01 && make up STAGE=01` boots cleanly
("Application startup complete"), confirming the load-before-up flow resolves the reported
error. (Operational aside, re-learned here: in-container checks must avoid the SPEC §12 `pkill`
foot-gun — a command whose text contains a literal `node.py`/`coordinator.py` is self-matched
and SIGTERM'd by `make down`'s `pkill -f`, which looks like a hang/`exit 143`.)

## References

- [`WORKSHOP-WALKTHROUGH.md`](../../WORKSHOP-WALKTHROUGH.md) (§1, §6, §7)
- [walkthrough doc](2026-06-23_workshop-walkthrough-doc.md) · [build SPEC §12](../../build-kvstore/SPEC.md)
