import requests
import time
import os

REGISTRY_URL = "http://localhost:5000/nodes"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    while True:
        clear_screen()
        print("        🌐  SERVICE DISCOVERY & HEARTBEATS  🌐")
        print("=" * 45)
        print("Node ID | Port | Last Seen (seconds ago)")
        print("-" * 45)
        
        try:
            resp = requests.get(REGISTRY_URL, timeout=1)
            nodes = resp.json()
            
            if not nodes:
                print("       No active nodes registered.")
            
            now = time.time()
            for nid, info in nodes.items():
                last_seen = now - info["last_seen"]
                print(f" {nid:<7} | {info['port']:<4} | {last_seen:.1f}s ago")
                
        except:
            print("  [ERROR] Could not connect to Registry.")

        print("-" * 45)
        print("\nHow to test:")
        print("1. Start Registry: python3 workshop_materials/11_membership/registry.py")
        print("2. Start Nodes: python3 workshop_materials/11_membership/heartbeat_node.py --port 6001 --id node1")
        print("3. Watch them appear here.")
        print("4. Kill a node (Ctrl+C). Watch it disappear after 5 seconds!")
        
        print("\nPress Ctrl+C to stop.")
        time.sleep(1)

if __name__ == "__main__":
    main()
