# Module 1: Nodes & RPC

## Goal
Understand how distributed systems are just processes talking over a network.

## Key Concepts
- **Node**: A process listening on a port
- **RPC**: Remote Procedure Call (HTTP in our case)
- **Serialization**: JSON for data exchange

## Files
- `node.py`: The server that stores data
- `client.py`: The client that talks to nodes

## Exercise

### 1. Start Multiple Nodes
Open 3 terminal windows and run:
```bash
python3 workshop_materials/01_nodes/node.py --port 5001 --id 1
python3 workshop_materials/01_nodes/node.py --port 5002 --id 2
python3 workshop_materials/01_nodes/node.py --port 5003 --id 3
```

### 2. Test Manually
```bash
# Check health
curl http://localhost:5001/health

# Store data
curl -X POST http://localhost:5001/data \
  -H "Content-Type: application/json" \
  -d '{"key": "user_123", "value": "Alice"}'

# Retrieve data
curl http://localhost:5001/data/user_123
```

### 3. Run the Client
```bash
python3 workshop_materials/01_nodes/client.py
```

## Challenge
Modify `client.py` to implement **Round Robin** load balancing instead of always hitting Node 1.
