# Building Large Scale Systems: The Workshop

Welcome to **Building Large Scale Systems**! Learn how to build resilient distributed systems from scratch through hands-on labs.

## Quick Start (Docker)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### 1. Clone and Start

```bash
git clone https://github.com/abhimanyu-bitsgoa/building-large-scale-systems.git
cd building-large-scale-systems

# Build and start the container (Make sure Docker is UP & RUNNING before this step)
docker-compose up -d

# Enter the workshop environment
docker-compose exec workshop bash
```

### 2. Verify Setup

Inside the container, test a simple node:

```bash
python labs/scalability/node.py --port 5001 --id 1
```

If you see `Node 1 starting on port 5001`, you're ready!

---

## Workshop Structure

| Lab                                                               | Topic                          | What You'll Learn                                                                   |
| ----------------------------------------------------------------- | ------------------------------ | ----------------------------------------------------------------------------------- |
| [**Scalability**](labs/scalability/README.md)                  | Load Balancing & Rate Limiting | Horizontal scaling, load distribution strategies, protecting services from overload |
| [**Replication**](labs/replication/README.md)                  | Leader-Follower Replication    | Write quorums, read quorums, sync vs async replication, consistency tradeoffs       |
| [**Distributed KV Store**](labs/distributed-kvstore/README.md) | Full System Integration        | Service discovery, heartbeats, automatic failover, combining everything together    |

Each lab has its own `README.md` with step-by-step demos. Start with **Scalability** and work your way up!
