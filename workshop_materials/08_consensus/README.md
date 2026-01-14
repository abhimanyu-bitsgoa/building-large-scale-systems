# Module 08: Leader Election (Bully Algorithm)

## 🎯 The Scenario

Your system has 3 nodes. Node 3 is the "leader"—it coordinates writes to ensure consistency.

Node 3 just crashed. The other nodes are still running, but **who's in charge now?**

*How do the remaining nodes agree on a new leader?*

---

## 🧠 Pause and Think

1. If Node 1 and Node 2 both think they should be leader... what happens?
2. How do you break ties?
3. What if the old leader comes back online?

---

## 💡 The Concept

### Leader Election
Choosing a single node to coordinate operations. Only one leader at a time.

### The Bully Algorithm
The node with the **highest ID** always wins.

1. Node detects leader is missing
2. Sends "ELECTION" message to all higher-ID nodes
3. If any respond ("I'm taking over"), wait for them to become leader
4. If none respond, declare yourself leader and announce "VICTORY"

```
Node 1: "Leader is dead. Anyone higher than me?"
Node 2: "I'm higher than you. Sit down."
Node 2: "Anyone higher than me?" (silence)
Node 2: "I am the leader now!"
```

---

## 🚀 How to Run

### Step 1: Start 3 Nodes
```bash
python3 workshop_materials/08_consensus/bully_node.py --port 8001 --id 1 --nodes 1:8001,2:8002,3:8003
python3 workshop_materials/08_consensus/bully_node.py --port 8002 --id 2 --nodes 1:8001,2:8002,3:8003
python3 workshop_materials/08_consensus/bully_node.py --port 8003 --id 3 --nodes 1:8001,2:8002,3:8003
```

### Step 2: Run Visualizer
```bash
python3 workshop_materials/08_consensus/visualize_election.py
```

### Step 3: Kill the Leader
Kill Node 3 (`Ctrl+C`). Watch Node 2 take over.

---

## 📚 The Real Incident

### etcd Upgrade Bug (2024) — Zombie Members

During etcd v3.5 to v3.6 upgrades, a bug caused removed nodes to persist as "zombies" in the membership list.

The cluster thought: "We have 4 nodes. Need 3 votes for quorum."
Reality: "We have 3 nodes. Zombie can't vote."

When one real node went down for maintenance, the remaining 2 couldn't elect a leader (needed 3 votes). Kubernetes clusters froze.

**Lesson:** Leader election depends on accurate membership. Corrupted membership lists break elections.

---

## 🏆 Challenge

The Bully Algorithm is simple but has flaws. What happens if:
1. The highest-ID node has a slow network?
2. A node keeps crashing and restarting, triggering elections?

Research **Raft** for a more robust approach.
