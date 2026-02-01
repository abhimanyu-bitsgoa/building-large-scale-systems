# Scalability Lab

Learn about load balancing and rate limiting through hands-on experimentation.

## Overview

This lab demonstrates:

- **Vertical scaling limits**: How a single node gets overwhelmed
- **Horizontal scaling**: Distributing load across multiple nodes
- **Load balancing strategies**: Round-robin vs adaptive routing
- **Rate limiting**: Protecting nodes from overload with fixed window algorithm

## Files

| File                 | Description                                       |
| -------------------- | ------------------------------------------------- |
| `node.py`          | Server node with rate limiting support            |
| `client.py`        | Client with load balancing integration            |
| `load_balancer.py` | Load balancing strategies (round-robin, adaptive) |
| `rate_limiter.py`  | Rate limiting with fixed window algorithm         |

---

## Demo 1: Single Node Choking

**Goal**: See how a single node gets overwhelmed with concurrent requests.

### Step 1: Start a single node

```bash
# Terminal 1: Start node with load simulation
python labs/scalability/node.py --port 5001 --id 1 --load-factor 35
```

### Step 2: Hit with the expected load

```bash
# Terminal 2: Run client with serial request load
python labs/scalability/client.py --target http://localhost:5001  --requests 30 --verbose
```

### Step 3: Hit it with more than expected concurrent requests

```bash
# Terminal 3: Run client with high concurrency
python labs/scalability/client.py --target http://localhost:5001 --concurrent 10 --requests 30 --verbose
```

**Observe**: Watch the latency increase dramatically as the single node struggles.

### Step 4: Simulate vertical scaling

```bash
# Terminal 1: Start node with load simulation
python labs/scalability/node.py --port 5001 --id 1 --load-factor 35 --workers 5
```

**Observe**: Watch the latency go down as the node can handle more requests.

## Demo 2: Horizontal Scaling with Load balancer

**Goal**: Distribute load across multiple nodes.

### Step 1: Start 3 nodes with different capacities

```bash
# Terminal 1: Low capacity node (1 worker)
python labs/scalability/node.py --port 5001 --id 1 --load-factor 35 --workers 5

# Terminal 2: Medium capacity node (2 workers)
python labs/scalability/node.py --port 5002 --id 2 --load-factor 35 --workers 5

# Terminal 3: High capacity node (4 workers)
python labs/scalability/node.py --port 5003 --id 3 --load-factor 35
```

### Step 2: Run client with a load balancer

```bash
# Terminal 4: Run client with round-robin strategy
python labs/scalability/client.py --concurrent 20 --requests 100 --strategy round_robin
```

**Observe**: Requests are distributed equally, but the low-capacity node has higher latency.

### Step 3: Try client with different strategies

You can try running it with **adaptive** or **weighted** & notice the distribution & latency change

```bash
# Terminal 4: Run client with round-robin strategy
python labs/scalability/client.py --concurrent 20 --requests 100 --strategy adaptive
```

---

## Demo 3: Rate Limiting

**Goal**: See rate limiting in action with HTTP 429 responses.

### Step 1: Start a node with rate limiting

```bash
# Terminal 1: Node with rate limiting (5 requests per 10 seconds)
python labs/scalability/node.py --port 5001 --id 1 --rate-limit fixed_window --rate-limit-max 5 --rate-limit-window 10
```

### Step 2: Flood the node with requests

```bash
# Terminal 2: High concurrency without delay
python labs/scalability/client.py --target http://localhost:5001 --concurrent 10 --requests 50 --verbose
```

**Observe**:

- First 5 requests succeed (✅)
- Subsequent requests get rate limited (🚫 429)
- You can try allowing 10 requests in 10 seconds & see how your performance metrics change.

### Step 3: Respectful client with rate delay

```bash
# Terminal 3: Slower client respects rate limit
python labs/scalability/client.py --target http://localhost:5001 --concurrent 1 --rate 2 --requests 10 --verbose
```

**Observe**: All requests succeed because we're under the rate limit.

---

## Key Takeaways

1. **Single nodes have limits**: CPU, memory, and network all bottleneck
2. **Horizontal scaling helps**: More nodes = more capacity
3. **Naive load balancing (round-robin)**: Simple but ignores node capacity
4. **Adaptive load balancing**: Considers response time and load
5. **Rate limiting protects resources**: Prevents abuse, ensures fairness

---

## TODO Sections (For Students)

Look for `TODO: [STUDENT EXERCISE]` comments in:

- `node.py` - Core rate limiting logic
- `rate_limiter.py` - Fixed window algorithm implementation

These sections contain the key algorithms that students can study and modify.
