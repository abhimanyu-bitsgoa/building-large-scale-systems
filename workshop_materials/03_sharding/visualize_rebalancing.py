import random
from sharding_lib import ModuloStrategy, ConsistentHashingStrategy

def visualize_rebalancing(strategy_name: str, num_keys=1000):
    print(f"\n🧪 Testing Strategy: {strategy_name}")
    print(f"Generating {num_keys} keys...")
    
    keys = [f"key_{i}" for i in range(num_keys)]
    nodes_initial = ["Node A", "Node B", "Node C"]
    
    # Select Strategy
    if strategy_name == "MODULO":
        strategy = ModuloStrategy()
    else:
        strategy = ConsistentHashingStrategy(nodes_initial)
        
    # Phase 1: Initial Mapping
    mapping_initial = {}
    for k in keys:
        node = strategy.get_node(k, nodes_initial)
        mapping_initial[k] = node
        
    print(f"Phase 1: Keys distributed across {len(nodes_initial)} nodes.")
    
    # Phase 2: Add a Node
    print("Phase 2: Adding 'Node D'...")
    nodes_final = nodes_initial + ["Node D"]
    
    if isinstance(strategy, ConsistentHashingStrategy):
        strategy.add_node("Node D")
        
    mapping_final = {}
    moved_count = 0
    
    for k in keys:
        new_node = strategy.get_node(k, nodes_final)
        mapping_final[k] = new_node
        if new_node != mapping_initial[k]:
            moved_count += 1
            
    percent_moved = (moved_count / num_keys) * 100
    
    # Visualization Bar
    bar_moved = "▓" * int(percent_moved / 2)
    bar_stayed = "░" * int((100 - percent_moved) / 2)
    
    print("\n📊 RESULTS:")
    print(f"Keys Moved:   {moved_count}/{num_keys}")
    print(f"Percentage:   {percent_moved:.1f}%")
    print(f"Visualization: [{bar_moved}{bar_stayed}]")
    
    if percent_moved > 50:
        print("⚠️ HIGH IMPACT! (Naive sharding requires moving most data)")
    else:
        print("✅ LOW IMPACT! (Consistent hashing minimizes movement)")

if __name__ == "__main__":
    visualize_rebalancing("MODULO")
    print("\n" + "-"*40)
    visualize_rebalancing("CONSISTENT_HASHING")
