from typing import List, Protocol
import hashlib
import bisect

class ShardingStrategy(Protocol):
    def get_node(self, key: str, nodes: List[str]) -> str:
        """Determines which node responsible for the given key."""
        ...

class ModuloStrategy:
    def get_node(self, key: str, nodes: List[str]) -> str:
        if not nodes:
            return None
        # Simple hash of the string to get an integer
        # We use a standard hash to be deterministic across runs if properly seeded,
        # but built-in hash() is randomized in Python 3. 
        # So we use sha256 for stability in the workshop.
        hash_val = int(hashlib.sha256(key.encode()).hexdigest(), 16)
        index = hash_val % len(nodes)
        return nodes[index]

class ConsistentHashingStrategy:
    def __init__(self, nodes: List[str] = None, virtual_nodes: int = 100):
        self.virtual_nodes = virtual_nodes
        self.ring = {}
        self.sorted_keys = []
        if nodes:
            for node in nodes:
                self.add_node(node)

    def _hash(self, key: str) -> int:
        return int(hashlib.sha256(key.encode()).hexdigest(), 16)

    def add_node(self, node: str):
        for i in range(self.virtual_nodes):
            virtual_key = f"{node}-{i}"
            hash_val = self._hash(virtual_key)
            self.ring[hash_val] = node
            bisect.insort(self.sorted_keys, hash_val)

    def remove_node(self, node: str):
        # In a real impl, this is O(VN). For workshop it's fine.
        keys_to_remove = [k for k, v in self.ring.items() if v == node]
        for k in keys_to_remove:
            del self.ring[k]
            self.sorted_keys.remove(k)

    def get_node(self, key: str, nodes: List[str]=None) -> str:
        # Note: 'nodes' arg is ignored here as the Ring manages its own state.
        # This divergence from the Protocol signature suggests we might want 
        # to initialize the Strategy with nodes, but for simplicity we keep usage similar.
        if not self.ring:
            return None
            
        hash_val = self._hash(key)
        # Find the first key on the ring >= hash_val
        idx = bisect.bisect(self.sorted_keys, hash_val)
        
        # Wrap around if needed
        if idx == len(self.sorted_keys):
            idx = 0
            
        return self.ring[self.sorted_keys[idx]]
