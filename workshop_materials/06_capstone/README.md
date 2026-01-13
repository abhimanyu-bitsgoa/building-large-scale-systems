# Module 06: The Capstone Challenge (Mini)

## 🎯 About This Module

This module serves as a **mid-workshop checkpoint** where you combine Modules 1-5.

For the **Grand Capstone** (combining ALL concepts), see [Module 23: The Resilient System](../23_resilient_system/README.md).

---

## The Challenge

Keep a client running and successfully reading/writing data while the "Chaos Script" randomly kills your nodes.

---

## 🚀 How to Run

### Step 1: Start 3 Nodes
```bash
python3 workshop_materials/01_nodes/node.py --port 5001 --id 1
python3 workshop_materials/01_nodes/node.py --port 5002 --id 2
python3 workshop_materials/01_nodes/node.py --port 5003 --id 3
```

### Step 2: Start Chaos Script
```bash
python3 workshop_materials/chaos/kill_script.py
```

### Step 3: Implement & Run Resilient Client
Edit `workshop_materials/06_capstone/capstone_client.py` and implement:
- `write_quorum()` — Write to W nodes
- `read_quorum()` — Read from R nodes

Then run:
```bash
python3 workshop_materials/06_capstone/capstone_client.py
```

---

## ✅ Victory Condition

Your client prints `"✅ Write Success"` even while nodes are being killed.

---

## 🎓 Ready for More?

Once you've completed this, proceed to **[Module 23: The Resilient System](../23_resilient_system/README.md)** for the full experience with:
- Service Discovery & Heartbeats
- Unified Dashboard
- Dynamic Scaling
- Graduation Easter Egg 🎉
