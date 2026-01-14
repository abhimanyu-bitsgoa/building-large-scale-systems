# Module 14: Distributed Locking

## 🎯 The Scenario

It's concert ticket day. **1 seat left.** 1,000 people click "Buy" at the exact same millisecond.

Your code:
```python
if seats_available > 0:
    seats_available -= 1
    charge_credit_card()
    confirm_ticket()
```

On one server, this works. On 10 servers running simultaneously?

**You just sold 1,000 tickets for 1 seat.**

*How do you prevent double-booking in a distributed system?*

---

## 🧠 Pause and Think

1. In a single process, you'd use a mutex. But data is on different machines.
2. What if two servers both check `seats_available` at the same time?
3. How do you ensure only ONE server can sell that seat?

---

## 💡 The Concept

### Distributed Locking
An external "Lock Coordinator" (Redis, Zookeeper, etcd) that all servers consult.

```
Server A: "I want to lock seat-42"
Coordinator: "Granted. You have 5 seconds."
Server A: ... checks, charges, confirms ...
Server A: "Release lock on seat-42"

Server B: "I want to lock seat-42"
Coordinator: "Denied. Server A has it."
Server B: (waits or fails)
```

### Critical Properties
1. **Mutual Exclusion:** Only one holder at a time
2. **Deadlock-Free:** Locks eventually expire (TTL)
3. **Fault-Tolerant:** Survives coordinator restarts

---

## 🚀 How to Run

### Step 1: Start Lock Server
```bash
python3 workshop_materials/14_locking/lock_server.py
```

### Step 2: Run Visualizer
```bash
python3 workshop_materials/14_locking/visualize_locking.py
```

### Step 3: Simulate the Race
Open two terminals and run simultaneously:
```bash
# Terminal A
python3 workshop_materials/14_locking/book_ticket.py --id Node_Alpha

# Terminal B
python3 workshop_materials/14_locking/book_ticket.py --id Node_Beta
```

**What you'll see:**
- One node acquires the lock: "Lock ACQUIRED!" ✅
- Other node is denied: "Permission DENIED" ❌
- Winner holds lock for 2 seconds (doing work), then releases
- If winner crashes, TTL ensures lock expires anyway

---

## 🎮 Micro-Challenge

1. Start both book_ticket processes at the same time
2. Kill the winner (Ctrl+C) before it releases the lock
3. **Question:** How long until the loser can acquire the lock?

---

## 📚 The Real Incident

### Redis SETNX Race Condition (Common Pattern)

Many teams implement locking with Redis `SETNX`:

```python
if redis.setnx("lock:seat-42", "my_id"):
    redis.expire("lock:seat-42", 5)  # ← DANGER!
    do_work()
    redis.delete("lock:seat-42")
```

**The Bug:** Between `setnx` and `expire`, the server can crash. The lock is acquired but never expires. **Deadlock.**

**The Fix:** Use `SET key value EX 5 NX` (atomic set-if-not-exists with expiry) or a proper distributed lock library like Redlock.

---

### Cloudflare — November 2025 (Configuration Lock)

Cloudflare's outage was partly caused by configuration data that was "locked" by a publishing mechanism. When the mechanism failed, the lock wasn't released, preventing configuration updates that could have fixed the issue faster.

**Lesson:** Critical recovery paths should never be blocked by the same locks that protect normal operations.

---

## 🏆 Challenge

Implement **Redlock**:

Instead of one Redis instance, use 3+. A lock is only acquired if you successfully lock a majority. This survives single-node failures.

Beware: Redlock is controversial. Read Martin Kleppmann's "How to do distributed locking" for the debate.
