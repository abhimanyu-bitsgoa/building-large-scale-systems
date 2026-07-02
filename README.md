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

Inside the container, run the preflight check — it verifies Python, the workshop
libraries, tmux, and boots a real node end-to-end (~15 seconds):

```bash
cd build-kvstore
make verify
```

If you see the **`SETUP VERIFIED`** banner, you're ready for the workshop. If any
line shows `[FAIL]`, it prints the one-line fix next to it — apply it and re-run.

> **Please run this the day before the workshop** — the first `docker-compose up -d`
> downloads and builds the image; don't save that for conference wifi.

### Platform notes

- **Windows:** run the `docker-compose` commands from **PowerShell or Windows
  Terminal** — not Git Bash. (Git Bash's terminal breaks `docker-compose exec`
  with *"the input device is not a TTY"*, and legacy consoles render the
  dashboards poorly.)
- **`docker-compose` vs `docker compose`:** newer Docker Desktop installs ship the
  command as `docker compose` (with a space). If `docker-compose` says *command
  not found*, use `docker compose` — same arguments everywhere.
- **Linux:** start the Docker daemon first if needed (`sudo systemctl start docker`).

***Once done, please register your completion [here](https://forms.gle/fBfvTbLwgAKH13yd9)***

---

## Workshop Structure

| Lab                                                               | Topic                          | What You'll Learn                                                                   |
| ----------------------------------------------------------------- | ------------------------------ | ----------------------------------------------------------------------------------- |
| [**Scalability**](labs/scalability/README.md)                  | Load Balancing & Rate Limiting | Horizontal scaling, load distribution strategies, protecting services from overload |
| [**Replication**](labs/replication/README.md)                  | Leader-Follower Replication    | Write quorums, read quorums, sync vs async replication, consistency tradeoffs       |
| [**Distributed KV Store**](labs/distributed-kvstore/README.md) | Full System Integration        | Service discovery, heartbeats, automatic failover, combining everything together    |

Each lab has its own `README.md` with step-by-step demos. Start with **Scalability** and work your way up!
