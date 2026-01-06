# Module 1: Nodes & RPC

## Goal
Understand how distributed systems are just processes talking over a network, and how they behave under load.

## Key Concepts
- **Node**: A process listening on a port.
- **RPC**: Remote Procedure Call (HTTP in our case).
- **Serialization**: JSON for data exchange.
- **Vertical Scaling**: Adding more power (workers) to a single node.
- **Horizontal Scaling**: Adding more nodes to handle traffic.

## Files
- `node.py`: The server that stores data. Now supports load simulation.
- `client.py`: The client that talks to nodes. Now supports concurrent load testing.

## Usage

### 1. Basic Node
Start a simple node:
```bash
python3 workshop_materials/01_nodes/node.py --port 5001 --id 1
```

### 2. "Heavy" Node (Simulate CPU Load)
Start a node that performs heavy calculation (Fibonacci) for every data request:
```bash
# --load-factor 35 means calculate fib(35) for every request
python3 workshop_materials/01_nodes/node.py --port 5002 --id 2 --load-factor 35
```

### 3. Vertically Scaled Node (Multiple Workers)
To run with multiple worker processes (e.g., 10):
```bash
python3 workshop_materials/01_nodes/node.py --port 5002 --workers 10 --load-factor 35
```

### 4. Concurrent Client
Run the client to flood a node with requests:
```bash
# --concurrent 5: Fire 5 requests at once
# --target ...: Focus fire on a specific node
python3 workshop_materials/01_nodes/client.py --concurrent 5 --target http://localhost:5002
```

## Challenge
1.  **Crash a Node**: Use the concurrent client to make the Single-Worker node unresponsive ("Noisy Neighbor").
2.  **Scale It**: Restart with `--workers 10` and see the difference.
3.  **Break It Again**: Increase concurrency until even 10 workers can't keep up.
