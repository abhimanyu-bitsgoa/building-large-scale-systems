# Decision log

This folder records **why** non-trivial changes were made to the codebase — not just what
changed (git already tracks that), but the reasoning, the alternatives weighed, and the
consequences. It is the source that the **Learn from history** working principle in
[`CLAUDE.md`](../../CLAUDE.md) reads before proposing or changing anything.

Every entry is also listed in [`INDEX.md`](INDEX.md) — keep it updated whenever you add a
decision file.

## When to add an entry

Add a decision file for any change that a future reader would want the reasoning for:
config/behavior changes, architectural choices, trade-offs between approaches, or anything
that corrects a previous mistake. Trivial edits (typos, formatting) don't need one.

## Naming

One file per decision, named:

```
YYYY-MM-DD_short-kebab-slug.md
```

Example: `2026-05-28_adk-ollama-gemma4-fix.md`. The date prefix keeps the log sorted
chronologically; the slug summarizes the change.

## What to write

Be detailed enough that someone new to the codebase understands the change without prior
context. Copy the template below and fill in every section.

```markdown
# <Title of the decision>

- **Date:** YYYY-MM-DD
- **Status:** accepted | superseded by <file> | reverted
- **Change / commit(s):** <branch, PR, or commit refs>

## Context
What problem or situation prompted this change? What did a reader need to know beforehand?

## Decision
What was actually done, in detail.

## Alternatives considered
Each option weighed, and why it was *not* chosen.

## Trade-offs
What this change costs or gives up. Be honest about the downsides.

## Side effects & risks
What else this touches, what could break, what to watch for afterward.

## References
Links to relevant files, READMEs, incidents, or prior decisions.
```
