# Module 07: Gossip Protocol

How do nodes in a huge cluster (like Amazon S3 or DynamoDB) know about each other without a central "Master" server? 

They **Gossip**.

### The Concept
Gossip (or Epidemic) protocols are inspired by how rumors or diseases spread in a population. 
1. A node picks a random neighbor.
2. It shares what it knows.
3. The neighbor incorporates that knowledge and shares it with another random neighbor.

This is highly scalable, fault-tolerant, and eventually consistent.

### How to Run

1. **Start 4 Gossip Nodes** (in separate terminals or look at the visualizer's port list):
   ```bash
   python3 workshop_materials/07_gossip/gossip_node.py --port 7001 --id 1 --neighbors 7002,7003,7004
   python3 workshop_materials/07_gossip/gossip_node.py --port 7002 --id 2 --neighbors 7001,7003,7004
   python3 workshop_materials/07_gossip/gossip_node.py --port 7003 --id 3 --neighbors 7001,7002,7004
   python3 workshop_materials/07_gossip/gossip_node.py --port 7004 --id 4 --neighbors 7001,7002,7003
   ```

2. **Run the Visualizer**:
   ```bash
   python3 workshop_materials/07_gossip/visualize_gossip.py
   ```

3. **Inject a Change**:
   Pick any node and update its version:
   ```bash
   curl -X POST http://localhost:7001/update
   ```

### What to Observe
- Watch the Visualizer. Initially, only Node 1 has `1: 1`. 
- Over the next few seconds, you will see `1: 1` appear on Node 2, Node 3, and finally Node 4.
- If you kill a node (Ctrl+C) and update another one, the cluster continues to work. When you restart the killed node, it will "catch up" via gossip!
