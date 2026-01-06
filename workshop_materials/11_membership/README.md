# Module 11: Service Discovery & Heartbeats

In a large-scale system, you can't hardcode IP addresses. Machines come and go, they crash, and they scale out. How do nodes find each other?

### Service Discovery
Nodes register themselves with a central **Registry** (like HashiCorp Consul, Netflix Eureka, or Zookeeper). When a client wants to talk to a node, it asks the Registry: "Who is alive right now?".

### Heartbeats
How does the Registry know if a node is *still* alive? The node must send a "Heartbeat" (a small ping) every few seconds. If the Registry doesn't hear from a node for a while, it marks it as dead and removes it from the list.

### How to Run

1. **Start the Registry**:
   ```bash
   python3 workshop_materials/11_membership/registry.py --port 5000
   ```

2. **Run the Visualizer**:
   ```bash
   python3 workshop_materials/11_membership/visualize_membership.py
   ```

3. **Start Multiple Nodes** (in separate terminals):
   ```bash
   python3 workshop_materials/11_membership/heartbeat_node.py --port 6001 --id node-alpha
   python3 workshop_materials/11_membership/heartbeat_node.py --port 6002 --id node-beta
   ```

### What to Observe
- Watch the Visualizer. You'll see nodes appear as soon as they start.
- The "Last Seen" timer should stay low (Resetting every 2 seconds).
- Kill `node-alpha` (Ctrl+C). The timer will climb until it hits 5 seconds, then the Registry will **prune** it. 💀
