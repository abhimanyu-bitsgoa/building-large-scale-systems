"""
Least Connections Solution

📋 SOLUTION FILE - Students can copy this to see the load balancer working.

Copy the select_node() method below into your LeastConnectionsStrategy class
in load_balancer.py to complete the exercise.
"""


def select_node_solution(self, nodes):
    """
    Complete implementation of the least connections algorithm.
    
    Copy this method into your LeastConnectionsStrategy class.
    """
    if not nodes:
        raise ValueError("No nodes available")
    
    # Find the node with the minimum active connections
    # Using min() with a lambda to compare by connection count
    selected = min(
        nodes,
        key=lambda node: self.active_connections[node["url"]]
    )
    
    return selected


# ═══════════════════════════════════════════════════════════════════
# ALTERNATIVE IMPLEMENTATION (More explicit)
# ═══════════════════════════════════════════════════════════════════

def select_node_explicit(self, nodes):
    """
    Explicit loop version - easier to understand for beginners.
    """
    if not nodes:
        raise ValueError("No nodes available")
    
    best_node = nodes[0]
    min_connections = self.active_connections[best_node["url"]]
    
    for node in nodes[1:]:
        connections = self.active_connections[node["url"]]
        if connections < min_connections:
            min_connections = connections
            best_node = node
    
    return best_node


# ═══════════════════════════════════════════════════════════════════
# QUICK COPY-PASTE VERSION
# ═══════════════════════════════════════════════════════════════════
# Replace the entire select_node method in load_balancer.py with this:

"""
def select_node(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not nodes:
        raise ValueError("No nodes available")
    
    return min(nodes, key=lambda node: self.active_connections[node["url"]])
"""
