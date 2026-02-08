# Multi-Region KV Store Assessment - How It Works

This document explains what the assessment tests measure.

---

## Configuration Schema

Student configs specify:
- **`leader_region`**: Where the leader node is deployed (us, eu, or asia)
- **`followers`**: Number of follower nodes per region
- **`quorum`**: Write quorum (W) and read quorum (R)

```json
{
    "leader_region": "us",
    "followers": { "us": 0, "eu": 1, "asia": 1 },
    "quorum": { "write_quorum": 2, "read_quorum": 2 }
}
```

---

## Cost Calculation

Cost is calculated in **dollars** based on node deployment:

| Region | Cost per Node |
|--------|---------------|
| US     | $12           |
| EU     | $15           |
| Asia   | $10           |

**Total Cost** = Leader cost + Sum(followers × region cost)

---

## Test Execution

The assessment runs a workload simulation:
- **100 requests** (configurable by instructor)
- **80/20 read/write ratio** (configurable)
- **Users distributed across US, EU, Asia**

Network latency between regions is simulated:

| From/To | US    | EU    | Asia  |
|---------|-------|-------|-------|
| US      | 3ms   | 120ms | 200ms |
| EU      | 120ms | 3ms   | 95ms  |
| Asia    | 200ms | 95ms  | 3ms   |

---

## Results Measured

- **Availability**: % of successful requests
- **P95 Latency**: 95th percentile response time
- **Avg Latency**: Mean response time
- **Stale Reads**: Count of reads returning outdated data

---

## Quorum Trade-offs

### Strong Consistency (no stale reads)
For `W + R > N` where N = total nodes:
- W=2, R=2 with 3 nodes → Strong consistency ✓
- W=2, R=1 with 3 nodes → May have stale reads ⚠️

### Availability vs Consistency
- Higher R → Fewer stale reads, but lower availability
- Lower R → Higher availability, but risk of stale reads
