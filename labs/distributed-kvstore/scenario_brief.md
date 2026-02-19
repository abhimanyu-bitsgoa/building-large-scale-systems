# 🛒 CloudCart — Distributed KV Store Design Brief

## Your Mission

You are the **infrastructure engineer** at **CloudCart**, an e-commerce startup. Your team needs a distributed key-value store to manage **shopping cart and session data** across multiple servers.

Your job: **Design the right configuration** that balances reliability, performance, and cost.

---

## System Requirements

### Traffic Profile

- **Normal traffic**: ~5 requests/second
- **Flash sale events**: Bursts of 20+ requests/second for short periods
- **Read-heavy**: 70% reads, 30% writes (users browse more than they buy)

### Reliability Requirements

- **Must survive node failures**: At least 1 server can go down without service interruption
- **No stale cart data**: When a user adds an item, it must be visible immediately on next read
- **Auto-recovery preferred**: Failed nodes should be replaced automatically when possible

### Budget

- Each node costs **$10/hour** (1 leader + N followers)
- Management wants **total cost under $50/hour** while meeting all requirements
- Over-provisioning wastes money; under-provisioning risks outages

---

## Your Configuration Decisions

Open `student_config.json` and configure these parameters:

| Parameter | What it controls | Key question |
|-----------|-----------------|--------------|
| `followers` | Number of follower nodes | How many failures can you survive? |
| `write_quorum` (W) | Followers that must ack writes | Higher = more durable, but slower |
| `read_quorum` (R) | Followers queried for reads | Higher = more consistent, but slower |
| `auto_spawn` | Auto-replace dead nodes | Faster recovery, but adds complexity |
| `auto_spawn_delay` | Seconds before respawning | Too fast = thrashing, too slow = long outage |
| `rate_limit_max` | Max requests per window | Too low = reject valid traffic |
| `rate_limit_window` | Window size in seconds | Shorter = faster rate limit recovery |

### The Key Formula

> **W + R > N** guarantees strong consistency (no stale reads)
>
> Where: W = write_quorum, R = read_quorum, N = followers

---

## How You'll Be Graded

The assessment script tests your configuration against 5 scenarios:

1. **Basic Operations (15 pts)** — Can your system read and write data?
2. **Fault Tolerance (25 pts)** — Does it survive node failures?
3. **Consistency (25 pts)** — Are reads always fresh (no stale data)?
4. **Rate Limiting (15 pts)** — Does the gateway protect against traffic bursts?
5. **Recovery (20 pts)** — Can the system recover after failures?

**Total: 100 points**

---

## Steps

1. **Experiment**: The instructor will demo the system — observe how quorums, failures, and rate limiting work
2. **Read**: Study this brief and understand the requirements
3. **Design**: Edit `student_config.json` with your choices
4. **Justify**: Fill in all 4 justification fields — explain *why* you chose each setting
5. **Test**: Run the assessment and iterate:
   ```bash
   python labs/distributed-kvstore/assessment.py --config labs/distributed-kvstore/student_config.json
   ```
6. **Improve**: Adjust your config based on the results and re-run

> **💡 Tip**: There's no single "perfect" answer. The assessment tests whether your configuration *meets the requirements* — different valid configurations can all score well.
