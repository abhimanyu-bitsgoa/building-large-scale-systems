import time
import requests
import argparse
import concurrent.futures
import sys

# Default Nodes
NODES = [
    "http://localhost:5001",
    "http://localhost:5002",
    "http://localhost:5003"
]

def send_request(node_url, verbose=False):
    """Sends a single request and prints the result."""
    try:
        start_time = time.time()
        resp = requests.post(f"{node_url}/data", json={"key": "test", "value": "123"}, timeout=5)
        latency = (time.time() - start_time) * 1000
        
        status = "✅" if resp.status_code == 200 else "❌"
        active_reqs = resp.headers.get("X-Active-Requests", "?")
        
        if verbose or resp.status_code != 200:
            print(f"{status} [{node_url}] {resp.status_code} | Latency: {latency:.2f}ms | Active: {active_reqs}")
        return True, latency
    except Exception as e:
        print(f"❌ Failed to reach {node_url}: {e}")
        return False, 0

def run_client(concurrency, target_url, requests_limit):
    print(f"🚀 Starting Client with {concurrency} threads.")
    if target_url:
        print(f"🎯 Targeting: {target_url}")
    else:
        print(f"🔄 Round-Robin across {len(NODES)} nodes.")

    count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        while True:
            if requests_limit and count >= requests_limit:
                break
                
            futures = []
            # Schedule a batch of tasks equal to concurrency
            for _ in range(concurrency):
                if requests_limit and count >= requests_limit:
                    break
                
                # Pick node
                if target_url:
                    node = target_url
                else:
                    node = NODES[count % len(NODES)]
                
                futures.append(executor.submit(send_request, node, True))
                count += 1
            
            # Wait for this batch to complete (simple synchronization for demo output clarity)
            # In a real load test, we might just flood without waiting.
            concurrent.futures.wait(futures)
            
            # Small sleep to prevent unreadable console spam if fast
            time.sleep(0.1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrent", type=int, default=1, help="Number of concurrent threads")
    parser.add_argument("--target", type=str, help="Specific Node URL to target (e.g. http://localhost:5002)")
    parser.add_argument("--requests", type=int, default=0, help="Total requests to send (0 = infinite)")
    args = parser.parse_args()
    
    try:
        run_client(args.concurrent, args.target, args.requests)
    except KeyboardInterrupt:
        print("\n🛑 Client stopped.")
