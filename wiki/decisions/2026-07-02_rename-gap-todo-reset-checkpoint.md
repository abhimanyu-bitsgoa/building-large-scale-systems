# Rename Makefile verbs: `gap` → `todo`, `reset` → `checkpoint`

**Date:** 2026-07-02
**Scope:** `build-kvstore/` only (the EuroPython lab). Status: accepted.

## What changed

Two workshop `make` verbs were renamed for clarity of the learner-facing mental model:

| Old | New | What it does (unchanged) |
| --- | --- | --- |
| `make gap STAGE=NN`   | `make todo STAGE=NN`       | Load the exercise starting point (`stages/NN-*` → `kvstore/`) with one core function left blank. |
| `make reset STAGE=NN` | `make checkpoint STAGE=NN` | Restore `kvstore/` to a known-good checkpoint (`checkpoints/NN-*`) — the rescue/panic button. |

No behavior changed — only the target names, their `.PHONY` entry, and the two echo strings
in `build-kvstore/Makefile`. All doc/script references to the two commands were updated to match.

## Why

- **`gap`** was vague. What the verb loads is an exercise with a `TODO`/`NotImplementedError`
  to fill in; `todo` names that directly and matches how the stages are framed to attendees.
- **`reset`** collided conceptually with `git reset`, `X-RateLimit-Reset`, and the "reset the
  window" rate-limiter language already in the codebase. The verb restores a *checkpoint*, so
  `checkpoint` is the honest name and reuses vocabulary already central to the lab
  (`checkpoints/` dir, "known-good checkpoint", the rescue button).

Requested by the author (speaker) ahead of the EuroPython tutorial.

## How it was done

1. Edited `build-kvstore/Makefile`: `.PHONY` list, `help` text, target labels `gap:`→`todo:`
   and `reset:`→`checkpoint:`, plus the two echoed status strings.
2. Bulk exact-phrase replacement of `make gap`→`make todo` and `make reset`→`make checkpoint`
   across all `*.md` and `*.sh` under `build-kvstore/` (LAB-MANUAL, docs/, instructor/,
   per-stage/checkpoint READMEs, tmux tooling). These exact phrases only ever referred to the
   commands, so the replacement is safe.
3. Hand-updated the four **shorthand verb-lists** that name the bare verbs without a `make `
   prefix (`start|gap|up|...`, `gap/up/incident/reset`, `` `gap`/`reset` ``) in
   `instructor/{HANDOFF,SPEC,INSTRUCTOR-GUIDE}.md`.

## What was deliberately NOT changed (scope discipline)

Per the "no gratuitous refactoring" principle, conceptual uses of the *words* were left alone:

- The word **"gap"** as jargon for the code blank ("implement the gap", "the gap at stage 05",
  "code-gap stages", "gapped starting point") — still meaningful, and pervasive in author-only
  comments (`tools/validate_ladder.sh`, `SPEC.md` "Code gap" column).
- All uses of **"reset"** unrelated to the command: `git reset --hard`, the rate limiter's
  "reset the window", `metadata['reset']`, `X-RateLimit-Reset`.

This leaves a mild vocabulary seam (e.g. `tools/tmux_lab.sh`: "`make todo` ... then implement
the gap"). It reads fine and renaming the *concept* everywhere is a broader change the request
did not ask for — flagged to the author as an optional follow-up rather than done silently.

## Risk / verification

- **No functional risk.** No script invokes these targets internally — the tmux/up tooling and
  `validate_ladder.sh` only use `make up`/`make incident`/`make status` or operate on the
  `stages/`/`checkpoints/` directories directly. The rename is Makefile-labels + prose only.
- Verified with `make -n todo STAGE=05` and `make -n checkpoint STAGE=01` (both resolve to the
  correct `rm -rf kvstore && cp -r ...` recipes); confirmed the old `gap`/`reset` targets now
  error with "No rule to make target". `make help` renders the new names.
- The KV-store assessment and `validate_ladder` exercise cluster code, not make target names,
  so they are unaffected by this change.
