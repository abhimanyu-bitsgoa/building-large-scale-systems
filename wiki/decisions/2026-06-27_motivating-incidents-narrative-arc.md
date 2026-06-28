# Add an incident-driven "narrative arc" report for the talk

**Date:** 2026-06-27
**Status:** accepted
**Area:** `build-kvstore/instructor/motivating-incidents.md` (new), instructor-only (excluded from attendee template)

## Context

The speaker wanted a single artifact that gives the EuroPython talk a *story spine*: for every stage
(00–10), a **real outage or documented failure in a real planet-scale system** that motivates *why
that stage exists*. The goal is presentation flow — open each stage with the failure (the "scar"),
then the stage's fix lands as inevitable rather than academic.

We already had [`instructor/real-world-systems.md`](../../build-kvstore/instructor/real-world-systems.md),
but that doc answers a *different* question — "what production system embodies this stage's
**pattern**?" (the "what"). It is a pattern catalog, not a motivation/narrative. The new request is
the "why" that comes *before* the concept in a talk.

## Decision

Add a new instructor file `build-kvstore/instructor/motivating-incidents.md` structured as a
narrative arc. Per stage: a **hook** line to say out loud, **what really happened** (the real
incident, dated and attributed), the **lesson → why this stage exists**, an optional **caveat** where
our teaching model simplifies, and **the arc (→ next)** that hands the next stage its problem. Plus an
opening framing, a summary table, and a sourced citation list.

Incident chosen per stage:

| Stage | Incident anchor |
|---|---|
| 00 | Redis's origin (antirez/LLOOGG, 2009) — a dict behind a socket |
| 01 | Cloudflare regex CPU meltdown, Jul 2 2019 (single-thread/CPU ceiling) |
| 02 | Twitter "Fail Whale" — single primary as SPOF + capacity wall |
| 03 | "The Tail at Scale" (Dean & Barroso, CACM 2013) — slow node sets p99 |
| 04 | GitHub 1.35 Tbps DDoS (2018, external) + DynamoDB Sep 20 2015 retry storm (self-inflicted) |
| 05 | GitLab Jan 31 2017 — deleted primary, 6h data loss, backups broken |
| 06 | Replica-lag stale reads — Facebook "Scaling Memcache" (NSDI 2013) |
| 07 | Kafka `acks=all`/`min.insync.replicas` zero-fault stall + CAP |
| 08 | Roblox 73-hour Consul/BoltDB outage (Oct 2021) |
| 09 | Netflix Chaos Monkey (2011) — recovery must be automatic |
| 10 | No incident — synthesis; a table mapping each layer back to its scar |

## Alternatives considered

- **Fold the incidents into `real-world-systems.md`.** Rejected: that doc is already long and serves
  a distinct purpose (pattern → system mapping). Mixing "why (incident)" with "what (pattern)" would
  blur both. Kept them as complementary companions and cross-linked them at the top/bottom of each.
- **Put it in the attendee-facing `LAB-MANUAL.md`.** Rejected: it's speaker/presentation material
  (hooks, "say this" lines, pacing), so it belongs in `instructor/`, which is excluded from the
  attendee template — consistent with where `INSTRUCTOR-GUIDE.md` lives.
- **One incident per stage vs. two for some.** Stage 04 keeps two (GitHub external flood + DynamoDB
  self-inflicted retry storm) because "flood" has two genuinely different real-world shapes and the
  self-DDoS is the more surprising, memorable point for the room.

## Accuracy guardrails (important — this is for a public talk)

- Verified the load-bearing specifics via web search before writing: Roblox (73h, Consul streaming +
  BoltDB freelist), DynamoDB **Sep 20 2015** (metadata-service retry storm; GSI-inflated membership),
  and GitLab (Jan 31 2017, ~300 GB, ~6h lost, all backups ineffective).
- **Deliberately separated the 2015 DynamoDB incident from the later AWS DNS Planner/Enactor outage**
  — a naive search conflates them. We attribute only the metadata/retry-storm story to 2015.
- Carried the existing honesty caveats from `INSTRUCTOR-GUIDE.md`/`talk-readiness-findings` into the
  doc: the quorum is a `W+R>N` rule on a *single-leader* system with overlap engineered by port
  ordering; recovery is **follower-only**, not leader election; staleness is made deterministic for
  reproducible demos. Each appears as a per-stage **Caveat** so the speaker doesn't overclaim.

## Side effects / risks

- **No code touched**, no behavior change → `make validate` unaffected (still 18/18). This is
  pure instructor documentation.
- Risk: incident facts drift or are misremembered live. Mitigation: every claim has a **Sources**
  entry with a primary URL (vendor postmortems / the original paper) for the speaker to verify or cite
  on a slide.
- Risk: overlap/confusion with `real-world-systems.md`. Mitigation: explicit "why vs. what" framing
  and reciprocal cross-links between the two docs.
