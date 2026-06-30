# Add an instructor FAQ doc (seeded with the Stage 04 rate-limiting Q&A)

**Date:** 2026-06-28
**Status:** accepted
**Area:** `build-kvstore/instructor/faq.md` (new), instructor-only (excluded from attendee template)

## Context

While reviewing Stage 04, the speaker raised two questions worth capturing for live Q&A: (1) a fresher
incident than GitHub's 2018 DDoS, and (2) the sharp architectural point that the rate limiter is itself
a single box that could be overwhelmed. Both have honest, useful answers (web-verified), and they're
exactly the kind of thing that recurs across deliveries — so they belong in a durable, per-stage FAQ
rather than scattered in chat or buried in the narrative docs.

## Decision

Add `build-kvstore/instructor/faq.md`, **divided per stage (01–10, matching the current code ladder
after the 2026-06-30 merge/renumber — single node `01`, vertical `02`, horizontal+load-balancing `03`,
rate limiting `04`, … `10`)**, with the two Stage 04 rate-limiting Q&As filled in and the other stages
stubbed (`_No questions logged yet._`) so the file grows over time. Seeded content:

- **"Is there a more recent example than GitHub 2018?"** → HTTP/2 Rapid Reset (CVE-2023-44487,
  Aug–Oct 2023; Google 398M rps, Cloudflare 201M, AWS 155M; ~20k-machine botnet; cheap-to-send /
  expensive-to-serve), the climbing Cloudflare Tbps records (3.8 → 7.3 → ~31 Tbps, 2024–2025), and the
  AWS Dec 7 2021 self-inflicted retry storm.
- **"Isn't the rate limiter itself a single box that gets overwhelmed?"** → honest "yes, in the lab,"
  then production reality (anycast + POPs, work asymmetry of O(1) drop vs expensive serve, layered
  L3/L4→L7 defense) and the deep tension (distributed counting: per-node counters leak the limit, a
  shared central counter re-creates the bottleneck → approximate counting).

Each answer ends with primary sources for live citation.

## Alternatives considered

- **Fold the Q&A into `motivating-incidents.md` / `real-world-systems.md`.** Rejected: those are the
  narrative spine and pattern catalog; a Q&A-shaped, per-stage FAQ is a distinct artifact the speaker
  can scan mid-session. Cross-linked instead. (A follow-up may still refresh the Stage 04 *incident* in
  `motivating-incidents.md`/`slide-deck.md`; the FAQ doesn't preclude that.)
- **Only a Stage 04 section.** Rejected: the speaker asked for the file "divided per section," so all
  10 stage sections (01–10) are stubbed as a skeleton.

> **Note:** the broader instructor narrative docs (`motivating-incidents.md`, `real-world-systems.md`,
> and the session's new `slide-deck.md` / `architecture.md`) still use the *pre-renumber* 00–10 ladder
> and are now out of sync with the code (which is 01–10 with horizontal+load-balancing merged into 03).
> This FAQ was authored against the **current code ladder**; reconciling the other docs is tracked
> separately.

## Accuracy guardrails

- All figures web-verified (Rapid Reset rps numbers + CVE, Cloudflare Tbps records by date, AWS Dec
  2021 self-DDoS root cause) and dated; sources listed inline.

## Side effects / risks

- **No code touched** → `make validate` unaffected (still 18/18). Pure instructor documentation,
  excluded from the attendee template.
