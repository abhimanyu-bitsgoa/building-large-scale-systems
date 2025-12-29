import time
import random

# Initial State: 3 Nodes with Data Version 1
NODES = {
    "Node 1": {"v": 1, "status": "UP"},
    "Node 2": {"v": 1, "status": "UP"},
    "Node 3": {"v": 1, "status": "UP"},
}

def read_quorum(key, r=2):
    responses = []
    print(f"Requesting key '{key}' from all nodes (R={r})...")
    
    for name, node in NODES.items():
        if node["status"] == "UP":
            responses.append((name, node["v"]))
        else:
            print(f"  ❌ {name} is DOWN")
            
    success_count = len(responses)
    if success_count >= r:
        # Return the highest version found
        best_node, best_ver = max(responses, key=lambda x: x[1])
        return True, best_ver, [n[0] for n in responses]
    else:
        return False, None, []

def main():
    print("--- SYSTEM HEALTHY ---")
    ok, ver, who = read_quorum("my_key")
    print(f"Result: SUCCESS. Got Version {ver} from {who}\n")
    
    print("--- 💥 DISASTER: KILLING NODE 2 ---")
    NODES["Node 2"]["status"] = "DOWN"
    
    ok, ver, who = read_quorum("my_key")
    if ok:
        print(f"Result: SUCCESS (Quorum Met). Got Version {ver} from {who}")
    else:
        print(f"Result: FAILURE. Quorum not met.")
        
    print("\n--- 💥 CATASTROPHE: KILLING NODE 3 ---")
    NODES["Node 3"]["status"] = "DOWN"
    
    ok, ver, who = read_quorum("my_key")
    if ok:
        print(f"Result: SUCCESS. Got {ver}")
    else:
        print(f"Result: FAILURE. Only 1/3 nodes alive. R=2 not met.")

if __name__ == "__main__":
    main()
