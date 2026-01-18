import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
import argparse
import os
import math
import time
import signal
import sys

app = FastAPI()

# Global variables - read from environment (for multi-worker support)
NODE_ID = os.environ.get("NODE_ID", "0")
LOAD_FACTOR = int(os.environ.get("LOAD_FACTOR", 0))

# Store data in-memory
data_store = {}

# Active Request Counter
active_requests = 0

# Middleware instances (set during startup)
sd_middleware = None

class DataPayload(BaseModel):
    key: str
    value: str

@app.middleware("http")
async def active_request_middleware(request: Request, call_next):
    global active_requests
    active_requests += 1
    try:
        response = await call_next(request)
        response.headers["X-Active-Requests"] = str(active_requests)
        response.headers["X-Node-ID"] = str(NODE_ID)
        return response
    finally:
        active_requests -= 1

def simulate_cpu_load(n):
    """
    Calculates Fibonacci(n) inefficiently to simulate CPU load.
    The GIL ensures this creates resource contention for other threads.
    """
    if n <= 0:
        return
    
    start_time = time.time()
    def fib(x):
        if x <= 1: return x
        return fib(x-1) + fib(x-2)
    
    _ = fib(n)
    duration = (time.time() - start_time) * 1000
    print(f"[Node {NODE_ID}] CPU Load: fib({n}) took {duration:.2f}ms")

@app.get("/")
def home():
    return {"message": "Node is running", "id": NODE_ID}

@app.get("/health")
def health():
    return {"status": "ok", "node_id": NODE_ID, "active_requests": active_requests}

@app.get("/stats")
def stats():
    return {
        "node_id": NODE_ID,
        "active_requests": active_requests,
        "load_factor": LOAD_FACTOR
    }

@app.post("/data")
def store_data(payload: DataPayload):
    """Store a key-value pair in this node's data store."""
    if LOAD_FACTOR > 0:
        simulate_cpu_load(LOAD_FACTOR)
        
    data_store[payload.key] = payload.value
    return {
        "status": "stored",
        "node_id": NODE_ID,
        "key": payload.key,
        "value": payload.value
    }

@app.get("/data/{key}")
def get_data(key: str):
    """Retrieve a value by key from this node's data store."""
    if key not in data_store:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found on Node {NODE_ID}")
        
    if LOAD_FACTOR > 0:
        simulate_cpu_load(LOAD_FACTOR)
        
    return {
        "node_id": NODE_ID,
        "key": key,
        "value": data_store[key]
    }


def graceful_shutdown(signum, frame):
    """Handle graceful shutdown - deregister from registry if connected."""
    global sd_middleware
    print(f"\n[Node {NODE_ID}] Shutting down...")
    if sd_middleware:
        sd_middleware.deregister()
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Distributed Node with Composable Middleware")
    
    # Basic node configuration
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--id", type=str, default="0", help="Node ID (string for compatibility)")
    parser.add_argument("--load-factor", type=int, default=0, help="Fibonacci input to simulate CPU load (e.g., 30)")
    parser.add_argument("--workers", type=int, default=1, help="Number of Uvicorn worker processes")
    
    # ═══════════════════════════════════════════════════════════════════
    # MIDDLEWARE FLAGS - Enable features by adding these flags
    # ═══════════════════════════════════════════════════════════════════
    parser.add_argument("--rate-limit", type=int, default=0,
                        help="Enable rate limiting (requests per second). Example: --rate-limit 5")
    parser.add_argument("--backpressure", type=int, default=0,
                        help="Enable backpressure (max queue size). Example: --backpressure 50")
    parser.add_argument("--circuit-breaker", action="store_true",
                        help="Enable circuit breaker pattern")
    parser.add_argument("--registry", type=str, default="",
                        help="Registry URL for service discovery. Example: --registry http://localhost:5000")
    
    # ═══════════════════════════════════════════════════════════════════
    # PHASE 2: DISTRIBUTION FLAGS
    # ═══════════════════════════════════════════════════════════════════
    parser.add_argument("--sharding", type=str, default="", choices=["", "consistent_hash", "modulo"],
                        help="Enable sharding. Example: --sharding consistent_hash --peers 5002,5003")
    parser.add_argument("--peers", type=str, default="",
                        help="Comma-separated peer ports for sharding/gossip. Example: --peers 5002,5003")
    parser.add_argument("--role", type=str, default="", choices=["", "leader", "follower"],
                        help="Replication role. Example: --role leader --followers 5002,5003")
    parser.add_argument("--followers", type=str, default="",
                        help="Comma-separated follower ports (for leader). Example: --followers 5002,5003")
    parser.add_argument("--leader", type=int, default=0,
                        help="Leader port (for follower). Example: --leader 5001")
    parser.add_argument("--leaderless", action="store_true",
                        help="Enable leaderless replication (gossip). Requires --peers")
    parser.add_argument("--replication-delay", type=float, default=0.0,
                        help="Artificial replication delay in seconds (for demos)")
    
    args = parser.parse_args()
    
    # Set environment variables so worker processes inherit them
    os.environ["NODE_ID"] = str(args.id)
    os.environ["LOAD_FACTOR"] = str(args.load_factor)
    
    # Update globals for single-worker mode
    NODE_ID = args.id
    LOAD_FACTOR = args.load_factor
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    
    # ═══════════════════════════════════════════════════════════════════
    # MIDDLEWARE COMPOSITION
    # Add middleware based on CLI flags
    # ═══════════════════════════════════════════════════════════════════
    
    enabled_middleware = []
    
    # Rate Limiting
    if args.rate_limit > 0:
        from middleware import RateLimiterMiddleware
        app.add_middleware(RateLimiterMiddleware, rate=args.rate_limit)
        enabled_middleware.append(f"RateLimiter({args.rate_limit}/sec)")
    
    # Backpressure
    if args.backpressure > 0:
        from middleware.backpressure import BackpressureMiddleware, add_backpressure_stats_endpoint
        bp_mw = BackpressureMiddleware(app, max_queue_size=args.backpressure)
        # Note: For ASGI we need to wrap differently, but for demo purposes
        # we'll add the endpoint that shows backpressure stats
        add_backpressure_stats_endpoint(app, bp_mw)
        enabled_middleware.append(f"Backpressure(queue={args.backpressure})")
    
    # Circuit Breaker  
    if args.circuit_breaker:
        from middleware.circuit_breaker import CircuitBreakerMiddleware, add_circuit_status_endpoint
        cb_mw = CircuitBreakerMiddleware(app, failure_threshold=3, recovery_timeout=5)
        add_circuit_status_endpoint(app, cb_mw)
        enabled_middleware.append("CircuitBreaker(threshold=3)")
    
    # Service Discovery
    if args.registry:
        from middleware.service_discovery import ServiceDiscoveryMiddleware, add_discovery_endpoints
        sd_middleware = ServiceDiscoveryMiddleware(
            app,
            node_id=args.id,
            node_port=args.port,
            registry_url=args.registry
        )
        add_discovery_endpoints(app, sd_middleware)
        enabled_middleware.append(f"ServiceDiscovery({args.registry})")
    
    # ═══════════════════════════════════════════════════════════════════
    # PHASE 2: DISTRIBUTION MIDDLEWARE
    # ═══════════════════════════════════════════════════════════════════
    
    # Parse peer ports
    peer_ports = [int(p.strip()) for p in args.peers.split(",") if p.strip()]
    
    # Sharding
    if args.sharding:
        from middleware.sharding import ShardingMiddleware, add_sharding_endpoints
        sharding_mw = ShardingMiddleware(
            app,
            node_id=args.id,
            node_port=args.port,
            peers=peer_ports,
            strategy=args.sharding
        )
        add_sharding_endpoints(app, sharding_mw, data_store)
        enabled_middleware.append(f"Sharding({args.sharding})")
    
    # Leader-Follower Replication
    if args.role:
        from middleware.replication import ReplicationMiddleware, add_replication_endpoints
        follower_ports = [int(p.strip()) for p in args.followers.split(",") if p.strip()]
        replication_mw = ReplicationMiddleware(
            app,
            node_id=args.id,
            node_port=args.port,
            role=args.role,
            leader_port=args.leader if args.leader else None,
            follower_ports=follower_ports if follower_ports else None,
            replication_delay=args.replication_delay
        )
        add_replication_endpoints(app, replication_mw, data_store)
        if args.role == "leader":
            enabled_middleware.append(f"Replication(leader→{len(follower_ports)} followers)")
        else:
            enabled_middleware.append(f"Replication(follower→leader:{args.leader})")
    
    # Leaderless Replication (Gossip)
    if args.leaderless:
        from middleware.leaderless_replication import LeaderlessReplicationMiddleware, add_leaderless_endpoints
        leaderless_mw = LeaderlessReplicationMiddleware(
            app,
            node_id=args.id,
            node_port=args.port,
            peers=peer_ports
        )
        add_leaderless_endpoints(app, leaderless_mw, data_store)
        enabled_middleware.append(f"LeaderlessReplication({len(peer_ports)} peers)")
    
    # ═══════════════════════════════════════════════════════════════════
    # STARTUP
    # ═══════════════════════════════════════════════════════════════════
    
    print(f"🚀 Starting Node '{args.id}' on port {args.port}")
    print(f"   Load Factor: {args.load_factor}")
    print(f"   Workers: {args.workers}")
    
    if enabled_middleware:
        print(f"   Middleware: {', '.join(enabled_middleware)}")
    else:
        print("   Middleware: None (use --help to see options)")
    
    print()
    
    if args.workers > 1:
        # Get the directory where this script is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Pass the directory to Uvicorn so workers can find 'node:app'
        uvicorn.run("node:app", host="0.0.0.0", port=args.port, workers=args.workers, app_dir=current_dir)
    else:
        uvicorn.run(app, host="0.0.0.0", port=args.port)

