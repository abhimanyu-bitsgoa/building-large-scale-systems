# Module 2: Load Balancing & Rate Limiting

## 🎯 The Scenario

**Problem 1:** You have 3 servers, but one is overloaded while others sit idle. Requests aren't distributed evenly.

**Problem 2:** A single customer is sending 10,000 requests per second. They're using 90% of your capacity and crowding out everyone else.

*How do you fix both?*

---

## 🧠 Pause and Think

1. If you randomly pick a server, will traffic be evenly distributed?
2. What's the fairest way to limit abusive clients without hurting good ones?
3. What happens if the rate limit is too aggressive?

---

## 💡 The Concepts

### Load Balancing
Distributing incoming requests across multiple servers. Common strategies:
- **Round-robin:** Rotate through servers in order
- **Random:** Pick a random server
- **Least connections:** Send to the server with fewest active requests
- **Consistent hashing:** Route based on request content (see Module 3)

### Rate Limiting
Controlling how many requests a client can make in a time window.
- **Token Bucket:** Clients "spend" tokens; tokens refill over time
- **Fixed Window:** Count requests per time window (e.g., 100/minute)
- **Sliding Window:** Rolling window for smoother limiting

---

## 🚀 How to Run

### Part A: Load Balancing Visualization

**Step 1:** Ensure 3 nodes are running (from Module 1)
```bash
python3 workshop_materials/01_nodes/node.py --port 5001 --id 1
python3 workshop_materials/01_nodes/node.py --port 5002 --id 2
python3 workshop_materials/01_nodes/node.py --port 5003 --id 3
```

**Step 2:** Run the visualizer
```bash
python3 workshop_materials/02_networking/visualize_load_balance.py
```

**What you'll see:** An ASCII bar chart showing requests distributed across nodes.

---

### Part B: Rate Limiting Demo

```bash
python3 workshop_materials/02_networking/visualize_rate_limit.py
```

**What you'll see:**
- **Good User:** Gets `200 OK` responses
- **Bad Actor:** Gets `429 Too Many Requests` after exceeding limit

---

## 📚 The Real Incidents

### Cloudflare August 2025 — Single Customer Saturation

A single customer began requesting cached objects at such a high rate that they **saturated Cloudflare's peering links** with AWS us-east-1. The outage lasted 3 hours.

**Root cause:** No per-customer traffic quota.  
**Fix:** Manual rate limiting of the customer's traffic.

**Lesson:** Rate limiting isn't just for attacks—it prevents one customer from monopolizing shared infrastructure.

---

### GitHub July 2022 — Rate Limiter Misconfiguration

GitHub deployed a new feature flag system. The rate limiter for this system was set too aggressively. Internal services couldn't fetch configuration files fast enough, causing partial outages.

**Lesson:** Rate limits that are too strict break your own systems. Test with realistic internal traffic patterns.

---

## 🏆 Challenge

Implement a **Fixed Window** rate limiting strategy:
1. Count requests per 60-second window
2. Reject requests once the count exceeds 100
3. Reset the count at the start of each new window

Swap it into the visualizer using the Strategy Pattern.
