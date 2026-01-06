import requests
import time
import os

NODES = [
    {"name": "PRIMARY", "port": 13000},
    {"name": "SECONDARY 1", "port": 13001},
    {"name": "SECONDARY 2", "port": 13002},
]

TEST_KEY = "user_1"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    while True:
        clear_screen()
        print("        🕒  REPLICATION LAG VISUALIZER  🕒")
        print("=" * 45)
        print(f"Tracking Key: '{TEST_KEY}'")
        print("-" * 45)
        print("Node Name   | Status   | Current Value")
        print("-" * 45)
        
        for node in NODES:
            try:
                resp = requests.get(f"http://localhost:{node['port']}/data/{TEST_KEY}", timeout=0.5)
                data = resp.json()
                val = data.get("value")
                val_display = f"'{val}'" if val else "NONE"
                print(f" {node['name']:<11} | ONLINE   | {val_display}")
            except:
                print(f" {node['name']:<11} | OFFLINE  | -")

        print("-" * 45)
        print("\nHow to test:")
        print("1. Run: curl -X POST http://localhost:13000/write \\")
        print("   -H \"Content-Type: application/json\" \\")
        print("   -d '{\"key\": \"user_1\", \"value\": \"Alice\"}'")
        print("\n2. Watch the value appear INSTANTLY on PRIMARY.")
        print("3. Watch the delay (5s) before it appears on SECONDARIES.")
        
        print("\nPress Ctrl+C to stop.")
        time.sleep(1)

if __name__ == "__main__":
    main()
