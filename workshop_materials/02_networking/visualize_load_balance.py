import time
import sys
import threading
import requests
import random
from collections import defaultdict

# Configuration
NODES = [
    "http://localhost:5001",
    "http://localhost:5002",
    "http://localhost:5003"
]

# Metrics: Node URL -> count
stats = defaultdict(int)
running = True

def worker():
    """Background worker that continuously sends requests."""
    while running:
        # Simulate Round Robin or Random load balancing here to generate data
        # In a real workshop, this visualization would monitor the ACTUAL traffic
        # But for this standalone demo script, we simulate the CLIENT traffic distribution
        target = random.choice(NODES)
        try:
            requests.get(f"{target}/health", timeout=1)
            stats[target] += 1
        except:
            pass
        time.sleep(0.1)

def print_stats():
    """Prints a live bar chart of traffic distribution."""
    print("\n" * 5) # Clear some space
    print("=== Load Balancer Visualization ===")
    total = sum(stats.values())
    if total == 0:
        return

    for node in NODES:
        count = stats[node]
        percent = (count / total) * 100
        bar = "█" * int(percent / 2) # 1 char = 2%
        print(f"{node} | {count:3d} reqs ({percent:5.1f}%) | {bar}")
    print("===================================")

if __name__ == "__main__":
    print("Starting Visualization... Press Ctrl+C to stop.")
    
    # Start 5 concurrent workers to generate traffic
    threads = []
    for _ in range(5):
        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)

    try:
        while True:
            print_stats()
            # Reset stats every 5 seconds to show instantaneous load
            if sum(stats.values()) > 500:
                stats.clear()
            time.sleep(0.5)
            # Simple "clear screen" effect
            print("\033[H\033[J", end="")
    except KeyboardInterrupt:
        running = False
        print("\nStopping...")
