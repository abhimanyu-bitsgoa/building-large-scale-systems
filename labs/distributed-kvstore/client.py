"""
Distributed KV Store Lab - Client

Client that connects through the gateway for read/write operations.
Core architecture consistent with Lab 1 and Lab 2.
"""

import requests
import argparse
import sys

# ========================
# Configuration
# ========================

DEFAULT_GATEWAY = "http://localhost:8000"

# ========================
# Client Functions
# ========================

def write_data(gateway_url: str, key: str, value: str, verbose: bool = True):
    """Write data through gateway."""
    try:
        resp = requests.post(
            f"{gateway_url}/write",
            json={"key": key, "value": value},
            timeout=30
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if verbose:
                print(f"✅ Write successful: {key}={value}")
                print(f"   Version: {data.get('version')}")
                print(f"   Acks: {data.get('acks')}/{data.get('quorum')}")
            return True, data
        elif resp.status_code == 429:
            if verbose:
                print(f"🚫 Rate limited! Try again later.")
            return False, "Rate limited"
        else:
            error = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
            if verbose:
                print(f"❌ Write failed: {error}")
            return False, error
    
    except requests.exceptions.RequestException as e:
        if verbose:
            print(f"❌ Connection error: {e}")
        return False, str(e)

def read_data(gateway_url: str, key: str, verbose: bool = True):
    """Read data through gateway."""
    try:
        resp = requests.get(f"{gateway_url}/read/{key}", timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if verbose:
                print(f"✅ Read successful: {key}={data.get('value')}")
                print(f"   Version: {data.get('version')}")
                print(f"   Served by: {data.get('served_by')}")
            return True, data
        elif resp.status_code == 404:
            if verbose:
                print(f"❌ Key not found: {key}")
            return False, "Not found"
        elif resp.status_code == 429:
            if verbose:
                print(f"🚫 Rate limited! Try again later.")
            return False, "Rate limited"
        else:
            if verbose:
                print(f"❌ Read failed: {resp.status_code}")
            return False, None
    
    except requests.exceptions.RequestException as e:
        if verbose:
            print(f"❌ Connection error: {e}")
        return False, str(e)

def get_cluster_status(gateway_url: str, verbose: bool = True):
    """Get cluster status through gateway."""
    try:
        resp = requests.get(f"{gateway_url}/cluster-status", timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            if verbose:
                print(f"📊 Cluster Status:")
                
                leader = data.get("leader")
                if leader:
                    icon = "🟢" if leader.get("status") == "alive" else "🔴"
                    print(f"   👑 Leader: {icon} {leader.get('node_id')} @ {leader.get('url')}")
                
                followers = data.get("followers", [])
                print(f"   📋 Followers ({len(followers)}):")
                for f in followers:
                    icon = "🟢" if f.get("status") == "alive" else "🔴"
                    print(f"      {icon} {f.get('node_id')} @ {f.get('url')}")
                
                quorum = data.get("quorum", {})
                print(f"   🔢 Quorum: W={quorum.get('W')} R={quorum.get('R')}")
                print(f"   ✏️  Can Write: {'✅' if quorum.get('can_write') else '❌'}")
                print(f"   📖 Can Read: {'✅' if quorum.get('can_read') else '❌'}")
            
            return True, data
        else:
            if verbose:
                print(f"❌ Failed to get status")
            return False, None
    
    except requests.exceptions.RequestException as e:
        if verbose:
            print(f"❌ Connection error: {e}")
        return False, str(e)

def get_gateway_stats(gateway_url: str, verbose: bool = True):
    """Get gateway statistics."""
    try:
        resp = requests.get(f"{gateway_url}/stats", timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            if verbose:
                print(f"📊 Gateway Stats:")
                gateway = data.get("gateway", {})
                print(f"   Total Requests: {gateway.get('total_requests')}")
                print(f"   Forwarded: {gateway.get('forwarded_requests')}")
                print(f"   Rate Limited: {gateway.get('rate_limited_requests')}")
                print(f"   Errors: {gateway.get('errors')}")
                
                rl = data.get("rate_limiter")
                if rl:
                    print(f"   Rate Limiter: {rl.get('allowed_requests')} allowed, {rl.get('rejected_requests')} rejected")
            
            return True, data
        else:
            return False, None
    
    except requests.exceptions.RequestException as e:
        if verbose:
            print(f"❌ Connection error: {e}")
        return False, str(e)

def graduate(gateway_url: str):
    """Hit the easter egg endpoint!"""
    try:
        resp = requests.get(f"{gateway_url}/graduate", timeout=5)
        if resp.status_code == 200:
            print(resp.text)
            return True
    except:
        print("❌ Could not reach gateway")
    return False

def interactive_mode(gateway_url: str):
    """Interactive client mode."""
    print(f"🖥️  Interactive Client")
    print(f"   Gateway: {gateway_url}")
    print()
    print("Commands:")
    print("   write <key> <value> - Write data")
    print("   read <key>          - Read data")
    print("   status              - Cluster status")
    print("   stats               - Gateway stats")
    print("   graduate            - 🎓 Easter egg!")
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
                write_data(gateway_url, parts[1], " ".join(parts[2:]))
            elif command == "read" and len(parts) >= 2:
                read_data(gateway_url, parts[1])
            elif command == "status":
                get_cluster_status(gateway_url)
            elif command == "stats":
                get_gateway_stats(gateway_url)
            elif command == "graduate":
                graduate(gateway_url)
            elif command in ["quit", "exit", "q"]:
                print("👋 Goodbye!")
                break
            else:
                print(f"Unknown: {cmd}")
            
            print()
        
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except EOFError:
            break

# ========================
# Main
# ========================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Distributed KV Store - Client")
    parser.add_argument("--gateway", type=str, default=DEFAULT_GATEWAY)
    parser.add_argument("command", nargs="?", default="interactive",
                        choices=["write", "read", "status", "stats", "graduate", "interactive"])
    parser.add_argument("--key", "-k", type=str)
    parser.add_argument("--value", "-v", type=str)
    
    args = parser.parse_args()
    
    if args.command == "interactive":
        interactive_mode(args.gateway)
    elif args.command == "write":
        if not args.key or not args.value:
            print("Usage: --key <key> --value <value>")
            sys.exit(1)
        write_data(args.gateway, args.key, args.value)
    elif args.command == "read":
        if not args.key:
            print("Usage: --key <key>")
            sys.exit(1)
        read_data(args.gateway, args.key)
    elif args.command == "status":
        get_cluster_status(args.gateway)
    elif args.command == "stats":
        get_gateway_stats(args.gateway)
    elif args.command == "graduate":
        graduate(args.gateway)
