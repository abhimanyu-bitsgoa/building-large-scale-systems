# Introduce CLAUDE.md (agent guidance) and a decision log

- **Date:** 2026-06-14
- **Status:** accepted
- **Change / commit(s):** branch `europython-lab-design` (PR into `europython-branch` pending)

## Context

The repository had **no agent-guidance file of any kind** — no `CLAUDE.md`, no project
`.claude/` directory, no `AGENTS.md`, and no user-level guidance. Every Claude Code session
therefore started "cold" and had to re-discover the codebase (the Docker-only run model, the
port conventions, the `W + R > N` quorum invariant, and — importantly — which files are
*intentional student gaps* rather than bugs to fix).

This repo is a EuroPython teaching workshop that the maintainer also wants to stand as a
proof-of-work showcase, and intends to distribute to attendees as a cleaned-up template repo.
Both goals benefit from explicit, written conventions that survive across sessions and
contributors.

## Decision

1. Added a root **`CLAUDE.md`** containing:
   - A `/init`-style description of what the repo is, the Docker environment, the three labs,
     port conventions, the quorum invariant, component topology, the student-exercise
     structure (so agents don't "fix" intentional `TODO` gaps or leak the solution file),
     and conventions.
   - A **Persona** section (thoughtful, distinguished programmer; simplest correct design).
   - A **Working principles** section (plan first, no assumptions, one task at a time, protect
     against breakage, no gratuitous refactoring, reuse before adding, learn from history).
   - A **Logging decisions** section describing this very workflow.
2. Created **`wiki/decisions/`** with a `README.md` documenting the convention and an ADR
   template, plus this first entry.
3. Added **`wiki/decisions/INDEX.md`** as a chronological index, and a rule in `CLAUDE.md`
   requiring the index to be updated in the same change as any new decision file.

## Alternatives considered

- **`CLAUDE.local.md` vs `CLAUDE.md` vs `AGENTS.md`** — chose committed `CLAUDE.md` because the
  guidance is meant to be shared with collaborators/attendees, not kept private. `CLAUDE.local.md`
  is effectively deprecated (breaks with git worktrees); the `@import` private-file pattern was
  noted as the route for any future *personal* notes. `AGENTS.md` (cross-tool) was considered
  but `CLAUDE.md` fits a Claude Code workflow and can coexist with `AGENTS.md` later.
- **Decision-log location & path form** — chose a root `wiki/decisions/` folder. The path is
  written **relative** (`wiki/decisions/`, not `/wiki/decisions/`) so it resolves correctly from
  the repo root both on the host and inside the container (where the repo is bind-mounted at
  `/workspace`). An absolute `/wiki/...` would not resolve inside the container.
- **Index placement** — kept `INDEX.md` inside `wiki/decisions/` (adjacent to the files it
  indexes) rather than at `wiki/` top level, so the index and entries live together.

## Trade-offs

- A committed `CLAUDE.md` is visible to everyone who clones the repo (intended), so it must stay
  free of anything private.
- Maintaining a decision log adds per-change overhead. Mitigated by scoping it to *non-trivial*
  changes only, and by the index rule that keeps the log discoverable rather than sprawling.
- The Persona/Working-principles guidance changes agent behavior (e.g. agents will now ask when
  unclear and run the assessment after changes). This is the goal, but it makes sessions slightly
  more deliberate.

## Side effects & risks

- The **Learn from history** principle now instructs agents to read `wiki/decisions/` before
  acting. If the log is not kept current, that instruction points at stale or missing context —
  hence the index-update rule and the "keep current alongside commits" guidance.
- Agents will treat `student_config_solution.json` as a spoiler and intentional `TODO` gaps as
  exercises; if future refactors move or rename these, `CLAUDE.md` must be updated to match.

## References

- [`CLAUDE.md`](../../CLAUDE.md)
- [`wiki/decisions/README.md`](README.md)
- [`wiki/decisions/INDEX.md`](INDEX.md)
