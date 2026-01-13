# Module 11: Service Discovery & Heartbeats

## 🎯 The Scenario

You have 100 servers. Servers crash, restart, scale up and down constantly.

Your load balancer needs to know: **Which servers are alive RIGHT NOW?**

*Do you hardcode a list of IP addresses? What happens when server 47 dies at 3am?*

---

## 🧠 Pause and Think

1. How does the load balancer know a server is still alive?
2. What's the difference between "server isn't responding" and "server is just slow"?
3. How quickly should you declare a server dead?

---

## 💡 The Concepts

### Service Discovery
Servers **register** themselves with a central Registry (like Consul, Eureka, or etcd). Clients query the Registry to find available servers.

### Heartbeats
Periodic "I'm alive" signals from servers to the Registry. If the Registry doesn't hear from a server for X seconds, it marks it dead.

```
Server → Registry: "I'm alive!" (every 2s)
Server → Registry: "I'm alive!" (every 2s)
Server → ❌ (crashed)
Registry: "No heartbeat for 5s... removing from pool"
```

### The Timeout Dilemma
- **Too short:** False positives. A slow server gets marked dead.
- **Too long:** Slow detection. Traffic keeps going to a dead server.

---

## 🚀 How to Run

### Step 1: Start the Registry
```bash
python3 workshop_materials/11_membership/registry.py --port 5000
```

### Step 2: Run the Visualizer
```bash
python3 workshop_materials/11_membership/visualize_membership.py
```

### Step 3: Start Nodes
```bash
python3 workshop_materials/11_membership/heartbeat_node.py --port 6001 --id node-alpha
python3 workshop_materials/11_membership/heartbeat_node.py --port 6002 --id node-beta
```

**What you'll see:**
- Nodes appear in the visualizer when they start
- "Last Seen" resets every 2 seconds (heartbeat)

### Step 4: Kill a Node
Press `Ctrl+C` on `node-alpha`. Watch the visualizer:
- "Last Seen" climbs: 2s... 3s... 4s... 5s...
- Registry prunes the node. 💀

---

## 🎮 Micro-Challenge

1. Kill `node-alpha`
2. Time how long until it's pruned from the registry
3. **Question:** Is 5 seconds too long? Too short? What would you change for:
   - A video streaming service?
   - A stock trading platform?

---

## 📚 The Real Incident

### AWS — October 2025 (Health Check Cascade)

During the DynamoDB DNS outage, Network Load Balancers (NLB) couldn't reach their backend servers (because DNS was broken, not because servers were dead).

The health check logic:
1. Ping the server
2. No response → mark as unhealthy
3. Remove from pool

**Result:** Healthy servers were removed because the health check itself was broken.

This created a cascade:
- Fewer servers in the pool → more load on remaining servers
- More health check failures → more servers removed
- Until no servers were left

**Lesson:** Health checks have hard dependencies (DNS, network). If those dependencies fail, healthy servers look dead. Use **Phi Accrual Failure Detection** (probabilistic, not binary) for better accuracy.

---

## 🏆 Challenge

Implement **Phi Accrual Failure Detection**:

Instead of "no heartbeat for 5s = dead", calculate the probability of failure based on heartbeat history. A server that normally responds in 100ms but hasn't responded in 500ms is suspicious. One that normally takes 1s but is at 1.5s is probably fine.
