# Building Large Scale Systems: The Workshop 🏗️

Welcome to **InstaScale**! In this workshop, you will learn how to build a resilient distributed system from scratch.

## 🚀 Instant Start

### 1. Open in VS Code with Docker
This repository is configured with a `.devcontainer` (via Dockerfile).
- **VS Code**: Click "Reopen in Container".
- **Manual**:
  ```bash
  docker-compose up -d
  docker-compose exec workshop bash
  ```

### 2. Verify Setup
Inside the container/terminal, run:
```bash
python3 workshop_materials/03_sharding/visualize_rebalancing.py
```
If you see a bar chart, you are ready to go!

## 📂 Workshop Structure

- **`workshop_materials/`**: Your workspace. Contains skeleton code and visualization tools.
    - `01_nodes/`: Module 1 (Processes & RPC)
    - `02_networking/`: Module 2 (Load Balancing & Rate Limiting)
    - `03_sharding/`: Module 3 (Sharding & Consistent Hashing)
    - `05_availability/`: Module 5 (Quorums)
- **`solutions/`**: Reference implementations (Don't peek unless stuck! 😉)

## 🧪 Visualizations
Each module has a `visualize_*.py` script. Run these to understand the "Why" before you write the code.

Happy Coding!
