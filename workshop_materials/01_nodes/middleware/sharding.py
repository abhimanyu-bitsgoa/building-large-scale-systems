"""
Sharding Middleware

Routes data to the correct node in a cluster based on key hash.
Demonstrates consistent hashing vs simple modulo-based sharding.
"""

import hashlib
import bisect
from typing import List, Dict, Any, Optional
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse


class ShardingStrategy:
    """Base class for sharding strategies."""
    
    def get_node(self, key: str, nodes: List[str]) -> str:
        """Determine which node is responsible for this key."""
        raise NotImplementedError


class ModuloStrategy(ShardingStrategy):
    """
    Simple Modulo-based Sharding
    
    📝 STUDENT EXERCISE: Implement the get_node() method
    
    How Modulo Sharding works:
    ┌─────────────────────────────────────────────────────────────┐
    │  1. Hash the key to get an integer                         │
    │  2. Use modulo (%) to pick a node index                    │
    │     node_index = hash(key) % number_of_nodes               │
    │  3. Return the node at that index                          │
    └─────────────────────────────────────────────────────────────┘
    
    Example with 3 nodes:
    - key "user:123" → hash = 12345 → 12345 % 3 = 0 → Node 0
    - key "user:456" → hash = 67890 → 67890 % 3 = 0 → Node 0
    - key "user:789" → hash = 24681 → 24681 % 3 = 1 → Node 1
    
    ⚠️ PROBLEM: When you add/remove nodes, almost ALL keys need to move!
    """
    
    def _hash(self, key: str) -> int:
        """Convert key to a stable integer hash."""
        return int(hashlib.sha256(key.encode()).hexdigest(), 16)
    
    def get_node(self, key: str, nodes: List[str]) -> str:
        """
        Get the node responsible for this key using modulo.
        
        ════════════════════════════════════════════════════════
        TODO: Implement the modulo sharding algorithm
        
        Steps:
        1. If nodes list is empty, return None
        2. Hash the key using self._hash(key)
        3. Calculate index = hash_value % len(nodes)
        4. Return nodes[index]
        ════════════════════════════════════════════════════════
        """
        # ─────────────────────────────────────────────────────
        # YOUR CODE HERE
        # ─────────────────────────────────────────────────────
        raise NotImplementedError(
            "Implement the modulo sharding algorithm! "
            "See the docstring above for step-by-step instructions."
        )


class ConsistentHashingStrategy(ShardingStrategy):
    """
    Consistent Hashing (Complete Implementation)
    
    Minimizes key redistribution when nodes join/leave.
    Uses virtual nodes for better distribution.
    
    How it works:
    ┌─────────────────────────────────────────────────────────────┐
    │  1. Place nodes on a "ring" (0 to 2^256)                   │
    │  2. Each physical node has multiple "virtual nodes"        │
    │  3. Hash the key to find its position on the ring          │
    │  4. Walk clockwise to find the first node                  │
    │  5. That node owns this key                                │
    └─────────────────────────────────────────────────────────────┘
    
    When a node leaves: Only its keys move to the next node
    When a node joins: It takes some keys from its neighbors
    """
    
    def __init__(self, nodes: List[str] = None, virtual_nodes: int = 100):
        """
        Initialize the hash ring.
        
        Args:
            nodes: Initial list of node addresses
            virtual_nodes: Number of virtual nodes per physical node
                          (more = better distribution)
        """
        self.virtual_nodes = virtual_nodes
        self.ring: Dict[int, str] = {}  # hash_position -> node_address
        self.sorted_keys: List[int] = []  # Sorted hash positions
        
        if nodes:
            for node in nodes:
                self.add_node(node)
    
    def _hash(self, key: str) -> int:
        """Convert key to a stable integer hash."""
        return int(hashlib.sha256(key.encode()).hexdigest(), 16)
    
    def add_node(self, node: str):
        """Add a node to the ring with virtual nodes."""
        for i in range(self.virtual_nodes):
            virtual_key = f"{node}-vn{i}"
            hash_val = self._hash(virtual_key)
            self.ring[hash_val] = node
            bisect.insort(self.sorted_keys, hash_val)
    
    def remove_node(self, node: str):
        """Remove a node and all its virtual nodes from the ring."""
        keys_to_remove = [k for k, v in self.ring.items() if v == node]
        for k in keys_to_remove:
            del self.ring[k]
            self.sorted_keys.remove(k)
    
    def get_node(self, key: str, nodes: List[str] = None) -> str:
        """
        Find the node responsible for this key.
        
        Walk clockwise on the ring until we hit a node.
        """
        if not self.ring:
            return None
        
        hash_val = self._hash(key)
        
        # Binary search for first position >= hash_val
        idx = bisect.bisect(self.sorted_keys, hash_val)
        
        # Wrap around if needed
        if idx == len(self.sorted_keys):
            idx = 0
        
        return self.ring[self.sorted_keys[idx]]
    
    def get_key_distribution(self) -> Dict[str, int]:
        """Get count of virtual nodes per physical node."""
        distribution = {}
        for node in self.ring.values():
            distribution[node] = distribution.get(node, 0) + 1
        return distribution


class ShardingMiddleware:
    """
    Middleware that routes requests to the correct shard.
    
    For writes: Routes to the responsible node
    For reads: Checks if this node owns the key, fetches from peer if not
    
    Usage:
        python node.py --port 5001 --id node-1 --sharding consistent_hash --peers 5002,5003
    """
    
    def __init__(
        self,
        app,
        node_id: str,
        node_port: int,
        peers: List[int],
        strategy: str = "consistent_hash"
    ):
        """
        Initialize sharding middleware.
        
        Args:
            app: FastAPI application
            node_id: This node's ID
            node_port: This node's port
            peers: List of peer ports
            strategy: "consistent_hash" or "modulo"
        """
        self.app = app
        self.node_id = node_id
        self.node_port = node_port
        self.node_address = f"http://localhost:{node_port}"
        
        # Build node list (self + peers)
        all_ports = [node_port] + peers
        self.nodes = [f"http://localhost:{p}" for p in sorted(all_ports)]
        
        # Initialize strategy
        if strategy == "consistent_hash":
            self.strategy = ConsistentHashingStrategy(self.nodes)
        else:
            self.strategy = ModuloStrategy()
        
        self.strategy_name = strategy
    
    def get_responsible_node(self, key: str) -> str:
        """Get the node responsible for a key."""
        return self.strategy.get_node(key, self.nodes)
    
    def is_local(self, key: str) -> bool:
        """Check if this node is responsible for the key."""
        responsible = self.get_responsible_node(key)
        return responsible == self.node_address
    
    def forward_to_node(self, node: str, method: str, path: str, data: dict = None) -> dict:
        """Forward a request to another node."""
        try:
            if method == "GET":
                resp = requests.get(f"{node}{path}", timeout=2)
            elif method == "POST":
                resp = requests.post(f"{node}{path}", json=data, timeout=2)
            return resp.json()
        except Exception as e:
            return {"error": str(e), "node": node}
    
    def get_shard_info(self) -> dict:
        """Get information about sharding configuration."""
        return {
            "node_id": self.node_id,
            "node_address": self.node_address,
            "strategy": self.strategy_name,
            "total_nodes": len(self.nodes),
            "nodes": self.nodes,
            "virtual_nodes_per_node": getattr(self.strategy, 'virtual_nodes', 'N/A')
        }
    
    async def __call__(self, scope, receive, send):
        """ASGI interface - passthrough for now."""
        await self.app(scope, receive, send)


def add_sharding_endpoints(app: FastAPI, middleware: ShardingMiddleware, data_store: dict):
    """
    Add sharding-aware endpoints.
    
    These override the default /data endpoints with shard-routing logic.
    """
    
    @app.get("/shard-info")
    def shard_info():
        """Get sharding configuration for this node."""
        return middleware.get_shard_info()
    
    @app.get("/shard-for/{key}")
    def get_shard_for_key(key: str):
        """Find which node is responsible for a key."""
        responsible = middleware.get_responsible_node(key)
        is_local = middleware.is_local(key)
        return {
            "key": key,
            "responsible_node": responsible,
            "is_local": is_local,
            "current_node": middleware.node_address
        }
    
    @app.post("/shard-write")
    def sharded_write(payload: dict):
        """
        Write to the correct shard.
        
        If this node owns the key, store locally.
        Otherwise, forward to the responsible node.
        """
        key = payload.get("key")
        value = payload.get("value")
        
        if not key or not value:
            return {"error": "Missing key or value"}
        
        responsible = middleware.get_responsible_node(key)
        
        if middleware.is_local(key):
            # Store locally
            data_store[key] = value
            return {
                "status": "stored",
                "node": middleware.node_id,
                "key": key,
                "location": "local"
            }
        else:
            # Forward to responsible node
            result = middleware.forward_to_node(responsible, "POST", "/shard-write", payload)
            result["forwarded_from"] = middleware.node_id
            return result
    
    @app.get("/shard-read/{key}")
    def sharded_read(key: str):
        """
        Read from the correct shard.
        
        If this node owns the key, read locally.
        Otherwise, forward to the responsible node.
        """
        responsible = middleware.get_responsible_node(key)
        
        if middleware.is_local(key):
            # Read locally
            value = data_store.get(key)
            return {
                "key": key,
                "value": value,
                "node": middleware.node_id,
                "location": "local"
            }
        else:
            # Forward to responsible node
            result = middleware.forward_to_node(responsible, "GET", f"/shard-read/{key}")
            result["forwarded_from"] = middleware.node_id
            return result
