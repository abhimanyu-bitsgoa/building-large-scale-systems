"""
Replication Lab - Client

A simple client that talks to the coordinator for read/write operations.
Core architecture is consistent with Lab 1 (Scalability) for student familiarity.
"""

import requests
import argparse
import time
import sys

# ========================
# Default Configuration
# ========================

DEFAULT_COORDINATOR = "http://localhost:6000"

# ========================
# Client Functions
# ========================

def print_error(label: str, error_data):
    """Print prettified error message."""
    if isinstance(error_data, dict) and "detail" in error_data:
        detail = error_data["detail"]
        if isinstance(detail, dict):
            print(f"❌ {label}: {detail.get('error', 'Unknown Error')}")
            for key, val in detail.items():
                if key != "error":
                    # Title case the key for display
                    display_key = key.replace("_", " ").title()
                    print(f"   {display_key}: {val}")
        else:
            print(f"❌ {label}: {detail}")
    else:
        print(f"❌ {label}: {error_data}")

def write_data(coordinator_url: str, key: str, value: str, verbose: bool = True):
    """Write data through coordinator."""
    try:
        start_time = time.time()
        resp = requests.post(
            f"{coordinator_url}/write",
            json={"key": key, "value": value},
            timeout=30  # Long timeout for replication delay
        )
        latency = (time.time() - start_time) * 1000
        
        if resp.status_code == 200:
            data = resp.json()
            if verbose:
                print(f"✅ Write successful: {key}={value}")
                print(f"   Version: {data.get('version')}")
                print(f"   Acks: {data.get('sync_acks')}/{data.get('quorum')}")
                replicated_to = data.get('sync_replicated_to', [])
                print(f"   Replicated to: {', '.join(replicated_to) if replicated_to else 'None'}")
                print(f"   Latency: {latency:.2f}ms")
            return True, data
        else:
            error = resp.json() if resp.headers.get("content-type") == "application/json" else resp.text
            if verbose:
                print_error("Write failed", error)
            return False, error
    
    except requests.exceptions.RequestException as e:
        if verbose:
            print(f"❌ Connection error: {e}")
        return False, str(e)

def read_data(coordinator_url: str, key: str, verbose: bool = True):
    """Read data through coordinator."""
    try:
        start_time = time.time()
        resp = requests.get(f"{coordinator_url}/read/{key}", timeout=10)
        latency = (time.time() - start_time) * 1000
        
        if resp.status_code == 200:
            data = resp.json()
            if verbose:
                print(f"✅ Read successful: {key}={data.get('value')}")
                print(f"   Version: {data.get('version')}")
                print(f"   Served by: {data.get('served_by')}")
                print(f"   Quorum responses: {data.get('quorum_responses')}")
                print(f"   Latency: {latency:.2f}ms")
            return True, data
        elif resp.status_code == 404:
            if verbose:
                print(f"❌ Key not found: {key}")
            return False, "Not found"
        else:
            error = resp.json() if resp.headers.get("content-type") == "application/json" else resp.text
            if verbose:
                print_error("Read failed", error)
            return False, error
    
    except requests.exceptions.RequestException as e:
        if verbose:
            print(f"❌ Connection error: {e}")
        return False, str(e)

def get_status(coordinator_url: str, verbose: bool = True):
    """Get cluster status from coordinator."""
    try:
        resp = requests.get(f"{coordinator_url}/status", timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            if verbose:
                print(f"📊 Cluster Status:")
                
                # Leader
                leader = data.get("leader")
                if leader:
                    status_icon = "🟢" if leader["status"] == "alive" else "🔴"
                    print(f"   👑 Leader: {status_icon} {leader['node_id']} @ {leader['url']}")
                else:
                    print(f"   👑 Leader: ❌ None")
                
                # Followers
                followers = data.get("followers", [])
                print(f"   📋 Followers ({len(followers)}):")
                for f in followers:
                    status_icon = "🟢" if f["status"] == "alive" else "🔴"
                    print(f"      {status_icon} {f['node_id']} @ {f['url']}")
                
                # Quorum
                quorum = data.get("quorum", {})
                can_write = "✅" if quorum.get("can_write") else "❌"
                can_read = "✅" if quorum.get("can_read") else "❌"
                print(f"   🔢 Quorum: W={quorum.get('W')} R={quorum.get('R')}")
                print(f"   ✏️  Can Write: {can_write}")
                print(f"   📖 Can Read: {can_read}")
            
            return True, data
        else:
            if verbose:
                print(f"❌ Failed to get status: {resp.status_code}")
            return False, None
    
    except requests.exceptions.RequestException as e:
        if verbose:
            print(f"❌ Connection error: {e}")
        return False, str(e)

def interactive_mode(coordinator_url: str):
    """Run interactive client mode."""
    print(f"🖥️  Interactive Client")
    print(f"   Coordinator: {coordinator_url}")
    print()
    print("Commands:")
    print("   write <key> <value> - Write a key-value pair")
    print("   read <key>          - Read a value by key")
    print("   status              - Show cluster status")
    print("   quit                - Exit")
    print()
    
    while True:
        try:
            cmd = input(">>> ").strip()
            if not cmd:
                continue
            
            parts = cmd.split()
            command = parts[0].lower()
            
            if command == "write" and len(parts) >= 3:
                key = parts[1]
                value = " ".join(parts[2:])
                write_data(coordinator_url, key, value)
            
            elif command == "read" and len(parts) >= 2:
                key = parts[1]
                read_data(coordinator_url, key)
            
            elif command == "status":
                get_status(coordinator_url)
            
            elif command in ["quit", "exit", "q"]:
                print("👋 Goodbye!")
                break
            
            else:
                print(f"Unknown command: {cmd}")
                print("Use: write <key> <value>, read <key>, status, quit")
            
            print()
        
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except EOFError:
            break

# ========================
# Main Entry Point
# ========================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replication Lab - Client")
    parser.add_argument("--coordinator", type=str, default=DEFAULT_COORDINATOR,
                        help="Coordinator URL")
    parser.add_argument("command", nargs="?", choices=["write", "read", "status", "interactive"],
                        default="interactive", help="Command to run")
    parser.add_argument("--key", "-k", type=str, help="Key for read/write")
    parser.add_argument("--value", "-v", type=str, help="Value for write")
    
    args = parser.parse_args()
    
    if args.command == "interactive":
        interactive_mode(args.coordinator)
    
    elif args.command == "write":
        if not args.key or not args.value:
            print("Usage: client.py write --key <key> --value <value>")
            sys.exit(1)
        write_data(args.coordinator, args.key, args.value)
    
    elif args.command == "read":
        if not args.key:
            print("Usage: client.py read --key <key>")
            sys.exit(1)
        read_data(args.coordinator, args.key)
    
    elif args.command == "status":
        get_status(args.coordinator)
