# 2026-06-28 — Add `.gitattributes` to force LF line endings (cross-platform attendees)

**Status:** accepted

## Context / the bug

An attendee on **Windows** cloned the repo, ran the workshop inside Docker, and hit:

```
$ make lab STAGE=10
WORKERS= bash tools/tmux_lab.sh 10
: invalid option namene 26: set: pipefail
make: *** [Makefile:33: lab] Error 2
```

Root cause: **CRLF line endings**. Git for Windows defaults to `core.autocrlf=true`, so on
`git clone` it rewrote every text file's `\n` into `\r\n` in the attendee's working tree. The
repo is **bind-mounted** into a Linux container (`docker-compose.yml`: `.:/workspace`), so the
container's `bash` reads the host files verbatim — including the trailing `\r`. Line 26 of
`tools/tmux_lab.sh` becomes `set -euo pipefail\r`, and bash treats `pipefail\r` as an unknown
option. (The garbled message is `line 26: set: pipefail\r: invalid option name` — the `\r`
carriage-returns the cursor to the line start and overwrites it.)

On the author's machine (macOS, `core.autocrlf` unset) the files are LF in both the index and
the working tree, so the bug was invisible locally. Confirmed via `git ls-files --eol`: every
tracked file was already `i/lf w/lf`. The repo is 100% text (py/md/sh/json/yml/txt) — **no
tracked binaries** — so a blanket normalization rule carries no corruption risk.

## Decision

Add a repo-root `.gitattributes` that forces **LF on checkout for every OS**:

```
* text=auto eol=lf
*.sh / *.py / Makefile / Dockerfile / *.yml / *.yaml / *.json / *.md / *.txt / .gitignore  text eol=lf
```

`.gitattributes` is committed, so it **overrides each attendee's local `core.autocrlf`** — no
per-machine setup, no instructions to memorize. Ran `git add --renormalize .` to apply the
policy to tracked files; because everything was already LF, this produced **zero content churn**
(only `.gitattributes` itself is new).

## Alternatives considered

- **`sed -i 's/\r$//' …` / `dos2unix` as a documented fix step.** This is the *reactive*
  remedy for an already-broken clone, not prevention. It mutates the attendee's working tree by
  hand and has to be re-run on every fresh clone. Kept only as the "already cloned, fix it now"
  escape hatch in attendee docs — not the primary defense.
- **Normalize in the `Dockerfile` (`RUN dos2unix …`).** Ineffective here: the image is built,
  then the bind mount (`.:/workspace`) **overlays** the image's `/workspace` with the host's
  CRLF files at runtime. A build-time fix never touches the files the container actually runs.
- **A container entrypoint / `make` target that strips `\r` at startup.** Works, but mutates the
  user's checked-out files as a side effect of running the lab, and adds a moving part. The
  declarative `.gitattributes` fixes the problem one layer earlier (at checkout) and is the
  industry-standard approach.
- **Tell attendees to set `git config --global core.autocrlf input`.** Relies on every attendee
  configuring their machine correctly before cloning — exactly the kind of per-person setup the
  workshop tries to avoid. `.gitattributes` makes the repo self-correcting instead.

## Side effects / risks

- Windows attendees who open scripts in an editor that *requires* CRLF would now see LF — a
  non-issue for VS Code, Notepad++, modern editors, and irrelevant inside the Linux container.
- Future contributors get LF working trees regardless of their `core.autocrlf`; correct for a
  repo whose scripts only ever run on Linux.
- No behavior change for existing macOS/Linux clones (already LF). `make validate` unaffected
  (no code touched).

## Follow-up for attendees who *already* cloned with CRLF

`.gitattributes` fixes future clones. An existing broken checkout needs a one-time renormalize:

```bash
git rm --cached -r . && git reset --hard      # re-checkout under the new rules
# or, without touching git, strip CR from scripts in place:
find . -name '*.sh' -exec sed -i 's/\r$//' {} +
```
