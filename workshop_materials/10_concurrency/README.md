# Module 10: Thundering Herd (Cache Stampede)

## 🎯 The Scenario

Your homepage data is cached for 60 seconds. At 12:00:00, the cache expires.

At that exact moment, **10,000 users** hit refresh. They all see "cache miss." They all query the database simultaneously.

Your database receives 10,000 identical queries in 1 millisecond. 💥

*How do you prevent this stampede?*

---

## 🧠 Pause and Think

1. If 10,000 requests all miss the cache at once, should all 10,000 hit the database?
2. What if only ONE request fetches from the database, and the other 9,999 wait for it?
3. How do you coordinate "who goes first"?

---

## 💡 The Concept

### The Problem: Cache Stampede
When a popular cache key expires or is invalidated, all concurrent requests trigger expensive backend operations.

### The Solution: Single Flight
Only **one** request performs the actual work. All other concurrent requests for the same key **wait** for that result.

```
Request 1: "Give me homepage data"  →  "I'll fetch it" (hits DB)
Request 2: "Give me homepage data"  →  "Someone's already fetching, I'll wait..."
Request 3: "Give me homepage data"  →  "Someone's already fetching, I'll wait..."
...
Request 1 finishes:  →  All waiters get the result
```

**Result:** 1 database query instead of 10,000.

---

## 🚀 How to Run

```bash
python3 workshop_materials/10_concurrency/cache_stampede.py
```

**Expected output:**
```
🧪 Scenario 1: STAMPEDE (No Protection)
  Client 0 → Cache miss → Querying DB...
  Client 1 → Cache miss → Querying DB...
  Client 2 → Cache miss → Querying DB...
  ...
  Total DB Queries: 5 😭

🧪 Scenario 2: SINGLE_FLIGHT (Protected)
  Client 0 → Cache miss → Querying DB...
  Client 1 → Waiting for ongoing request...
  Client 2 → Waiting for ongoing request...
  ...
  Total DB Queries: 1 😊
```

---

## 📚 The Real Incidents

### Roblox — October 2021 (73-Hour Outage)

Roblox upgraded Consul from v1.9 to v1.10, enabling a new streaming feature. Under high load, this created a pathological performance issue.

When Consul became unhealthy:
1. All services tried to reconnect simultaneously (thundering herd)
2. The recovery traffic exceeded Consul's capacity
3. Even upgraded hardware (128 cores) couldn't handle the stampede

The fix required:
- Completely shutting down Consul
- Resetting state from a snapshot
- **Slowly** bringing services back online to avoid another herd

**Lesson:** Recovery is just as dangerous as failure. Introducing jitter and rate limits during recovery prevents stampedes.

---

### AWS — October 2025 (DNS Retry Storm)

When AWS fixed the deleted DNS record, millions of SDK clients simultaneously retried:

1. Exponential backoff all started at the same time
2. All clients hit 1s delay together, then 2s together, then 4s together
3. Synchronized "waves" of traffic overwhelmed the control plane

**Lesson:** Exponential backoff without **jitter** (randomization) doesn't prevent thundering herds—it just changes the timing of the waves.

---

## 🏆 Challenge

Implement **Jitter**:

When a cache miss occurs, instead of retrying immediately, wait for:
```
delay = base_delay + random(0, base_delay)
```

Show how this desynchronizes the herd.
