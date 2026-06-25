"""
Scalability Lab - Client (stage 02: naive routing)

A client that spreads requests across several nodes by *naive round-robin* —
request i goes to nodes[i % len(nodes)], blind to how loaded each node is.

There is NO load balancer yet: routing is a single inline counter below. That is
exactly the point of this stage — once the nodes are heterogeneous (one weak, two
strong), naive round-robin sends a third of the traffic to the slow node and the
tail latency suffers. Stage 03 introduces `load_balancer.py` to fix that.
"""

import time
import requests
import argparse
import concurrent.futures
from collections import defaultdict

# ========================
# Default Configuration
# ========================

DEFAULT_NODES = [
    "http://localhost:5001",
    "http://localhost:5002",
    "http://localhost:5003"
]

# ========================
# Metrics Tracking
# ========================

class ClientMetrics:
    """Track request metrics for visualization."""

    def __init__(self):
        self.requests_per_node = defaultdict(int)
        self.latencies_per_node = defaultdict(list)
        self.rate_limited_per_node = defaultdict(int)
        self.errors_per_node = defaultdict(int)
        self.total_requests = 0
        self.total_rate_limited = 0

    def record_success(self, node_url: str, latency: float):
        """Record a successful request."""
        self.requests_per_node[node_url] += 1
        self.latencies_per_node[node_url].append(latency)
        self.total_requests += 1

    def record_rate_limited(self, node_url: str):
        """Record a rate-limited request (HTTP 429)."""
        self.rate_limited_per_node[node_url] += 1
        self.total_rate_limited += 1
        self.total_requests += 1

    def record_error(self, node_url: str):
        """Record a failed request."""
        self.errors_per_node[node_url] += 1
        self.total_requests += 1

metrics = ClientMetrics()

# ========================
# Request Functions
# ========================

def send_request(node_url: str, verbose: bool = False) -> tuple:
    """
    Send a single request to a node.

    Returns:
        Tuple of (success, latency_ms, status_code)
    """
    try:
        start_time = time.time()
        resp = requests.post(
            f"{node_url}/data",
            json={"key": "test", "value": "123"},
            timeout=10
        )
        latency = (time.time() - start_time) * 1000

        active_reqs = resp.headers.get("X-Active-Requests", "?")

        if resp.status_code == 200:
            metrics.record_success(node_url, latency)
            if verbose:
                print(f"✅ [{node_url}] 200 | Latency: {latency:.2f}ms | Active: {active_reqs}")
            return True, latency, 200

        elif resp.status_code == 429:
            metrics.record_rate_limited(node_url)
            retry_after = resp.headers.get("Retry-After", "?")
            if verbose:
                print(f"🚫 [{node_url}] 429 RATE LIMITED | Retry-After: {retry_after}s")
            return False, latency, 429

        else:
            metrics.record_error(node_url)
            if verbose:
                print(f"❌ [{node_url}] {resp.status_code} | Latency: {latency:.2f}ms")
            return False, latency, resp.status_code

    except Exception as e:
        metrics.record_error(node_url)
        if verbose:
            print(f"❌ Failed to reach {node_url}: {e}")
        return False, 0, 0

# ========================
# Main Client Loop
# ========================

def run_client(nodes: list, concurrency: int, requests_limit: int,
               rate_delay: float, verbose: bool):
    """
    Run the client, spreading requests across nodes by naive round-robin.

    Args:
        nodes: List of node URLs
        concurrency: Number of concurrent threads
        requests_limit: Total requests to send (0 = infinite)
        rate_delay: Delay between batches (seconds)
        verbose: Print each request result
    """
    print(f"🚀 Starting Client")
    print(f"   Nodes: {nodes}")
    print(f"   Threads: {concurrency}")
    print(f"   Routing: naive round-robin (no load balancer)")
    print(f"   Rate delay: {rate_delay}s")
    if requests_limit:
        print(f"   Request limit: {requests_limit}")
    print()

    count = 0  # also our round-robin cursor: node = nodes[count % len(nodes)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        try:
            while True:
                if requests_limit and count >= requests_limit:
                    break

                futures = []
                for _ in range(concurrency):
                    if requests_limit and count >= requests_limit:
                        break

                    # Naive round-robin: pick the next node in order, ignoring load.
                    node = nodes[count % len(nodes)]
                    futures.append(executor.submit(send_request, node, verbose))
                    count += 1

                for future in futures:
                    future.result()

                if rate_delay > 0:
                    time.sleep(rate_delay)
                else:
                    time.sleep(0.01)

        except KeyboardInterrupt:
            print("\n🛑 Client stopped.")

    print_stats(nodes)

def print_stats(nodes: list):
    """Print final statistics with P95, median, and global stats."""
    print("\n" + "=" * 60)
    print("FINAL STATISTICS")
    print("=" * 60)

    total = metrics.total_requests
    rate_limited = metrics.total_rate_limited

    if total == 0:
        print("No requests were made.")
        return

    rate_pct = (rate_limited / total * 100) if total > 0 else 0
    print(f"Total Requests: {total}")
    print(f"Rate Limited (429): {rate_limited} ({rate_pct:.1f}%)")
    print()

    all_latencies = []
    total_success = 0
    total_errors = 0

    for node in nodes:
        success = metrics.requests_per_node[node]
        limited = metrics.rate_limited_per_node[node]
        errors = metrics.errors_per_node[node]
        latencies = metrics.latencies_per_node[node]

        all_latencies.extend(latencies)
        total_success += success
        total_errors += errors

        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        p95_latency = calculate_percentile(latencies, 95) if latencies else 0.0

        print(f"{node}:")
        print(f"  ✅ Success: {success}")
        print(f"  🚫 Rate Limited: {limited}")
        print(f"  ❌ Errors: {errors}")
        print(f"  ⏱️  Avg Latency: {avg_latency:.2f}ms")
        print(f"  ⏱️  P95 Latency: {p95_latency:.2f}ms")
        print()

    print("=" * 60)
    print("GLOBAL SYSTEM STATS")
    print("=" * 60)

    if all_latencies:
        global_avg = sum(all_latencies) / len(all_latencies)
        global_p95 = calculate_percentile(all_latencies, 95)
    else:
        global_avg = global_p95 = 0.0

    print(f"  ✅ Total Success: {total_success}")
    print(f"  🚫 Total Rate Limited: {rate_limited}")
    print(f"  ❌ Total Errors: {total_errors}")
    print(f"  ⏱️  Global Avg Latency: {global_avg:.2f}ms")
    print(f"  ⏱️  Global P95 Latency: {global_p95:.2f}ms")
    print()

def calculate_percentile(data: list, percentile: float) -> float:
    """Calculate the given percentile of a list of values."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    n = len(sorted_data)
    index = (percentile / 100) * (n - 1)

    lower = int(index)
    upper = lower + 1

    if upper >= n:
        return sorted_data[-1]

    weight = index - lower
    return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight

# ========================
# Main Entry Point
# ========================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scalability Lab - Client (stage 02: naive round-robin)")
    parser.add_argument("--concurrent", type=int, default=1,
                        help="Number of concurrent threads")
    parser.add_argument("--target", type=str, default=None,
                        help="Single node URL to target (send everything to one node)")
    parser.add_argument("--nodes", type=str, default=None,
                        help="Comma-separated list of node URLs")
    parser.add_argument("--requests", type=int, default=0,
                        help="Total requests to send (0 = infinite)")
    parser.add_argument("--rate", type=float, default=0,
                        help="Delay between batches in seconds (e.g., --rate 1 for 1 second)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print each request result")

    args = parser.parse_args()

    if args.target:
        nodes = [args.target]
    elif args.nodes:
        nodes = [n.strip() for n in args.nodes.split(",")]
    else:
        nodes = DEFAULT_NODES

    try:
        run_client(
            nodes=nodes,
            concurrency=args.concurrent,
            requests_limit=args.requests,
            rate_delay=args.rate,
            verbose=args.verbose
        )
    except KeyboardInterrupt:
        print("\n🛑 Client stopped.")
        print_stats(nodes)
