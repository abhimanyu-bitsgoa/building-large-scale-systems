import json

class VectorClock:
    def __init__(self, node_id, num_nodes=3):
        self.node_id = node_id
        # [Node0_clock, Node1_clock, Node2_clock]
        self.clock = [0] * num_nodes

    def increment(self):
        """Called when a local event happens."""
        self.clock[self.node_id] += 1

    def update(self, received_clock):
        """Called when a message is received from another node."""
        for i in range(len(self.clock)):
            self.clock[i] = max(self.clock[i], received_clock[i])
        # After merging, increment own clock
        self.clock[self.node_id] += 1

    def __str__(self):
        return str(self.clock)

def compare_clocks(vc1, vc2):
    """
    Returns:
    -1: vc1 happened before vc2 (Causal)
     1: vc1 happened after vc2 (Causal)
     0: Concurrent (Conflicting)
    """
    less_than = False
    greater_than = False
    
    for c1, c2 in zip(vc1, vc2):
        if c1 < c2:
            less_than = True
        if c1 > c2:
            greater_than = True
            
    if less_than and not greater_than:
        return -1 # VC1 < VC2
    if greater_than and not less_than:
        return 1  # VC1 > VC2
    
    return 0 # Concurrent!

def demo():
    print("=== VECTOR CLOCKS: CAUSALITY DEMO ===")
    print("-" * 45)
    
    # Initialize clocks for 3 nodes
    vc0 = [0, 0, 0] # Node 0
    vc1 = [0, 0, 0] # Node 1
    
    # 1. Event pada Node 0
    vc0[0] += 1
    print(f"Node 0: Event local. Clock is now {vc0}")
    
    # 2. Node 0 sends message to Node 1
    print("Node 0 -> Sending message to Node 1...")
    msg_clock = list(vc0) 
    
    # 3. Node 1 receives message
    for i in range(3):
        vc1[i] = max(vc1[i], msg_clock[i])
    vc1[1] += 1 # Node 1 increments its own counter
    print(f"Node 1: Received message. Clock is now {vc1}")
    
    # Comparison
    relation = compare_clocks(vc0, vc1)
    print(f"\nResult: Node 0's clock {vc0} vs Node 1's clock {vc1}")
    if relation == -1:
        print("✅ CAUSAL: Node 0 definitely happened BEFORE Node 1.")
    
    # 4. A Concurrent Event (Conflict)
    vc0_concurrent = [2, 0, 0] # Node 0 did something else
    vc1_concurrent = [1, 2, 0] # Node 1 did something else without talking to Node 0
    
    print("\n" + "-" * 45)
    print("Scenario: Concurrent Events (The Conflict)")
    relation2 = compare_clocks(vc0_concurrent, vc1_concurrent)
    print(f"Node 0: {vc0_concurrent}")
    print(f"Node 1: {vc1_concurrent}")
    if relation2 == 0:
        print("🚨 CONFLICT: These events happened 'at the same time' (No causal link).")
        print("             We need to resolve this manually!")

if __name__ == "__main__":
    demo()
