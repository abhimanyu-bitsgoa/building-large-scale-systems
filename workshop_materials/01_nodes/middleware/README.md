# Node.py Middleware Package

Composable middleware for building resilient distributed systems.

## Quick Start

```bash
# Basic node (no middleware)
python node.py --port 5001 --id node-1

# With rate limiting (5 requests/second)
python node.py --port 5001 --id node-1 --rate-limit 5

# With backpressure (max 50 concurrent requests)
python node.py --port 5001 --id node-1 --backpressure 50

# With circuit breaker
python node.py --port 5001 --id node-1 --circuit-breaker

# With service discovery (requires registry running)
python node.py --port 5001 --id node-1 --registry http://localhost:5000

# All middleware enabled
python node.py --port 5001 --id node-1 \
    --rate-limit 5 \
    --backpressure 50 \
    --circuit-breaker \
    --registry http://localhost:5000
```

## Available Middleware

### Rate Limiter (`--rate-limit N`)

Token bucket rate limiting. Limits each client to N requests per second.

**Student Exercise**: Implement the `is_allowed()` method in `rate_limiter.py`

**Endpoints Added**: None (returns 429 when limit exceeded)

**Test It**:
```bash
# Start node with rate limit
python node.py --port 5001 --id node-1 --rate-limit 3

# Spam requests - should see 429 after first 3
for i in {1..10}; do curl -s -o /dev/null -w "%{http_code}\n" localhost:5001/health; done
```

---

### Backpressure (`--backpressure N`)

Limits concurrent requests. When queue exceeds N, new requests get 429.

**Endpoints Added**: `GET /queue-stats`

**Test It**:
```bash
# Start node with backpressure
python node.py --port 5001 --id node-1 --backpressure 50

# Check queue stats
curl localhost:5001/queue-stats
```

---

### Circuit Breaker (`--circuit-breaker`)

Implements CLOSED → OPEN → HALF_OPEN state machine. Fails fast when downstream is unhealthy.

**Endpoints Added**: `GET /circuit-status`

**Test It**:
```bash
python node.py --port 5001 --id node-1 --circuit-breaker
curl localhost:5001/circuit-status
```

---

### Service Discovery (`--registry URL`)

Auto-registers with a service registry and sends heartbeats.

**Endpoints Added**: `GET /discovery-status`, `GET /peers`

**Test It**:
```bash
# Terminal 1: Start registry
python registry.py --port 5000

# Terminal 2: Start node with SD
python node.py --port 5001 --id node-1 --registry http://localhost:5000

# Check status
curl localhost:5001/discovery-status
curl localhost:5001/peers
```

---

## Load Balancer

The `load_balancer.py` is a separate component that routes requests to multiple nodes.

**Student Exercise**: Implement the `select_node()` method in `LeastConnectionsStrategy`

```bash
# Start 3 nodes with different capacities
python node.py --port 5001 --id node-1 --workers 1 --load-factor 25 &
python node.py --port 5002 --id node-2 --workers 4 --load-factor 25 &
python node.py --port 5003 --id node-3 --workers 1 --load-factor 25 &

# Start load balancer with round robin (observe uneven latencies)
python load_balancer.py --port 8080 --nodes 5001,5002,5003 --strategy round_robin

# After implementing LeastConnectionsStrategy:
python load_balancer.py --port 8080 --nodes 5001,5002,5003 --strategy least_connections
```

---

## Solution Files

If you get stuck, check the `solutions/` folder:

- `token_bucket_solution.py` - Complete `is_allowed()` implementation
- `least_connections_solution.py` - Complete `select_node()` implementation

Just copy the method into your implementation file to see it working!
