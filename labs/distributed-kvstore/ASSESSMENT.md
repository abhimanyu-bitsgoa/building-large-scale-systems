# Distributed KV Store - Assessment Challenge

## Problem Statement

You are a cloud architect tasked with deploying a **globally distributed key-value store** for a startup with users across the US, Europe, and Asia. Your goal is to **minimize cost** while achieving **good latency** and **high availability**.

---

## Your Constraints

### User Distribution
- 33% of users in **US (Salt Lake City)**
- 33% of users in **EU (Berlin)**  
- 33% of users in **Asia (Mumbai)**

### Workload
You will specify the read/write ratio. The assessment will run **99 requests** following your specified ratio.

### Network Latency (Round Trip)
| Route | Latency |
|-------|---------|
| Same Region | ~6ms |
| US ↔ EU | ~240ms |
| US ↔ Asia | ~400ms |
| EU ↔ Asia | ~190ms |

---

## Pricing

### Node Cost (per region, per test run)
| Region | Cost |
|--------|------|
| Asia (Mumbai) | 10 credits |
| US (Salt Lake City) | 12 credits |
| EU (Berlin) | 15 credits |

### Service Discovery (Auto-Respawn)
Automatically restarts failed nodes. **Costs extra per region.**

| Region | Additional Cost |
|--------|-----------------|
| Asia | +15 credits |
| US | +18 credits |
| EU | +22 credits |

> **Note**: Without service discovery, failed nodes stay dead until manually restarted!

---

## Your Configuration

Submit a JSON file with:

```json
{
  "regions": {
    "us": true,
    "eu": true, 
    "asia": true
  },
  "quorum": {
    "write_quorum": 2,
    "read_quorum": 1
  },
  "service_discovery": true,
  "stale_reads_allowed": false,
  "rw_ratio": 80,
  "justification": "Your reasoning here..."
}
```

### Parameters Explained

| Parameter | Description |
|-----------|-------------|
| `regions` | Which regions to deploy nodes in |
| `write_quorum` (W) | Followers that must acknowledge writes |
| `read_quorum` (R) | Followers to query for reads |
| `service_discovery` | Auto-restart failed nodes (+cost) |
| `stale_reads_allowed` | Allow reading old data? (If false, you'll be penalized for stale reads) |
| `rw_ratio` | Percentage of requests that are reads (0-100) |

---

## Scoring

Your score combines three factors (weights tunable by instructor):

```
TOTAL = Cost Score + Latency Score + Availability Score - Stale Penalty
```

| Factor | Weight | Goal |
|--------|--------|------|
| Cost | 33% | Spend less credits |
| Latency (P95) | 33% | Lower response time |
| Availability | 34% | Fewer failed requests |

**Stale Read Penalty**: -20 points per stale read (if `stale_reads_allowed: false`)

---

## Key Trade-offs to Consider

1. **More regions = Lower latency, Higher cost**
2. **Higher W = Stronger durability, Slower writes**
3. **Higher R = Stronger consistency, Slower reads**
4. **R + W > N = No stale reads possible**
5. **Service Discovery = Higher cost, Better availability**

---

## Running the Assessment

```bash
# Test your config
python assessment.py --config my_config.json

# View help
python assessment.py --help
```

Good luck! 🚀
