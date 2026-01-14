from crdt_demo import GSet
import os
import time

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    node_a = GSet()
    node_b = GSet()
    
    actions = [
        ("A", "Buy Milk"),
        ("B", "Fix Bug"),
        ("A", "Call Mom"),
        ("B", "Milk the Cow"),
        ("A", "Fix Bug"), # Duplicate item (already in set)
    ]
    
    for actor, item in actions:
        clear_screen()
        print("        📋  CRDT VISUALIZER (G-SET)  📋")
        print("="*45)
        
        if actor == "A":
            node_a.add(item)
            print(f"Node A added: '{item}'")
        else:
            node_b.add(item)
            print(f"Node B added: '{item}'")
            
        print("-" * 45)
        print(f"Node A State: {node_a}")
        print(f"Node B State: {node_b}")
        print("-" * 45)
        print("Nodes are currently DISCONNECTED.")
        
        time.sleep(2)

    clear_screen()
    print("        📋  CRDT VISUALIZER (G-SET)  📋")
    print("="*45)
    print("Action: SYNCING NODES (Merge)")
    print("-" * 45)
    
    # Merge both ways to show commutativity
    node_a.merge(node_b)
    node_b.merge(node_a)
    
    print(f"Node A State: {node_a}")
    print(f"Node B State: {node_b}")
    print("-" * 45)
    print("✅ CONSISTENCY REACHED: Nodes are identical!")
    print("Notice how 'Fix Bug' only appears once.")
    
    print("\nPress Ctrl+C to exit.")
    while True: time.sleep(1)

if __name__ == "__main__":
    main()
