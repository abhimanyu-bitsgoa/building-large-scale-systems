# Module 5: Quorums & Replication

## Goal
Build fault-tolerant systems using the Quorum pattern.

## Key Concepts
- **Replication**: Storing data on multiple nodes
- **Quorum**: Majority agreement (R + W > N)
- **Read Repair**: Fixing stale data during reads
- **CAP Theorem**: You can't have perfect Consistency, Availability, AND Partition Tolerance

## Files
- `visualize_availability.py`: Conceptual demo of Quorum reads

## Exercise

### 1. Run the Simulation
```bash
python3 workshop_materials/05_availability/visualize_availability.py
```

**Expected Output:**
- System healthy: READ succeeds (3/3 nodes)
- Node 2 dies: READ still succeeds (2/3 ≥ quorum of 2)
- Node 3 dies: READ fails (1/3 < quorum of 2)

### 2. Implement Quorum Writes
In your `client.py`, add:
```python
def write_quorum(key, value, nodes, w=2):
    acks = 0
    for node_url in nodes:
        try:
            resp = requests.post(f"{node_url}/data", json={"key": key, "value": value})
            if resp.status_code == 200:
                acks += 1
        except:
            pass
    
    if acks >= w:
        return True  # Success
    else:
        raise Exception(f"Quorum not met: only {acks}/{w} nodes acked")
```

## Challenge
Implement **Read Repair**: When reading from a quorum, if nodes have different versions, update the stale ones.
