# Making the attendee template repo

This documents how to extract the attendee-facing workshop from this development monorepo into a
clean, standalone **template repository** for EuroPython attendees.

> This file lives in `instructor/`, which is **excluded** from the template — it never ships to
> attendees.

## What the template is

The template repo's root **is** the contents of `build-kvstore/` — minus the instructor-only and
development-only files. Because `build-kvstore/` now contains its own self-contained
`Dockerfile`, `docker-compose.yml`, `requirements.txt`, and `.gitignore` (the workshop root mounts at
`/workspace`), the extraction is essentially "copy `build-kvstore/`, drop a few folders."

## Include (everything in build-kvstore/ except the excludes below)

- `LAB-MANUAL.md`, `README.md`
- `Makefile`, `tools/`, `checkpoints/`, `stages/`, `incidents/`
- `docs/` (stages.md, diffs/, load-balancing-client-vs-server.md)
- `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `.gitignore`

## Exclude (do NOT copy into the template)

- `instructor/` — answers, SPEC, HANDOFF, bug log, this file
- `kvstore/` — git-ignored working copy (attendees create it with `make start`)
- `progress.json` — git-ignored local scoreboard
- `__pycache__/`, `*.pyc` — Python caches
- any `*-snapshot/` dirs created by `make snapshot`

The repo-level artifacts (`wiki/decisions/`, root `WORKSHOP-WALKTHROUGH.md`, root `README.md`,
`CLAUDE.md`, `labs/`, `venv/`) live **outside** `build-kvstore/` and are never part of the template.

## Extraction (one command)

From the monorepo root, into a fresh sibling directory:

```bash
rsync -a --delete \
  --exclude='instructor/' \
  --exclude='kvstore/' \
  --exclude='progress.json' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='*-snapshot/' \
  build-kvstore/ ../kvstore-workshop-template/
```

## Post-extraction checklist

1. `cd ../kvstore-workshop-template`
2. `git init && git add -A && git commit -m "Initial workshop template"`
3. Verify it boots standalone:
   - `docker compose up -d`
   - `docker compose exec workshop bash -c 'make validate'` → expect **18/18**
   - `docker compose exec workshop bash -c 'make start && make up STAGE=01'` (sanity)
4. Confirm `README.md` points at `LAB-MANUAL.md` and that no file links into `instructor/`
   (it's gone): `grep -rn "instructor/" .` should return nothing.
5. On GitHub: push, then **Settings → Template repository → ✅** so attendees get "Use this template".

## Keeping the template in sync later

The workshop is effectively frozen after EuroPython, so re-extraction is rare. If you do change the
workshop, edit it **here** (the monorepo, where `make validate` and the decision log live), then
re-run the rsync above. Never hand-edit the template repo directly — it has no regression suite.
