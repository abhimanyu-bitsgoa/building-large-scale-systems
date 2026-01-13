# Distributed Systems Workshop: Instructor's Manual

> **Target Audience:** College students with no prior distributed systems experience  
> **Duration:** 4-6 hours (can be split across 2 days)  
> **Required:** Docker, terminal access, basic Python knowledge

---

## 📋 Workshop Overview

### Core Track (4 hours) — Must Cover
| Module | Topic | Duration | Type |
|--------|-------|----------|------|
| 01 | Nodes & RPC | 45 min | Hands-on |
| 02 | Load Balancing & Rate Limiting | 30 min | Hands-on |
| 03 | Sharding & Consistent Hashing | 45 min | Hands-on |
| 05 | Quorums & Availability | 30 min | Hands-on |
| 07 | Gossip Protocol | 20 min | Demo + Challenge |
| 09 | Circuit Breaker | 20 min | Demo + Challenge |
| 23 | Resilient System (Capstone) | 60 min | Hands-on |

### Extended Track (Optional) — Self-Study
Modules 08 (Consensus), 10-22 (advanced patterns)

---

## 🕐 Suggested Schedule

### Day 1 (3 hours)
| Time | Module | Activity |
|------|--------|----------|
| 0:00-0:15 | Setup | Docker, verify environment |
| 0:15-1:00 | **Module 01** | Nodes & Scaling |
| 1:00-1:30 | **Module 02** | Load Balancing |
| 1:30-1:45 | ☕ Break | |
| 1:45-2:30 | **Module 03** | Sharding |
| 2:30-3:00 | **Module 05** | Quorums |

### Day 2 (3 hours)  
| Time | Module | Activity |
|------|--------|----------|
| 0:00-0:20 | **Module 07** | Gossip (Demo) |
| 0:20-0:40 | **Module 09** | Circuit Breaker (Demo) |
| 0:40-0:55 | ☕ Break | |
| 0:55-2:00 | **Module 23** | Capstone Challenge |
| 2:00-2:30 | Wrap-up | Q&A, Further Reading |

---

## 🚀 Prerequisites Setup

```bash
cd /path/to/building-large-scale-systems
docker-compose up -d --build
docker-compose exec workshop bash
```

**✅ Checkpoint:** All students should see `/workspace` prompt inside container.

---

## Module 01: Nodes & RPC
**Duration: 45 minutes**

### 🎯 Learning Goals
- Understand that distributed systems = processes talking over a network
- Experience why vertical scaling has limits
- See the need for horizontal scaling

### 🗣️ Teaching Notes

**Opening Hook (2 min):**
> "Imagine your startup just went viral on HackerNews. Your single server is melting. What do you do?"

**Key Concepts to Emphasize:**
- A "node" is just a process on a port
- HTTP is our RPC mechanism (Remote Procedure Call)
- The GIL (Global Interpreter Lock) limits Python's single-process throughput

### 📝 Exact Commands

**Step 1: Start 3 Nodes** (3 terminals)
```bash
# Terminal 1
python3 workshop_materials/01_nodes/node.py --port 5001 --id 1

# Terminal 2
python3 workshop_materials/01_nodes/node.py --port 5002 --id 2

# Terminal 3
python3 workshop_materials/01_nodes/node.py --port 5003 --id 3
```

**Step 2: Test Manually**
```bash
curl http://localhost:5001/health
curl -X POST http://localhost:5001/data -H "Content-Type: application/json" -d '{"key": "user_123", "value": "Alice"}'
curl http://localhost:5001/data/user_123
```

**✅ Checkpoint:** Students see `{"status": "stored", "node_id": 1, ...}`

**Step 3: The Scaling Journey**

**Phase 1 — Break a Single Node:**
```bash
# Terminal 1 (restart with load)
python3 workshop_materials/01_nodes/node.py --port 5002 --id 2 --load-factor 35

# Terminal 2 (flood it)
python3 workshop_materials/01_nodes/client.py --concurrent 5 --target http://localhost:5002
```

**🗣️ Discussion Prompt:** *"Why is latency so high? What's happening inside the node?"*

**Phase 2 — Vertical Scaling:**
```bash
# Restart with workers
python3 workshop_materials/01_nodes/node.py --port 5002 --id 2 --load-factor 35 --workers 10

# Flood again
python3 workshop_materials/01_nodes/client.py --concurrent 5 --target http://localhost:5002
```

**✅ Checkpoint:** Latency drops significantly.

**Phase 3 — Hit the Limit:**
```bash
python3 workshop_materials/01_nodes/client.py --concurrent 20 --target http://localhost:5002
```

**🗣️ Discussion Prompt:** *"10 workers can't handle 20 requests. What's our next option?"*

**Phase 4 — Horizontal Scaling:**
```bash
# Distribute across all 3 nodes
python3 workshop_materials/01_nodes/client.py --concurrent 20
```

**🎓 Key Takeaway:** We need a Load Balancer (Module 2)!

---

## Module 02: Load Balancing & Rate Limiting
**Duration: 30 minutes**

### 🎯 Learning Goals
- Understand traffic distribution strategies
- Learn rate limiting as protection against abuse

### 🗣️ Teaching Notes

**Opening Hook:**
> "A single customer is sending 10x more requests than everyone else. They're about to crash your system. What do you do?"

**Real-World Incident:** Cloudflare Aug 2025 — one customer saturated peering links for 3 hours.

### 📝 Exact Commands

**Step 1: Load Balancing Visualization**
```bash
# Ensure 3 nodes are running from Module 1, then:
python3 workshop_materials/02_networking/visualize_load_balance.py
```

**✅ Checkpoint:** ASCII bar chart shows traffic distributed across nodes.

**Step 2: Rate Limiting Demo**
```bash
python3 workshop_materials/02_networking/visualize_rate_limit.py
```

**🗣️ Discussion Prompt:** *"What's the difference between 200 OK and 429 Too Many Requests?"*

---

## Module 03: Sharding & Consistent Hashing
**Duration: 45 minutes**

### 🎯 Learning Goals
- Understand why data must be partitioned
- Compare modulo hashing vs. consistent hashing
- See why consistent hashing minimizes data movement

### 🗣️ Teaching Notes

**Opening Hook:**
> "Your database has 1 billion users. You need to add a 4th server. How many users need to move?"

**Answer Preview:** With modulo hashing: ~75%. With consistent hashing: ~25%.

### 📝 Exact Commands

**Step 1: Visualization (The "Aha!" Moment)**
```bash
python3 workshop_materials/03_sharding/visualize_rebalancing.py
```

**✅ Checkpoint:** Students see the dramatic difference in keys moved.

**Step 2: Router Demo**
```bash
python3 workshop_materials/03_sharding/router.py
```

**Step 3: Swap Strategies (Hands-on)**

Have students edit `workshop_materials/03_sharding/router.py`:
```python
# Comment line 7, uncomment line 8
self.strategy = ConsistentHashingStrategy(self.nodes)
```

Then run again and add a 4th node.

**🎓 Key Takeaway:** DynamoDB, Cassandra, and Redis Cluster all use consistent hashing.

---

## Module 05: Quorums & Availability
**Duration: 30 minutes**

### 🎯 Learning Goals
- Understand R + W > N formula
- See how quorum enables fault tolerance
- Recognize the CAP theorem trade-off

### 🗣️ Teaching Notes

**Opening Hook:**
> "You have 3 replicas. 2 just died. Can you still serve reads? Can you still serve writes?"

### 📝 Exact Commands

**Step 1: Simulation**
```bash
python3 workshop_materials/05_availability/visualize_availability.py
```

**✅ Checkpoint:**
- 3/3 nodes: SUCCESS
- 2/3 nodes: SUCCESS (quorum met)
- 1/3 nodes: FAILURE

**🗣️ Discussion Prompt:** *"What if you set R=1 and W=1? What's the trade-off?"*

**Real-World Incident:** XRP Ledger Feb 2025 — validators drifted, couldn't meet quorum, 1-hour halt.

---

## Module 07: Gossip Protocol
**Duration: 20 minutes (Demo + Micro-Challenge)**

### 🎯 Learning Goals
- Understand decentralized information propagation
- See eventual consistency in action

### 📝 Exact Commands

**Step 1: Start 4 Gossip Nodes**
```bash
python3 workshop_materials/07_gossip/gossip_node.py --port 7001 --id 1 --neighbors 7002,7003,7004
python3 workshop_materials/07_gossip/gossip_node.py --port 7002 --id 2 --neighbors 7001,7003,7004
python3 workshop_materials/07_gossip/gossip_node.py --port 7003 --id 3 --neighbors 7001,7002,7004
python3 workshop_materials/07_gossip/gossip_node.py --port 7004 --id 4 --neighbors 7001,7002,7003
```

**Step 2: Visualizer**
```bash
python3 workshop_materials/07_gossip/visualize_gossip.py
```

**Step 3: Inject Update**
```bash
curl -X POST http://localhost:7001/update
```

**✅ Checkpoint:** Watch update propagate to all nodes within seconds.

### 🎮 Micro-Challenge
> "Kill Node 3 (Ctrl+C). Update Node 1. How long until Node 4 gets the update? Does it still work?"

---

## Module 09: Circuit Breaker
**Duration: 20 minutes (Demo + Micro-Challenge)**

### 🎯 Learning Goals
- Understand fast-fail vs. slow timeout
- See the CLOSED → OPEN → HALF-OPEN state machine

### 📝 Exact Commands

**Step 1: Start Flaky Server**
```bash
python3 workshop_materials/09_patterns/flaky_server.py
```

**Step 2: Visualizer**
```bash
cd workshop_materials/09_patterns
python3 visualize_breaker.py
```

**Step 3: Trigger Failure**
```bash
curl -X POST http://localhost:9001/fail
```

**✅ Checkpoint:** Circuit opens after 3 failures.

**Step 4: Recover**
```bash
curl -X POST http://localhost:9001/recover
```

### 🎮 Micro-Challenge
> "Before triggering /fail, predict: How many requests will fail before the circuit opens? Time yourself."

---

## Module 23: Resilient System (Grand Capstone)
**Duration: 60 minutes**

### 🎯 Learning Goals
- Combine all concepts into a working system
- Experience chaos engineering firsthand
- Celebrate with the graduation easter egg!

### 📝 Exact Commands

**Step 1: Start Registry**
```bash
python3 workshop_materials/23_resilient_system/registry.py
```

**Step 2: Start 3 Nodes** (3 terminals)
```bash
python3 workshop_materials/23_resilient_system/resilient_node.py --port 5001 --id node-1
python3 workshop_materials/23_resilient_system/resilient_node.py --port 5002 --id node-2
python3 workshop_materials/23_resilient_system/resilient_node.py --port 5003 --id node-3
```

**Step 3: Dashboard**
```bash
python3 workshop_materials/23_resilient_system/unified_dashboard.py
```

**✅ Checkpoint:** All 3 nodes show green in dashboard.

**Step 4: Write Data**
```bash
curl -X POST http://localhost:5000/data -H "Content-Type: application/json" -d '{"key":"user:alice","value":"Alice"}'
```

**Step 5: Chaos Testing**
```bash
# Kill a node
curl -X POST http://localhost:5000/kill/node-2

# Try another write - should still work!
curl -X POST http://localhost:5000/data -H "Content-Type: application/json" -d '{"key":"user:bob","value":"Bob"}'
```

**Step 6: Scale Up**
```bash
curl -X POST http://localhost:5000/scale-up
```

**Step 7: Graduation!**
```bash
curl http://localhost:5000/graduate
```

🎉 **Victory Condition:** Students see the graduation ASCII art!

---

## 🛑 Troubleshooting Guide

| Problem | Solution |
|---------|----------|
| "ModuleNotFoundError" | Run `pip3 install -r requirements.txt` inside container |
| "Address already in use" | Kill existing process: `lsof -i :5001` then `kill <PID>` |
| Dashboard shows no nodes | Make sure nodes are running before dashboard |
| "Connection refused" | Check that registry is running on port 5000 |

---

## 📖 Further Reading (Extended Track)

| Module | Topic | Best For |
|--------|-------|----------|
| 10 | Thundering Herd | Understanding Roblox 2021 outage |
| 13 | Replication Lag | Database consistency issues |
| 14 | Distributed Locking | Preventing double-booking |
| 17 | Saga Pattern | Microservices transactions |
| 21 | CRDTs | Collaborative editing (Google Docs) |
| 22 | 2-Phase Commit | Strict transactional consistency |

---

## Quick Reference: Port Mapping

| Service | Inside Docker | From Host Mac |
|---------|---------------|---------------|
| Node 1 | localhost:5001 | localhost:8001 |
| Node 2 | localhost:5002 | localhost:8002 |
| Node 3 | localhost:5003 | localhost:8003 |
| Registry | localhost:5000 | localhost:8000 |

---

## 🎓 Closing Script

> "Today you built a distributed system from scratch. You saw why single servers fail. You learned how load balancing, consistent hashing, and quorums work. And you built a system that survives chaos.
> 
> The real world is messy. AWS goes down. DNS records get deleted. Retry storms overwhelm control planes. But now you know the patterns that make systems resilient.
> 
> Go build things that don't break. 🚀"

---

*Happy Teaching!*
