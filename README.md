# Building Large Scale Systems: The Workshop 🏗️

Welcome to **Building Large Scale Systems**! Learn how to build resilient distributed systems from scratch through hands-on labs.

## 🚀 Quick Start (Docker)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### 1. Clone and Start

```bash
git clone <repository-url>
cd building-large-scale-systems

# Build and start the container
docker-compose up -d

# Enter the workshop environment
docker-compose exec workshop bash
```

### 2. Verify Setup

Inside the container, test a simple node:

```bash
python labs/scalability/node.py --port 5001 --id 1
```

If you see `🚀 Node 1 starting on port 5001`, you're ready!

---

## 📂 Workshop Structure

| Lab                                                               | Topic                          | What You'll Learn                                                                   |
| ----------------------------------------------------------------- | ------------------------------ | ----------------------------------------------------------------------------------- |
| [**Scalability**](labs/scalability/README.md)                  | Load Balancing & Rate Limiting | Horizontal scaling, load distribution strategies, protecting services from overload |
| [**Replication**](labs/replication/README.md)                  | Leader-Follower Replication    | Write quorums, read quorums, sync vs async replication, consistency tradeoffs       |
| [**Distributed KV Store**](labs/distributed-kvstore/README.md) | Full System Integration        | Service discovery, heartbeats, automatic failover, combining everything together    |

Each lab has its own `README.md` with step-by-step demos. Start with **Scalability** and work your way up!

---

## 🔧 Alternative Setup (Without Docker)

If you prefer running locally without Docker:

<details>
<summary><strong>macOS</strong></summary>

```bash
# Install Python (if needed)
brew install python@3.11

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

</details>

<details>
<summary><strong>Linux (Ubuntu/Debian)</strong></summary>

```bash
# Install Python (if needed)
sudo apt update && sudo apt install python3 python3-pip python3-venv

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

</details>

<details>
<summary><strong>Windows</strong></summary>

```powershell
# Option 1: Use WSL2 (Recommended) - Then follow Linux instructions

# Option 2: Native Windows
# Download Python from https://www.python.org/downloads/
# During install, check "Add Python to PATH"

# In PowerShell:
python -m venv venv
.\venv\Scripts\Activate

pip install -r requirements.txt
```

</details>

---

## 📡 Port Reference (Internal)

The following ports are used **inside the container**. Note: These are not exposed to your Mac's host to avoid system port conflicts.

| Lab            | Component          | Port      |
| -------------- | ------------------ | --------- |
| Scalability    | Nodes              | 5001-5003 |
| (Note)         | Skip Port 5000     | N/A       |
| Replication    | Coordinator        | 6000      |
| Replication    | Leader + Followers | 6001-6004 |
| Distributed KV | Coordinator        | 7000      |
| Distributed KV | Gateway            | 8000      |
| Distributed KV | Registry           | 9000      |

---

## 🎓 Certificate of Completion

After finishing all labs, run this in the Distributed KV Store lab:

```bash
curl http://localhost:8000/graduate
```

**Happy Building!** 🏗️
