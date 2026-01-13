"""
Unified Dashboard - Real-time cluster health visualization.

Features:
- ASCII terminal dashboard
- Node heartbeat status with color coding
- Consistent hashing ring visualization
- Recent request log
- Key distribution across nodes
"""

import requests
import time
import os
import sys
from datetime import datetime

# ANSI color codes
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
    BG_YELLOW = "\033[43m"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_status_color(status: str, last_seen: float) -> str:
    if status == "alive" and last_seen < 3:
        return Colors.GREEN
    elif status == "alive" and last_seen < 5:
        return Colors.YELLOW
    else:
        return Colors.RED

def draw_node_box(node: dict) -> list:
    """Draw a single node status box."""
    status = node.get("status", "unknown")
    last_seen = node.get("last_seen_seconds_ago", 999)
    node_id = node.get("node_id", "???")
    address = node.get("address", "???")
    
    color = get_status_color(status, last_seen)
    
    # Status indicator
    if status == "alive" and last_seen < 3:
        indicator = "●"
        status_text = "HEALTHY"
    elif status == "alive":
        indicator = "◐"
        status_text = "SLOW"
    else:
        indicator = "○"
        status_text = "DEAD"
    
    lines = [
        f"┌──────────────────────────┐",
        f"│ {color}{indicator}{Colors.RESET} {Colors.BOLD}{node_id:20}{Colors.RESET}   │",
        f"│   {address:22} │",
        f"│   Status: {color}{status_text:6}{Colors.RESET}         │",
        f"│   Last seen: {last_seen:5.1f}s ago  │",
        f"└──────────────────────────┘"
    ]
    return lines

def get_node_hash_position(node_id: str) -> int:
    """Get consistent hash position (0-359 degrees) for a node."""
    import hashlib
    hash_val = int(hashlib.md5(node_id.encode()).hexdigest(), 16)
    return hash_val % 360

def draw_ring(nodes: list) -> list:
    """Draw an ASCII consistent hashing ring with node positions."""
    if not nodes:
        return ["  (no nodes registered)"]
    
    lines = []
    
    # Calculate positions for each node (0-359 degrees)
    node_positions = []
    for node in nodes:
        pos = get_node_hash_position(node["node_id"])
        node_positions.append((pos, node))
    node_positions.sort(key=lambda x: x[0])
    
    # ASCII ring (simplified 8-segment representation)
    #       0°
    #    7     1
    #   6   ●   2
    #    5     3
    #       4
    
    # Map 360 degrees to 8 segments
    segments = ["·"] * 8
    node_at_segment = [None] * 8
    
    for pos, node in node_positions:
        segment = (pos * 8) // 360
        color = Colors.GREEN if node.get("status") == "alive" else Colors.RED
        symbol = "●" if node.get("status") == "alive" else "✕"
        segments[segment] = f"{color}{symbol}{Colors.RESET}"
        node_at_segment[segment] = node["node_id"]
    
    # Draw the ring
    lines.append(f"                    {segments[0]}           ← 0° (top of ring)")
    lines.append(f"               {segments[7]}         {segments[1]}")
    lines.append(f"              {segments[6]}    ◯    {segments[2]}")
    lines.append(f"               {segments[5]}         {segments[3]}")
    lines.append(f"                    {segments[4]}")
    lines.append("")
    
    # Node position legend with hash ranges
    lines.append(f"  {Colors.BOLD}Node Positions on Ring:{Colors.RESET}")
    for pos, node in node_positions:
        color = Colors.GREEN if node.get("status") == "alive" else Colors.RED
        status_icon = "●" if node.get("status") == "alive" else "✕"
        lines.append(f"    {color}{status_icon}{Colors.RESET} {node['node_id']:10} at {pos:3}°")
    
    # Explain key ownership
    lines.append("")
    lines.append(f"  {Colors.CYAN}Keys are stored on the NEXT node clockwise from their hash position.{Colors.RESET}")
    
    return lines

def draw_key_migration_demo(nodes: list) -> list:
    """Show how adding/removing a node affects key distribution."""
    lines = []
    
    alive_nodes = [n for n in nodes if n.get("status") == "alive"]
    
    if len(alive_nodes) < 2:
        return ["  (need 2+ alive nodes to show migration)"]
    
    # Demo with sample keys
    sample_keys = ["user:alice", "user:bob", "config:db", "session:xyz"]
    
    lines.append(f"  {Colors.BOLD}Sample Key Ownership:{Colors.RESET}")
    lines.append(f"  {'Key':<15} {'Hash°':>6}  {'Owner':<12}")
    lines.append(f"  {'-'*35}")
    
    # Calculate positions
    node_positions = [(get_node_hash_position(n["node_id"]), n) for n in alive_nodes]
    node_positions.sort(key=lambda x: x[0])
    
    for key in sample_keys:
        key_hash = get_node_hash_position(key) 
        
        # Find owner (first node with position >= key_hash, wrap around)
        owner = None
        for pos, node in node_positions:
            if pos >= key_hash:
                owner = node["node_id"]
                break
        if owner is None:
            owner = node_positions[0][1]["node_id"]  # Wrap around
        
        lines.append(f"  {key:<15} {key_hash:>5}°  → {owner:<12}")
    
    # Show what happens if a node dies
    if len(alive_nodes) >= 2:
        lines.append("")
        lines.append(f"  {Colors.YELLOW}💡 If {alive_nodes[0]['node_id']} dies:{Colors.RESET}")
        lines.append(f"     Only keys owned by {alive_nodes[0]['node_id']} move to the next node.")
        lines.append(f"     Other keys stay put! This is why consistent hashing is efficient.")
    
    return lines

def fetch_cluster_status(registry_url: str) -> dict:
    """Fetch cluster status from registry."""
    try:
        resp = requests.get(f"{registry_url}/cluster-status", timeout=2)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

def fetch_node_stats(address: str) -> dict:
    """Fetch stats from a specific node."""
    try:
        resp = requests.get(f"{address}/stats", timeout=1)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

def main():
    registry_url = "http://localhost:5000"
    
    print(f"{Colors.CYAN}🔍 Connecting to Registry at {registry_url}...{Colors.RESET}")
    
    request_log = []
    
    while True:
        clear_screen()
        
        # Header
        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("╔═══════════════════════════════════════════════════════════════════════════════╗")
        print("║                     🌐 DISTRIBUTED CLUSTER DASHBOARD 🌐                       ║")
        print("╚═══════════════════════════════════════════════════════════════════════════════╝")
        print(f"{Colors.RESET}")
        
        # Fetch status
        status = fetch_cluster_status(registry_url)
        
        if not status:
            print(f"\n{Colors.RED}❌ Cannot connect to Registry at {registry_url}{Colors.RESET}")
            print(f"\nMake sure the registry is running:")
            print(f"  python3 workshop_materials/23_resilient_system/registry.py")
            time.sleep(2)
            continue
        
        nodes = status.get("nodes", [])
        health = status.get("health", "unknown")
        
        # Cluster Health Banner
        if health == "healthy":
            health_color = Colors.BG_GREEN
            health_icon = "✓"
        elif health == "degraded":
            health_color = Colors.BG_YELLOW
            health_icon = "!"
        else:
            health_color = Colors.BG_RED
            health_icon = "✕"
        
        print(f"\n  {health_color}{Colors.WHITE}{Colors.BOLD} {health_icon} CLUSTER: {health.upper()} {Colors.RESET}")
        print(f"  Nodes: {status.get('alive_count', 0)}/{status.get('total_nodes', 0)} alive")
        print(f"  Time: {datetime.now().strftime('%H:%M:%S')}")
        
        # Nodes Section
        print(f"\n{Colors.BOLD}┌─── NODES ────────────────────────────────────────────────────────────────────┐{Colors.RESET}")
        
        if not nodes:
            print(f"  {Colors.YELLOW}No nodes registered yet.{Colors.RESET}")
            print(f"  Start nodes with:")
            print(f"    python3 workshop_materials/23_resilient_system/resilient_node.py --port 5001 --id node-1")
        else:
            # Draw nodes side by side
            node_boxes = [draw_node_box(n) for n in nodes]
            max_width = 6  # Lines per box
            
            # Print nodes in rows of 3
            for row_start in range(0, len(node_boxes), 3):
                row_boxes = node_boxes[row_start:row_start+3]
                for line_idx in range(max_width):
                    line = "  "
                    for box in row_boxes:
                        if line_idx < len(box):
                            line += box[line_idx] + "  "
                    print(line)
                print()
        
        print(f"{Colors.BOLD}└──────────────────────────────────────────────────────────────────────────────┘{Colors.RESET}")
        
        # Consistent Hashing Ring
        print(f"\n{Colors.BOLD}┌─── CONSISTENT HASHING RING ─────────────────────────────────────────────────┐{Colors.RESET}")
        ring_lines = draw_ring(nodes)
        for line in ring_lines:
            print(f"  {line}")
        print(f"{Colors.BOLD}└──────────────────────────────────────────────────────────────────────────────┘{Colors.RESET}")
        
        # Key Migration Demo (shows how consistent hashing routes keys)
        print(f"\n{Colors.BOLD}┌─── KEY ROUTING (CONSISTENT HASHING DEMO) ──────────────────────────────────┐{Colors.RESET}")
        migration_lines = draw_key_migration_demo(nodes)
        for line in migration_lines:
            print(f"  {line}")
        print(f"{Colors.BOLD}└──────────────────────────────────────────────────────────────────────────────┘{Colors.RESET}")
        
        # Key Distribution
        print(f"\n{Colors.BOLD}┌─── KEY DISTRIBUTION ────────────────────────────────────────────────────────┐{Colors.RESET}")
        
        total_keys = 0
        for node in nodes:
            if node.get("status") == "alive":
                stats = fetch_node_stats(node.get("address", ""))
                if stats:
                    key_count = stats.get("data_count", 0)
                    total_keys += key_count
                    keys = stats.get("keys", [])
                    
                    bar_width = min(key_count * 2, 40)
                    bar = "█" * bar_width + "░" * (40 - bar_width)
                    
                    print(f"  {node['node_id']:10} │{Colors.CYAN}{bar}{Colors.RESET}│ {key_count} keys")
                    if keys:
                        print(f"             └─ {', '.join(keys[:5])}")
        
        if total_keys == 0:
            print(f"  {Colors.YELLOW}No data stored yet.{Colors.RESET}")
            print(f"  Try: curl -X POST http://localhost:5000/data -H 'Content-Type: application/json' -d '{{\"key\":\"test\",\"value\":\"hello\"}}'")
        
        print(f"{Colors.BOLD}└──────────────────────────────────────────────────────────────────────────────┘{Colors.RESET}")
        
        # Controls
        print(f"\n{Colors.BOLD}┌─── CONTROLS ────────────────────────────────────────────────────────────────┐{Colors.RESET}")
        print(f"  {Colors.CYAN}Kill Node:{Colors.RESET}    curl -X POST http://localhost:5000/kill/node-1")
        print(f"  {Colors.CYAN}Scale Up:{Colors.RESET}     curl -X POST http://localhost:5000/scale-up")
        print(f"  {Colors.CYAN}Write Data:{Colors.RESET}   curl -X POST http://localhost:5000/data -H 'Content-Type: application/json' -d '{{\"key\":\"x\",\"value\":\"y\"}}'")
        print(f"  {Colors.CYAN}Read Data:{Colors.RESET}    curl http://localhost:5000/data/x")
        print(f"  {Colors.MAGENTA}Graduate:{Colors.RESET}     curl http://localhost:5000/graduate")
        print(f"{Colors.BOLD}└──────────────────────────────────────────────────────────────────────────────┘{Colors.RESET}")
        
        print(f"\n  Press {Colors.BOLD}Ctrl+C{Colors.RESET} to exit. Refreshing every 2 seconds...")
        
        time.sleep(2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.CYAN}👋 Dashboard closed.{Colors.RESET}")
        sys.exit(0)
