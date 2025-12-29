from typing import List
from sharding_lib import ModuloStrategy, ConsistentHashingStrategy

class Router:
    def __init__(self):
        self.nodes = ["Node A", "Node B", "Node C"]
        self.strategy = ModuloStrategy()
        # self.strategy = ConsistentHashingStrategy(self.nodes)

    def add_node(self, node: str):
        self.nodes.append(node)
        # If using ConsistentHashing, we need to update the ring
        if isinstance(self.strategy, ConsistentHashingStrategy):
            self.strategy.add_node(node)
        print(f"➕ Added {node}. Total: {len(self.nodes)}")

    def get_node_for_key(self, key: str) -> str:
        # TODO: Use the strategy to get the node
        return self.strategy.get_node(key, self.nodes)

if __name__ == "__main__":
    router = Router()
    key = "user_123"
    node = router.get_node_for_key(key)
    print(f"Key '{key}' maps to {node}")
