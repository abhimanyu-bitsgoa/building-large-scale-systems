"""
Modulo Strategy Solution

📋 SOLUTION FILE - Students can copy this to see the sharding working.

Copy the get_node() method below into your ModuloStrategy class
in middleware/sharding.py to complete the exercise.
"""


def get_node_solution(self, key: str, nodes) -> str:
    """
    Complete implementation of the modulo sharding algorithm.
    
    Copy this method into your ModuloStrategy class.
    """
    if not nodes:
        return None
    
    # Hash the key to get a stable integer
    hash_value = self._hash(key)
    
    # Use modulo to pick a node index
    index = hash_value % len(nodes)
    
    # Return the node at that index
    return nodes[index]


# ═══════════════════════════════════════════════════════════════════
# QUICK COPY-PASTE VERSION
# ═══════════════════════════════════════════════════════════════════
# Replace the entire get_node method in sharding.py with this:

"""
def get_node(self, key: str, nodes: List[str]) -> str:
    if not nodes:
        return None
    hash_value = self._hash(key)
    index = hash_value % len(nodes)
    return nodes[index]
"""
