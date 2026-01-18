"""
Load Balancer with Pluggable Strategies

A standalone load balancer that demonstrates why Round Robin fails
with heterogeneous nodes (different capacities/workers).

Demo Flow:
1. Start nodes with different --workers or --load-factor
2. Run load_balancer.py with --strategy round_robin
3. Observe uneven latencies and overloaded slow nodes
4. Students implement LeastConnectionsStrategy to fix it
5. Re-run with --strategy least_connections

Usage:
    python load_balancer.py --port 8080 --nodes 5001,5002,5003 --strategy round_robin
"""

import uvicorn
from fastapi import FastAPI, Request
import httpx
import argparse
import time
from typing import List, Dict, Any
from collections import defaultdict
import asyncio

from middleware.strategies import LoadBalanceStrategy


# ═══════════════════════════════════════════════════════════════════
# LOAD BALANCING STRATEGIES
# ═══════════════════════════════════════════════════════════════════

class RoundRobinStrategy(LoadBalanceStrategy):
    """
    Round Robin Load Balancing (Complete Implementation)
    
    Cycles through nodes in order: Node1 → Node2 → Node3 → Node1 → ...
    
    ⚠️ PROBLEM: Ignores node capacity/load!
    - If Node1 has 1 worker and Node2 has 4 workers, Round Robin 
      still sends equal traffic to both.
    - This causes Node1 to become overloaded while Node2 is underutilized.
    """
    
    def __init__(self):
        self.current_index = 0
    
    def select_node(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the next node in round-robin order."""
        if not nodes:
            raise ValueError("No nodes available")
        
        node = nodes[self.current_index % len(nodes)]
        self.current_index += 1
        return node


class LeastConnectionsStrategy(LoadBalanceStrategy):
    """
    Least Connections Load Balancing
    
    📝 STUDENT EXERCISE: Implement the select_node() method
    
    How Least Connections works:
    ┌─────────────────────────────────────────────────────────────┐
    │  🔍 Track active connections to each node                  │
    │  📊 When a new request comes in, pick the node with        │
    │     the FEWEST active connections                          │
    │  ⚖️  This naturally balances load across different          │
    │     capacity nodes!                                         │
    └─────────────────────────────────────────────────────────────┘
    
    Example:
    - Node1 (1 worker): 5 active connections
    - Node2 (4 workers): 3 active connections  ← Choose this!
    - Node3 (1 worker): 8 active connections
    
    Why this works better:
    - Slow nodes naturally accumulate connections (requests take longer)
    - Fast nodes complete quickly, freeing up slots
    - New requests go to fast nodes more often
    """
    
    def __init__(self):
        # Track active connections per node
        # Format: {node_url: count}
        self.active_connections = defaultdict(int)
    
    def select_node(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select the node with the fewest active connections.
        
        ════════════════════════════════════════════════════════
        TODO: Implement the least connections algorithm
        
        Steps:
        1. If no nodes available, raise ValueError
        2. Find the node with minimum active_connections
        3. Return that node
        
        Hints:
        - Use self.active_connections[node["url"]] to get connection count
        - Use min() with a key function, or iterate to find minimum
        - Each node dict has a "url" field like "http://localhost:5001"
        ════════════════════════════════════════════════════════
        """
        # ─────────────────────────────────────────────────────
        # YOUR CODE HERE
        # ─────────────────────────────────────────────────────
        raise NotImplementedError(
            "Implement the least connections algorithm! "
            "See the docstring above for step-by-step instructions."
        )
    
    def on_request_start(self, node: Dict[str, Any]) -> None:
        """Called when sending a request to a node - increment counter."""
        self.active_connections[node["url"]] += 1
    
    def on_request_end(self, node: Dict[str, Any]) -> None:
        """Called when request completes - decrement counter."""
        self.active_connections[node["url"]] = max(0, self.active_connections[node["url"]] - 1)


# ═══════════════════════════════════════════════════════════════════
# LOAD BALANCER SERVER
# ═══════════════════════════════════════════════════════════════════

app = FastAPI()

# Global state
nodes: List[Dict[str, Any]] = []
strategy: LoadBalanceStrategy = None
stats = defaultdict(lambda: {"requests": 0, "total_latency": 0, "errors": 0})


@app.get("/")
def home():
    return {
        "service": "Load Balancer",
        "strategy": strategy.__class__.__name__,
        "nodes": [n["url"] for n in nodes]
    }


@app.get("/stats")
def get_stats():
    """Get load balancer statistics per node."""
    result = {}
    for node in nodes:
        url = node["url"]
        s = stats[url]
        avg_latency = s["total_latency"] / s["requests"] if s["requests"] > 0 else 0
        result[url] = {
            "requests": s["requests"],
            "avg_latency_ms": round(avg_latency * 1000, 2),
            "errors": s["errors"]
        }
    return result


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_request(path: str, request: Request):
    """
    Proxy all requests to backend nodes using the configured strategy.
    """
    global strategy, stats
    
    # Select a node using the strategy
    selected_node = strategy.select_node(nodes)
    node_url = selected_node["url"]
    target_url = f"{node_url}/{path}"
    
    # Track connection start
    strategy.on_request_start(selected_node)
    
    start_time = time.time()
    try:
        async with httpx.AsyncClient() as client:
            # Forward the request
            body = await request.body()
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=dict(request.headers),
                content=body,
                timeout=30.0
            )
            
            latency = time.time() - start_time
            stats[node_url]["requests"] += 1
            stats[node_url]["total_latency"] += latency
            
            # Return proxied response
            return {
                "proxied_from": node_url,
                "latency_ms": round(latency * 1000, 2),
                "status": response.status_code,
                "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
            }
    except Exception as e:
        stats[node_url]["errors"] += 1
        return {"error": str(e), "node": node_url}
    finally:
        strategy.on_request_end(selected_node)


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load Balancer with pluggable strategies")
    parser.add_argument("--port", type=int, default=8080, help="Load balancer port")
    parser.add_argument("--nodes", type=str, required=True, 
                        help="Comma-separated list of node ports (e.g., 5001,5002,5003)")
    parser.add_argument("--strategy", type=str, default="round_robin",
                        choices=["round_robin", "least_connections"],
                        help="Load balancing strategy")
    args = parser.parse_args()
    
    # Parse node ports
    node_ports = [int(p.strip()) for p in args.nodes.split(",")]
    nodes = [{"url": f"http://localhost:{port}", "port": port} for port in node_ports]
    
    # Select strategy
    if args.strategy == "round_robin":
        strategy = RoundRobinStrategy()
    elif args.strategy == "least_connections":
        strategy = LeastConnectionsStrategy()
    
    print(f"🔀 Load Balancer starting on port {args.port}")
    print(f"   Strategy: {strategy.__class__.__name__}")
    print(f"   Nodes: {[n['url'] for n in nodes]}")
    print()
    print("📊 View stats: http://localhost:{}/stats".format(args.port))
    
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="warning")
