# Workshop Execution Guide: Step-by-Step Instructions

This guide provides **exact commands** to run each module of the Distributed Systems workshop.

---

## Prerequisites

1. **Start Docker Environment**:
```bash
cd /Users/aronzx/Documents/code/building-large-scale-systems
docker-compose up -d --build
docker-compose exec workshop bash
```

You should now be inside the container at `/workspace`.

---

## Module 1: Nodes & RPC

### Step 1: Start 3 Nodes
Open **3 separate terminal windows/tabs**, and in each one, enter the container and run:

**Terminal 1 (Node 1):**
```bash
docker-compose exec workshop bash
python3 workshop_materials/01_nodes/node.py --port 5001 --id 1
```

**Terminal 2 (Node 2):**
```bash
docker-compose exec workshop bash
python3 workshop_materials/01_nodes/node.py --port 5002 --id 2
```

**Terminal 3 (Node 3):**
```bash
docker-compose exec workshop bash
python3 workshop_materials/01_nodes/node.py --port 5003 --id 3
```

### Step 2: Test Manually (New Terminal)
```bash
docker-compose exec workshop bash

# Check health
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

**Expected Output**: Continuous health check requests hitting Node 1.

### Step 4: The Scaling Journey 🚀
In this step, we will intentionally break a single node to understand the limits of **Vertical Scaling** and the need for **Horizontal Scaling**.

#### Phase 1: The "Noisy Neighbor" (Single Process)
First, let's see what happens when a single node process gets overwhelmed.

1.  **Start a Single-Worker Node** (Simulating a standard Python app):
    ```bash
    # Terminal 1
    # --id 2: We use Node 2 as our test subject
    # --load-factor 35: High CPU load (Fibonacci) per request
    python3 workshop_materials/01_nodes/node.py --port 5002 --id 2 --load-factor 35
    ```

2.  **Flood it with Requests:**
    ```bash
    # Terminal 2 (Client)
    # Fire 5 concurrent requests at Node 2
    python3 workshop_materials/01_nodes/client.py --concurrent 5 --target http://localhost:5002
    ```

    **Observation**:
    - You will see high latency (e.g., `Latency: 2000ms+`).
    - `Active: 5`: Requests pile up because a single process can only handle one CPU-heavy task at a time (GIL).

#### Phase 2: Vertical Scaling (Bigger Server)
Let's "buy a bigger server" by adding more CPU cores (Processes).

1.  **Restart Node 2 with 10 Workers**:
    ```bash
    # Terminal 1 (Ctrl+C first)
    # We use workers=10 to scale vertically
    python3 workshop_materials/01_nodes/node.py --port 5002 --id 2 --load-factor 35 --workers 10
    ```

2.  **Flood it Again:**
    ```bash
    # Terminal 2
    python3 workshop_materials/01_nodes/client.py --concurrent 5 --target http://localhost:5002
    ```

    **Observation**:
    - **Latency Drops**: Responses are much faster!
    - **Why?**: 10 separate processes can handle 5 requests *in parallel*. Use `Active` stats to see them clearing instantly.

#### Phase 3: The Limit (Overload Again)
Vertical scaling has limits. What if we get *too much* traffic?

1.  **Flood with 20 concurrent requests**:
    ```bash
    # Terminal 2
    python3 workshop_materials/01_nodes/client.py --concurrent 20 --target http://localhost:5002
    ```

    **Observation**:
    - Latency spikes again! 10 workers cannot handle 20 heavy requests simultaneously. Queueing returns.

#### Phase 4: Horizontal Scaling (Load Balancing)
The solution is to add **More Nodes**, not just bigger ones.

1.  **Start Node 1 & Node 3** (Normal, no load factor):
    ```bash
    # Terminal 3
    python3 workshop_materials/01_nodes/node.py --port 5001 --id 1
    
    # Terminal 4
    python3 workshop_materials/01_nodes/node.py --port 5003 --id 3
    ```

2.  **Run Client in Round-Robin Mode**:
    ```bash
    # Terminal 2
    # Remove --target to use all 3 nodes
    python3 workshop_materials/01_nodes/client.py --concurrent 20
    ```

    **Observation**:
    - Requests distributed to Node 1 and 3 are **FAST**.
    - Requests hitting Node 2 are **SLOW**.
    - **Lesson**: We need a Load Balancer (Module 2) to intelligently route around the slow node!

---

## Module 2A: Load Balancing Visualization

### Step 1: Ensure 3 Nodes are Running
(Use nodes from Module 1, or restart them if needed)

### Step 2: Run the Visualizer
```bash
docker-compose exec workshop bash
python3 workshop_materials/02_networking/visualize_load_balance.py
```

**Expected Output**: A live ASCII bar chart showing request distribution across the 3 nodes.

**To Stop**: Press `Ctrl+C`.

---

## Module 2B: Rate Limiting

### Step 1: Start a Rate-Limited Node

**Edit `node.py` temporarily** (or create a copy):
```python
# Add this import at the top
import sys
sys.path.append('/workspace')
from workshop_materials.networking.rate_limit_middleware import RateLimitMiddleware

# Add this BEFORE uvicorn.run()
app.add_middleware(RateLimitMiddleware, requests_per_second=5)
```

**Run the modified node:**
```bash
python3 workshop_materials/01_nodes/node.py --port 5001 --id 1
```

### Step 2: Run the Rate Limit Visualizer
```bash
# In another terminal
docker-compose exec workshop bash
python3 workshop_materials/02_networking/visualize_rate_limit.py
```

**Expected Output**:
- **Good User**: Gets 200 responses
- **Bad Actor**: Gets 429 "Too Many Requests" errors

---

## Module 3 & 4: Sharding & Consistent Hashing

### Step 1: Run the Rebalancing Visualization
```bash
docker-compose exec workshop bash
python3 workshop_materials/03_sharding/visualize_rebalancing.py
```

**Expected Output**:
```
🧪 Testing Strategy: MODULO
Keys Moved:   746/1000
Percentage:   74.6%
⚠️ HIGH IMPACT!

🧪 Testing Strategy: CONSISTENT_HASHING
Keys Moved:   246/1000
Percentage:   24.6%
✅ LOW IMPACT!
```

### Step 2: Test the Router
```bash
python3 workshop_materials/03_sharding/router.py
```

**Expected Output**:
```
Key 'user_123' maps to Node B
```

### Step 3: Swap Strategies
Edit `workshop_materials/03_sharding/router.py`:
```python
# Line 7: Comment out
# self.strategy = ModuloStrategy()

# Line 8: Uncomment
self.strategy = ConsistentHashingStrategy(self.nodes)
```

Run again:
```bash
python3 workshop_materials/03_sharding/router.py
```

---

## Module 5: Quorums & Availability

### Step 1: Run the Availability Simulation
```bash
docker-compose exec workshop bash
python3 workshop_materials/05_availability/visualize_availability.py
```

**Expected Output**:
```
--- SYSTEM HEALTHY ---
Result: SUCCESS. Got Version 1 from ['Node 1', 'Node 2', 'Node 3']

--- 💥 DISASTER: KILLING NODE 2 ---
Result: SUCCESS (Quorum Met). Got Version 1 from ['Node 1', 'Node 3']

--- 💥 CATASTROPHE: KILLING NODE 3 ---
Result: FAILURE. Only 1/3 nodes alive. R=2 not met.
```

---

## Module 6: The Capstone Challenge

### Step 1: Start 3 Nodes
(Same as Module 1)

```bash
# Terminal 1
python3 workshop_materials/01_nodes/node.py --port 5001 --id 1

# Terminal 2
python3 workshop_materials/01_nodes/node.py --port 5002 --id 2

# Terminal 3
python3 workshop_materials/01_nodes/node.py --port 5003 --id 3
```

### Step 2: Start the Chaos Script
```bash
# Terminal 4
docker-compose exec workshop bash
python3 workshop_materials/chaos/kill_script.py
```

**Expected Output**: Every 10 seconds, it will randomly kill one node.

### Step 3: Implement and Run the Resilient Client

**TODO for Students**: Edit `workshop_materials/06_capstone/capstone_client.py` and implement:
- `write_quorum()`
- `read_quorum()`

Once implemented, run:
```bash
# Terminal 5
python3 workshop_materials/06_capstone/capstone_client.py
```

**Victory Condition**: The client prints "✅ Write Success" even while nodes are being killed.

---

## Module 07: Gossip Protocol

### Step 1: Start 4 Nodes
```bash
python3 workshop_materials/07_gossip/gossip_node.py --port 7001 --id 1 --neighbors 7002,7003,7004
python3 workshop_materials/07_gossip/gossip_node.py --port 7002 --id 2 --neighbors 7001,7003,7004
python3 workshop_materials/07_gossip/gossip_node.py --port 7003 --id 3 --neighbors 7001,7002,7004
python3 workshop_materials/07_gossip/gossip_node.py --port 7004 --id 4 --neighbors 7001,7002,7003
```

### Step 2: Run Visualizer
```bash
python3 workshop_materials/07_gossip/visualize_gossip.py
```

### Step 3: Trigger Update
```bash
curl -X POST http://localhost:7001/update
```

---

## Module 08: Leader Election (Bully)

### Step 1: Start 3 Nodes
```bash
python3 workshop_materials/08_consensus/bully_node.py --port 8001 --id 1 --nodes 1:8001,2:8002,3:8003
python3 workshop_materials/08_consensus/bully_node.py --port 8002 --id 2 --nodes 1:8001,2:8002,3:8003
python3 workshop_materials/08_consensus/bully_node.py --port 8003 --id 3 --nodes 1:8001,2:8002,3:8003
```

### Step 2: Run Visualizer
```bash
python3 workshop_materials/08_consensus/visualize_election.py
```

---

## Module 09: Circuit Breaker

### Step 1: Start Flaky Server
```bash
python3 workshop_materials/09_patterns/flaky_server.py
```

### Step 2: Run Visualizer
```bash
cd workshop_materials/09_patterns
python3 visualize_breaker.py
```

### Step 3: Fail & Recover
```bash
curl -X POST http://localhost:9001/fail
curl -X POST http://localhost:9001/recover
```

---

## Module 10: Thundering Herd

### Step 1: Run Simulation
```bash
python3 workshop_materials/10_concurrency/cache_stampede.py
```

---

## Module 11: Service Discovery

### Step 1: Start Registry
```bash
python3 workshop_materials/11_membership/registry.py
```

### Step 2: Run Visualizer
```bash
python3 workshop_materials/11_membership/visualize_membership.py
```

### Step 3: Start Nodes
```bash
python3 workshop_materials/11_membership/heartbeat_node.py --port 6001 --id node1
python3 workshop_materials/11_membership/heartbeat_node.py --port 6002 --id node2
```

---

## Stopping Everything

```bash
# Exit all terminals with Ctrl+C

# Stop the Docker container
docker-compose down
```

---

## Quick Reference: Port Mapping

Since we're using Docker with port mapping:
- **Inside Container**: `localhost:5001`, `localhost:5002`, `localhost:5003`
- **From Your Mac (Host)**: `localhost:8001`, `localhost:8002`, `localhost:8003`

If you want to test from your Mac's browser or `curl`:
```bash
# From your Mac terminal (outside Docker)
curl http://localhost:8001/health
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "ModuleNotFoundError: No module named 'fastapi'" | Run `pip3 install -r requirements.txt` inside the container |
| "Address already in use" (port 5000) | Use ports 5001-5003 instead, or disable macOS AirPlay |
| Chaos script says "No nodes found" | Make sure nodes are running with `node.py` in their process name |
| Import errors for `sharding_lib` | Run scripts from the `/workspace` directory |

Happy Building! 🚀
