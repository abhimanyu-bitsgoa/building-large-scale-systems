# Module 1: Nodes & RPC

## 🎯 The Scenario

Your startup just got featured on HackerNews. Traffic is 100x normal. Your single server returns **502 Bad Gateway**. Customers are rage-tweeting. The CEO is panicking.

*What do you do?*

---

## 🧠 Pause and Think

Before looking at the solution, consider:
1. Why can't one server handle unlimited requests?
2. If you "buy a bigger server," what limits will you eventually hit?
3. What's the alternative to bigger servers?

---

## 💡 The Concepts

### What is a Node?
A **node** is simply a process listening on a network port. In our workshop, it's a Python FastAPI server. In production, it could be a container, a VM, or a physical machine.

### Remote Procedure Call (RPC)
When one process calls a function on another process over the network, that's RPC. We use HTTP + JSON, but gRPC, Thrift, or raw TCP are also common.

### Vertical vs. Horizontal Scaling
| Strategy | What it means | Limits |
|----------|---------------|--------|
| **Vertical** | Add more CPU/RAM to one server | Hardware max, cost, single point of failure |
| **Horizontal** | Add more servers | Need load balancing, data consistency |

---

## 🚀 How to Run

### Step 1: Start 3 Nodes
Open 3 terminal windows:
```bash
# Terminal 1
python3 workshop_materials/01_nodes/node.py --port 5001 --id 1

# Terminal 2
python3 workshop_materials/01_nodes/node.py --port 5002 --id 2

# Terminal 3
python3 workshop_materials/01_nodes/node.py --port 5003 --id 3
```

### Step 2: Test Manually
```bash
# Health check
curl http://localhost:5001/health

# Store data
curl -X POST http://localhost:5001/data \
  -H "Content-Type: application/json" \
  -d '{"key": "user_123", "value": "Alice"}'

# Retrieve data
curl http://localhost:5001/data/user_123
```

### Step 3: Run the Client
```bash
python3 workshop_materials/01_nodes/client.py
```

---

## 🔥 The Scaling Journey

### Phase 1: Overwhelm a Single Node
```bash
# Start a "heavy" node (simulates CPU-intensive work)
python3 workshop_materials/01_nodes/node.py --port 5002 --id 2 --load-factor 35

# Flood it with concurrent requests
python3 workshop_materials/01_nodes/client.py --concurrent 5 --target http://localhost:5002
```

**What you'll see:** Latency spikes to 2000ms+. The node can't keep up.

### Phase 2: Vertical Scaling
```bash
# Restart with 10 worker processes
python3 workshop_materials/01_nodes/node.py --port 5002 --id 2 --load-factor 35 --workers 10

# Same flood
python3 workshop_materials/01_nodes/client.py --concurrent 5 --target http://localhost:5002
```

**What you'll see:** Latency drops! 10 processes handle 5 requests in parallel.

### Phase 3: Hit the Limit
```bash
# Increase concurrency beyond worker count
python3 workshop_materials/01_nodes/client.py --concurrent 20 --target http://localhost:5002
```

**What you'll see:** Latency spikes again. 10 workers can't handle 20 concurrent requests.

### Phase 4: Horizontal Scaling
```bash
# Use all 3 nodes
python3 workshop_materials/01_nodes/client.py --concurrent 20
```

**What you'll see:** Requests distributed across nodes. Fast nodes respond quickly; slow nodes still lag.

**Key Insight:** We need a *Load Balancer* to intelligently route around slow nodes!

---

## 📚 The Real Incident

### AWS US-East-1 Outage (October 2025)

On October 20, 2025, a single DNS configuration error triggered a 15-hour cascade:

1. **Initial failure:** An automated system deleted a critical DNS record for DynamoDB
2. **Retry storm:** Millions of AWS SDK clients started retrying simultaneously
3. **EC2 control plane collapse:** The retry flood exceeded EC2's capacity to launch new instances
4. **Cascading failure:** EC2 failures broke networking, which broke health checks, which broke load balancers

The system that was supposed to heal itself became the source of the outage.

**Lesson:** Vertical scaling (bigger EC2 instances) wouldn't have helped. The system needed horizontal resilience with proper rate limiting and circuit breakers.

---

## 🏆 Challenge

1. Use the client to crash a single-worker node (latency > 5000ms)
2. Scale vertically until it recovers
3. Find the concurrency level that breaks even 10 workers
4. Explain why horizontal scaling is the only way forward
