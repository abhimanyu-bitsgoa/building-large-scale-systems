# Module 13: Replication Lag

## 🎯 The Scenario

You post a tweet. Twitter says "Posted!" You reload your profile.

**Your tweet isn't there.**

You reload again. Still not there. You panic. You post again. Now you have **two identical tweets**.

*What happened?*

---

## 🧠 Pause and Think

1. If writes go to a Primary and reads come from Replicas, what happens if replicas are behind?
2. How far behind is "too far"?
3. Should you always read from the Primary? What's the trade-off?

---

## 💡 The Concept

### Primary-Replica Architecture
- **Primary:** Accepts all writes
- **Replicas:** Receive copies of data asynchronously
- **Why?** Distribute read load, survive Primary failure

### Replication Lag
The delay between a write hitting Primary and appearing on Replicas.

```
User writes to Primary:  "Post: Hello World" at T=0
Replica 1 receives it:   at T=2 seconds
Replica 2 receives it:   at T=5 seconds

If you read from Replica 2 at T=3... you don't see your post!
```

### Read-Your-Writes Consistency
After writing, route that user's reads to Primary (or to a replica known to be up-to-date) until lag catches up.

---

## 🚀 How to Run

### Step 1: Start the Cluster
```bash
# Primary
python3 workshop_materials/13_replication/primary.py --port 13000 --secondaries 13001,13002 --delay 5

# Secondaries
python3 workshop_materials/13_replication/secondary.py --port 13001 --id 1
python3 workshop_materials/13_replication/secondary.py --port 13002 --id 2
```

### Step 2: Run Visualizer
```bash
python3 workshop_materials/13_replication/visualize_lag.py
```

### Step 3: Write Something
```bash
curl -X POST http://localhost:13000/write \
  -H "Content-Type: application/json" \
  -d '{"key": "tweet", "value": "Hello World"}'
```

**What you'll see:** Primary updates immediately. Secondaries update after the `--delay` period.

---

## 🎮 Micro-Challenge

1. Write to Primary
2. Immediately read from Secondary 1: `curl http://localhost:13001/data/tweet`
3. Wait 5 seconds, read again
4. **Question:** How would you implement "read-your-writes" consistency?

---

## 📚 The Real Incidents

### GitLab — January 2017 (Database Wipe)

GitLab's Postgres Primary was under heavy load. Replication lag grew to 4GB. An engineer tried to fix replication and accidentally ran:

```bash
rm -rf /var/opt/gitlab/postgresql/data
```

...on the **Primary** instead of the Secondary.

6 hours of data was permanently lost. Why?
- Backups were failing silently
- Replication was too far behind to promote
- The one healthy Secondary was also lagging

**Lesson:** Replication lag isn't just a performance problem—it's a data safety problem.

---

### Matrix.org — September 2025 (51TB Restore)

Matrix.org's 51TB database was monolithically replicated. When Primary failed and Secondary also failed during promotion, recovery required restoring from S3.

Restoring 51TB took **24 hours**.

**Lesson:** Large monolithic databases are fragile. Sharding would have reduced "blast radius."

---

## 🏆 Challenge

Implement **Monotonic Reads**:

Track the last version a user has seen. On subsequent reads, only serve from replicas that have at least that version. This prevents "time travel" where users see older data after seeing newer data.
