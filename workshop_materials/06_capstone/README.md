# Hour 6: The Capstone - Surviving the Chaos 🌪️

## The Challenge
Welcome to the final hour. You have built:
1. Nodes that can run independently.
2. A Sharding Router to distribute keys.
3. A Quorum Client to read/write reliably.

Now, we break it.

## The Goal
Keep your `client.py` running and successfully writing/reading data while the "Chaos Script" randomly kills your nodes.

## Instructions

### 1. Setup the Cluster
Start 3 Nodes and your Chaos Monkey.
```bash
# Terminal 1
python3 workshop_materials/01_nodes/node.py --port 5001 --id 1
# ... run nodes 2 & 3 similarly ...

# Terminal 2 (The Villain)
python3 workshop_materials/chaos/kill_script.py
```

### 2. Implement "Resilient Client"
Modify your `client.py` to combine all skills:
- **Discovery**: If a node connection fails, mark it as `DOWN` in your local list.
- **Routing**: Use `ConsistentHashing` to find the *primary* node for a key.
- **Replication**: If Primary is down, try the *next* node in the ring.
- **Quorums**: Ensure you get `W=2` acks before saying "Success".

### 3. Victory Condition
Your client prints: 
`✅ Write Success (Key: user_123)` 
...even when `kill_script.py` prints:
`🔫 Killing process 12345`

Good luck!
