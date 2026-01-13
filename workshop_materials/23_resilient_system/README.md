# Module 23: The Resilient System (Grand Capstone)

## 🎯 The Scenario

Congratulations. You've just been promoted to **Lead Architect** at a fast-growing startup. Your CEO walks in:

> "We're launching globally next month. I need you to build a system that **never goes down**. Our competitor lost $50 million in 6 hours when AWS US-East-1 collapsed last year. That cannot happen to us."

You have 3 database servers. Users will be hitting your API from around the world. Servers *will* crash. Networks *will* fail. Your job is to build a system that **survives chaos**.

---

## 🧠 Pause and Think

Before you look at the solution, ask yourself:

1. How will your client know which servers are alive?
2. If Server 2 dies mid-write, how do you ensure data isn't lost?
3. If you add a 4th server, how do you redistribute data without downtime?
4. How do you prevent a "thundering herd" when servers come back online?

*Write down your answers. We'll see how close you get.*

---

## 💡 The Concepts (All Together)

This module combines **everything** you've learned:

| Concept | How It's Used |
|---------|---------------|
| **Service Discovery** (Module 11) | Registry tracks which nodes are alive via heartbeats |
| **Heartbeats** (Module 11) | Nodes ping the registry every 2 seconds |
| **Consistent Hashing** (Module 3) | Keys are distributed across nodes; adding/removing nodes moves minimal data |
| **Quorum Writes** (Module 5) | Data is written to W=2 nodes before acknowledging success |
| **Replication** (Module 13) | Each key is stored on multiple nodes for redundancy |
| **Circuit Breaker** (Module 9) | Client stops hitting dead nodes immediately |
| **Retry with Jitter** (Module 10) | Prevents thundering herd on recovery |

---

## 🏗️ System Architecture

```
                      ┌───────────────────┐
                      │     Registry      │ ← Knows all nodes
                      │   (Port 5000)     │    Receives heartbeats
                      └─────────┬─────────┘
                                │ 
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
   ┌─────────┐             ┌─────────┐             ┌─────────┐
   │ Node 1  │◄───────────►│ Node 2  │◄───────────►│ Node 3  │
   │ :5001   │  Replicate  │ :5002   │  Replicate  │ :5003   │
   └─────────┘             └─────────┘             └─────────┘
        ▲                       ▲                       ▲
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
                      ┌─────────┴─────────┐
                      │   Smart Client    │ ← Routes via Consistent Hashing
                      │  (cluster_client) │    Failover on node death
                      └───────────────────┘
                                ▲
                      ┌─────────┴─────────┐
                      │  Unified Dashboard │ ← Real-time cluster view
                      │ (unified_dashboard)│
                      └───────────────────┘
```

---

## 🚀 How to Run

### Step 1: Start the Registry (The Brain)
```bash
python3 workshop_materials/23_resilient_system/registry.py
```

### Step 2: Start 3 Resilient Nodes
Open 3 separate terminals:
```bash
# Terminal 1
python3 workshop_materials/23_resilient_system/resilient_node.py --port 5001 --id node-1

# Terminal 2
python3 workshop_materials/23_resilient_system/resilient_node.py --port 5002 --id node-2

# Terminal 3
python3 workshop_materials/23_resilient_system/resilient_node.py --port 5003 --id node-3
```

### Step 3: Launch the Unified Dashboard
```bash
python3 workshop_materials/23_resilient_system/unified_dashboard.py
```

You should see all 3 nodes with green status and a linear hash ring visualization.

### Step 4: Test Data Operations
```bash
# Write data (goes to 2+ nodes for quorum)
curl -X POST http://localhost:5000/data \
  -H "Content-Type: application/json" \
  -d '{"key": "user_123", "value": "Alice"}'

# Read data (with automatic failover)
curl http://localhost:5000/data/user_123

# Check cluster health
curl http://localhost:5000/cluster-status
```

### Step 5: Load Test (See Distribution!)
```bash
python3 workshop_materials/23_resilient_system/load_test.py
```

This sends 50 requests and shows which nodes received them — demonstrating consistent hashing in action!

---

## 🔥 The Chaos Challenge

Now let's break things and watch the system heal.

### Challenge 1: Kill a Node (For scale-up nodes)
```bash
# First, add a new node via scale-up
curl -X POST http://localhost:5000/scale-up

# Now kill it (this one will fully terminate)
curl -X POST http://localhost:5000/kill/node-4
```

**Watch the dashboard.** Node-4 should disappear.

### Challenge 2: Simulate Node Death (For manually-started nodes)
For nodes you started manually (node-1, node-2, node-3), the kill command marks them as dead but you need to press **Ctrl+C** in their terminal to fully stop them.

```bash
# This marks node-2 as dead in the registry
curl -X POST http://localhost:5000/kill/node-2
```

Then press Ctrl+C in node-2's terminal.

**Try another write.** It should still succeed! (Quorum of 2 from remaining nodes)

### Challenge 2: Scale Up Under Load
```bash
# Add a new node
curl -X POST http://localhost:5000/scale-up
```

**Watch the dashboard.** A new node should appear. The consistent hashing ring will rebalance.

### Challenge 3: Thundering Herd Prevention
1. Kill 2 nodes rapidly
2. Watch the client retry with exponential backoff + jitter
3. Bring nodes back online
4. Notice gradual recovery (no stampede)

---

## 🎓 The Graduation Challenge

When you've successfully:
- ✅ Kept writes succeeding while killing nodes
- ✅ Observed automatic failover to healthy nodes
- ✅ Scaled up the cluster dynamically
- ✅ Watched the system recover gracefully

Hit the secret endpoint:
```bash
curl http://localhost:5000/graduate
```

---

## 📚 The Real Incident

### AWS US-East-1 Collapse (October 20, 2025)

This module exists because of what happened that day:

1. **A single DNS record deletion** in DynamoDB triggered a cascade
2. **Retry storms** from millions of SDK clients overwhelmed EC2's control plane
3. **Health check failures** at the NLB layer amplified the problem
4. **15+ hours of downtime** affecting Snapchat, Fortnite, and countless applications

The systems that survived had:
- Multi-region redundancy
- Circuit breakers on client SDKs
- Jitter in retry logic
- Quorum-based writes that tolerated partial failures

**You just built all of that.**

---

## 🏆 Victory Condition

Your system is "production-ready" when:
1. The unified dashboard shows all nodes green
2. Writes succeed even when 1 of 3 nodes is dead
3. Reads automatically failover to healthy replicas
4. Scale-up adds capacity without downtime
5. You've earned your graduation ASCII art

Good luck, Distributed Systems Engineer. 🚀
