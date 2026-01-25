"""
Scalability Lab - TUI Dashboard

Real-time visualization of load distribution, rate limiting, and node health.
Inspired by unified_dashboard.py from workshop_materials/23_resilient_system.
"""

import time
import sys
import threading
import requests
from collections import defaultdict
import argparse

# ========================
# ANSI Color Codes
# ========================

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"

# ========================
# Dashboard State
# ========================

class DashboardState:
    """Tracks state for the dashboard."""
    
    def __init__(self, nodes: list):
        self.nodes = nodes
        self.lock = threading.Lock()
        
        # Per-node metrics
        self.stats = {node: {
            "requests": 0,
            "rate_limited": 0,
            "errors": 0,
            "avg_latency": 0.0,
            "active_requests": 0,
            "status": "unknown"
        } for node in nodes}
        
        # Total metrics
        self.total_requests = 0
        self.total_rate_limited = 0
        self.total_errors = 0
    
    def update_node(self, node: str, requests: int = 0, rate_limited: int = 0,
                    errors: int = 0, latency: float = 0, active: int = 0, status: str = None):
        """Update metrics for a node."""
        with self.lock:
            stats = self.stats.get(node, {})
            stats["requests"] = requests
            stats["rate_limited"] = rate_limited
            stats["errors"] = errors
            stats["avg_latency"] = latency
            stats["active_requests"] = active
            if status:
                stats["status"] = status
            self.stats[node] = stats
    
    def increment_totals(self, requests: int = 0, rate_limited: int = 0, errors: int = 0):
        """Increment total counters."""
        with self.lock:
            self.total_requests += requests
            self.total_rate_limited += rate_limited
            self.total_errors += errors

# ========================
# Display Functions
# ========================

def clear_screen():
    """Clear the terminal screen."""
    print("\033[H\033[J", end="")

def draw_bar(value: int, max_value: int, width: int = 30, color: str = Colors.GREEN) -> str:
    """Draw a colored bar chart."""
    if max_value == 0:
        filled = 0
    else:
        filled = int((value / max_value) * width)
    
    bar = "█" * filled + "░" * (width - filled)
    return f"{color}{bar}{Colors.RESET}"

def draw_dashboard(state: DashboardState):
    """Draw the complete dashboard."""
    clear_screen()
    
    # Header
    print(f"{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}║         SCALABILITY LAB - LOAD BALANCING DASHBOARD               ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}╚══════════════════════════════════════════════════════════════════╝{Colors.RESET}")
    print()
    
    # Summary
    print(f"{Colors.BOLD}📊 SUMMARY{Colors.RESET}")
    print(f"   Total Requests: {state.total_requests}")
    print(f"   Rate Limited:   {Colors.RED}{state.total_rate_limited}{Colors.RESET}")
    print(f"   Errors:         {state.total_errors}")
    print()
    
    # Node metrics
    print(f"{Colors.BOLD}🖥️  NODE METRICS{Colors.RESET}")
    print("-" * 70)
    
    # Calculate max for bar scaling
    max_requests = max(s["requests"] for s in state.stats.values()) or 1
    max_rate_limited = max(s["rate_limited"] for s in state.stats.values()) or 1
    
    for node in state.nodes:
        stats = state.stats[node]
        status_icon = "🟢" if stats["status"] == "ok" else "🔴" if stats["status"] == "error" else "⚪"
        
        print(f"\n{status_icon} {Colors.BOLD}{node}{Colors.RESET}")
        
        # Requests bar (green)
        req_bar = draw_bar(stats["requests"], max_requests, width=25, color=Colors.GREEN)
        print(f"   Requests:     {req_bar} {stats['requests']}")
        
        # Rate Limited bar (red)
        rl_bar = draw_bar(stats["rate_limited"], max(max_rate_limited, 1), width=25, color=Colors.RED)
        print(f"   Rate Limited: {rl_bar} {Colors.RED}{stats['rate_limited']}{Colors.RESET}")
        
        # Stats line
        print(f"   Latency: {stats['avg_latency']:.1f}ms | Active: {stats['active_requests']} | Errors: {stats['errors']}")
    
    print()
    print("-" * 70)
    print(f"{Colors.YELLOW}Press Ctrl+C to stop{Colors.RESET}")

# ========================
# Polling Functions
# ========================

def poll_node(node: str, state: DashboardState):
    """Poll a single node for stats."""
    try:
        resp = requests.get(f"{node}/stats", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            state.update_node(
                node,
                requests=data.get("total_requests", 0),
                rate_limited=data.get("rate_limited_requests", 0),
                active=data.get("active_requests", 0),
                latency=data.get("avg_latency_ms", 0.0),
                status="ok"
            )
        else:
            state.update_node(node, status="error")
    except:
        state.update_node(node, status="error")

def poll_loop(state: DashboardState, interval: float = 0.5):
    """Background loop that polls nodes."""
    while True:
        for node in state.nodes:
            poll_node(node, state)
        time.sleep(interval)

# ========================
# Traffic Generator (for demo)
# ========================

def generate_test_traffic(nodes: list, rate: float = 0.1):
    """Generate test traffic for demonstration."""
    import random
    
    while True:
        node = random.choice(nodes)
        try:
            requests.post(f"{node}/data", json={"key": "demo", "value": "test"}, timeout=2)
        except:
            pass
        time.sleep(rate)

# ========================
# Main Entry Point
# ========================

def run_dashboard(nodes: list, refresh_rate: float = 0.5, generate_traffic: bool = False):
    """Run the dashboard."""
    state = DashboardState(nodes)
    
    # Start polling thread
    poll_thread = threading.Thread(target=poll_loop, args=(state, refresh_rate), daemon=True)
    poll_thread.start()
    
    # Optionally start traffic generator
    if generate_traffic:
        traffic_thread = threading.Thread(target=generate_test_traffic, args=(nodes,), daemon=True)
        traffic_thread.start()
    
    # Main display loop
    try:
        while True:
            draw_dashboard(state)
            time.sleep(refresh_rate)
    except KeyboardInterrupt:
        clear_screen()
        print("👋 Dashboard stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scalability Lab - Dashboard")
    parser.add_argument("--nodes", type=str, default="http://localhost:5001,http://localhost:5002,http://localhost:5003",
                        help="Comma-separated list of node URLs")
    parser.add_argument("--refresh", type=float, default=0.5,
                        help="Refresh rate in seconds")
    parser.add_argument("--generate-traffic", action="store_true",
                        help="Generate test traffic for demonstration")
    
    args = parser.parse_args()
    nodes = [n.strip() for n in args.nodes.split(",")]
    
    print("🚀 Starting Dashboard...")
    print(f"   Monitoring: {nodes}")
    print(f"   Refresh rate: {args.refresh}s")
    if args.generate_traffic:
        print("   Traffic generator: ENABLED")
    print()
    time.sleep(1)
    
    run_dashboard(nodes, refresh_rate=args.refresh, generate_traffic=args.generate_traffic)
