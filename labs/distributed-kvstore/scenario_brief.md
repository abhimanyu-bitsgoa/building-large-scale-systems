# 🛒 CloudCart — Incident Investigation Brief

## Situation

You've just joined **CloudCart** as a **Site Reliability Engineer (SRE)**. CloudCart is an e-commerce startup running a distributed key-value store to manage **shopping cart and session data** across multiple servers.

The previous engineer left abruptly, and the system has been plagued with production incidents. Your CTO has handed you **5 open incident tickets** and the system's configuration file (`student_config.json`).

**Your mission**: Investigate each incident, find the root cause in the configuration, and fix it.

---

## System Context

- **Traffic profile**: ~5 req/s normal, 20+ req/s during flash sales (70% reads, 30% writes)
- **Budget**: Each node costs **$10/hour** (1 leader + N followers). Budget cap: **$50/hour**
- **Consistency rule**: **W + R > N** guarantees no stale reads (W = write quorum, R = read quorum, N = followers)

---

## Open Incident Tickets

### 🔴 INC-1: Gateway Flooded During Flash Sale

**Severity**: P1 — Complete service degradation  
**Reported by**: Platform Monitoring  
**Time**: Last Tuesday, 14:02 UTC

**What happened**: During our Valentine's Day flash sale, monitoring detected a sustained burst of 20+ requests/second from a range of IPs (likely scrapers/bots). The gateway was supposed to rate-limit this traffic, but **every request got through**. The entire cluster was overwhelmed and legitimate customers got timeouts for 15 minutes.

**What we know**: Rate limiting *is* enabled. The `rate_limit_max` is set to 20, which should catch this burst. But somehow the limiter never triggered during sustained abuse. The ops team says "it's like the counter keeps resetting before it ever reaches the limit."

**Your task**: Figure out why the rate limiter fails to block sustained bursts and fix the config.

---

### 🔴 INC-2: Ghost Nodes Appearing After Network Blip

**Severity**: P2 — Data integrity risk  
**Reported by**: Infrastructure Team  
**Time**: Last Thursday, 03:17 UTC

**What happened**: A brief network congestion event (~2 seconds of packet loss) between our racks caused heartbeats to be delayed. When the network recovered, we found that the cluster had **spawned a duplicate of the same logical node on a different machine**. We now had two copies of `follower-2` — one on the original machine (which was alive the whole time) and a brand-new one spawned by auto-recovery. Replication traffic was going to both, causing inconsistent data.

**What we know**: Auto-spawn is enabled (good for recovery), but the spawn delay seems extremely aggressive. The original node's heartbeat was only delayed by ~2 seconds due to the network blip, but by the time it arrived, a replacement had already been spawned. On a slow or congested network link, this would happen constantly.

**Your task**: Fix the auto-spawn timing so transient network issues don't trigger unnecessary respawns.

---

### 🔴 INC-3: Stale Cart Data After Checkout

**Severity**: P1 — Customer-facing data corruption  
**Reported by**: Customer Support (12 tickets in one week)  
**Time**: Ongoing

**What happened**: Multiple customers have reported that items they added to their cart "disappeared" on the checkout page, or that a coupon code they applied wasn't reflected when they hit "Pay." One customer was charged for an old cart that didn't include their discount. Investigation shows the **read path is sometimes returning stale data** — a version of the cart that doesn't include the most recent write.

**What we know**: The writes succeed (the leader and enough followers acknowledge). But when a read goes out, it sometimes hits a follower that **hasn't received the latest write yet**. This suggests the read quorum isn't high enough to guarantee overlap with the write quorum. Check whether `W + R > N` holds.

**Your task**: Adjust the quorum settings so reads always return the freshest data.

---

### 🔴 INC-4: Total Write Outage After Single Node Failure

**Severity**: P1 — Complete write path failure  
**Reported by**: PagerDuty Alert  
**Time**: Last Saturday, 03:12 UTC

**What happened**: Two follower nodes went down during a routine rolling update. Within seconds, **all write operations started failing** with `503 Write quorum not available`. The cluster has 5 followers — losing just 2 shouldn't cause a total outage. But it did.

**What we know**: The write quorum (`W=4`) is set too high relative to the number of followers. With 5 followers and `W=4`, losing just 2 nodes means only 3 remain — not enough to meet the write quorum. A shopping cart system should tolerate `floor(N/2)` failures, but the current quorum is so tight that even a minor outage breaks writes.

**Your task**: Lower the write quorum to a value that provides durability without making the system fragile to small-scale failures.

---

### 🟡 INC-5: Infrastructure Costs 2× Over Budget

**Severity**: P3 — Financial  
**Reported by**: Finance Team  
**Time**: Monthly cost review

**What happened**: Finance flagged that our KV store infrastructure costs **$60/hour** (1 leader + 5 followers = 6 nodes × $10/hr). Our budget is $50/hour. The previous engineer provisioned 5 followers "for safety" but we only need to survive 1 node failure. This is classic over-provisioning.

**What we know**: With the right quorum settings, **3 followers** can survive 1 failure and provide strong consistency. That would bring costs to $40/hour — well within budget.

**Your task**: Right-size the cluster to meet reliability needs without exceeding the budget.

---

## Investigation Toolkit

Use these commands to reproduce and diagnose the incidents:

```bash
# Check cluster status — see all nodes and their health
curl http://localhost:7000/status

# Write & read data — test basic operations
curl -X POST http://localhost:8000/write -H "Content-Type: application/json" \
  -d '{"key": "test", "value": "hello"}'
curl http://localhost:8000/read/test

# Kill a node — simulate failures (INC-4)
curl -X POST http://localhost:7000/kill/follower-1

# Spawn a replacement — test recovery (INC-2)
curl -X POST http://localhost:7000/spawn

# Check gateway stats — inspect rate limiter state (INC-1)
curl http://localhost:8000/stats

# Rapid-fire requests — reproduce burst traffic (INC-1)
for i in $(seq 1 30); do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/read/test; done
```

---

## Deliverables

1. **Fix** `student_config.json` — resolve all 5 incidents
2. **Justify** — fill in all 4 justification fields explaining what was wrong and why your fix addresses it
3. **Validate** — run the assessment and confirm your fixes work:
   ```bash
   python labs/distributed-kvstore/assessment.py --config labs/distributed-kvstore/student_config.json
   ```

## Grading

| Scenario                                 | Points | What it validates                      |
|------------------------------------------|--------|----------------------------------------|
| INC-0: Basic Operations                  | 15     | Reads and writes work                  |
| INC-1: Gateway Flood (Rate Limiting)     | 15     | Sustained burst protection (INC-1)     |
| INC-3: Stale Cart Data (Consistency)     | 25     | No stale reads (INC-3)                 |
| INC-4: Write Outage (Fault Tolerance)    | 25     | Survives node failures (INC-4)         |
| INC-2/5: Recovery & Right-Sizing         | 20     | System recovery (INC-2 + INC-5)        |

**Total: 100 points**

> **💡 Tip**: The incidents are interconnected. Fixing one without considering the others can introduce new problems. Think about how `W`, `R`, and `N` interact before making changes.
