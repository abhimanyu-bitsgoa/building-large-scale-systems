#!/usr/bin/env bash
# export-student-repo.sh — mirror the curated student subset of build-kvstore/ into the
# attendee repo (github.com/<you>/europython-planetscale-systems).
#
#   THE MONOREPO'S build-kvstore/ IS THE SINGLE SOURCE OF TRUTH.
#
# The attendee repo is a byte-exact copy of build-kvstore/ MINUS the instructor-only and
# working-state files listed below. To reconcile any change you make here, re-run this script
# at the same destination, then review + commit + push in the attendee repo. Because it uses
# `rsync --delete`, files you remove here are removed there too — the two stay in lockstep.
#
# Usage:
#   instructor/export-student-repo.sh /path/to/europython-planetscale-systems         # apply
#   instructor/export-student-repo.sh -n /path/to/europython-planetscale-systems      # dry-run
#
# What is EXCLUDED from the attendee repo (everything else is copied verbatim):
#   instructor/        instructor + speaker material, exercise answers, the slide deck PDF, and the
#                      build-narrative docs/ (docs/diffs/, load-balancing ref) — all spoiler/reference
#   kvstore/           the attendee's own working copy (seeded by `make start`; git-ignored)
#   progress.json      per-run state (git-ignored)
#   __pycache__ *.pyc  build artifacts
#   .git/ .DS_Store    never mirror the destination's history or OS cruft
set -euo pipefail

DRY=""
if [ "${1:-}" = "-n" ] || [ "${1:-}" = "--dry-run" ]; then DRY="--dry-run"; shift; fi

DEST="${1:?usage: export-student-repo.sh [-n] /path/to/europython-planetscale-systems}"
SRC="$(cd "$(dirname "$0")/.." && pwd)"   # build-kvstore/  (this script lives in build-kvstore/instructor/)

[ -d "$DEST" ] || { echo "error: destination '$DEST' does not exist (create/clone it first)"; exit 1; }

echo "Source (truth): $SRC"
echo "Destination:    $DEST"
[ -n "$DRY" ] && echo "(dry run — nothing will be written)"
echo

rsync -a --delete $DRY \
  --exclude '/instructor/' \
  --exclude '/kvstore/' \
  --exclude '/progress.json' \
  --exclude '__pycache__/' \
  --exclude '*.py[cod]' \
  --exclude '.git/' \
  --exclude '.DS_Store' \
  "$SRC"/ "$DEST"/

echo
if [ -n "$DRY" ]; then
  echo "Dry run complete. Re-run without -n to apply."
elif [ -d "$DEST/.git" ]; then
  echo "Synced. Changes in the attendee repo:"
  git -C "$DEST" status --short
  echo
  echo "Next: review the diff, then in $DEST run:  git add -A && git commit && git push"
else
  echo "Synced. ($DEST is not a git repo yet — 'git init' there, then commit & push.)"
fi
