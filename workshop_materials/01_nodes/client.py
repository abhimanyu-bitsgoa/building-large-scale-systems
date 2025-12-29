import time
import requests

# TODO: Define your list of nodes here
NODES = [
    "http://localhost:5001",
    "http://localhost:5002",
    "http://localhost:5003"
]

def send_request():
    # TODO: Implement Round Robin selection
    target_node = NODES[0] 
    
    try:
        start_time = time.time()
        resp = requests.get(f"{target_node}/health", timeout=2)
        print(f"✅ Success from {target_node}: {resp.json()} ({time.time() - start_time:.4f}s)")
    except Exception as e:
        print(f"❌ Failed to reach {target_node}: {e}")

if __name__ == "__main__":
    print("Starting Client Loop...")
    while True:
        send_request()
        time.sleep(1)
