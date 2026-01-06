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

### Step 4: Demonstrate "The Noisy Neighbor" (CPU Load)
Now, let's simulate a busy server to understand why we need load balancing.

**1. Start a "Slow" Node:**
```bash
# In a new terminal
python3 workshop_materials/01_nodes/node.py --port 5002 --id 2 --load-factor 30
```
*(This tells the node to calculate the 30th Fibonacci number for every data request)*

**2. Send a Request & Watch Latency:**
```bash
# In another terminal, count the time
time curl -X POST http://localhost:5002/data -d '{"key":"k","value":"v"}'
```
You should see a noticeable delay (e.g., 0.1s - 0.5s) compared to Node 1.

**3. Check Active Requests:**
```bash
curl http://localhost:5002/stats
```
If you hit this while a heavy request is running, you'll see `"active_requests": 1`.

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
