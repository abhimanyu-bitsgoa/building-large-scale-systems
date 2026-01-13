# Module 18: Byzantine Faults

## 🎯 The Scenario

You ask 3 generals: "Attack or Retreat?"
- General 1: "Attack!"
- General 2: "Attack!"
- General 3: "Retreat!" (traitor or buggy)

With 2 vs 1, you attack. But what if General 3 told other nodes something different?

*How do you reach consensus when nodes might lie?*

---

## 💡 The Concept

### Crash Fault vs Byzantine Fault
| Type | Behavior |
|------|----------|
| Crash | Node is dead. Simple. |
| Byzantine | Node is alive but sends wrong/malicious data. |

### Byzantine Fault Tolerance (BFT)
To tolerate F traitors, you need **3F + 1** nodes.
- 1 traitor → need 4 nodes
- 2 traitors → need 7 nodes

### Where It Matters
- Blockchain (adversarial environment)
- Spacecraft (cosmic ray bit flips)
- Financial systems (compromised nodes)

---

## 🚀 How to Run

```bash
python3 workshop_materials/18_byzantine/byzantine_demo.py
```

**What you'll see:**
- **1 traitor, 3 nodes:** Majority wins, traitor ignored
- **2 traitors, 3 nodes:** Traitors control majority. Consensus broken!

---

## 📚 The Real-World Context

Bitcoin and Ethereum solve Byzantine consensus at global scale using Proof of Work / Proof of Stake—making it economically expensive to be a traitor.

---

## 🏆 Challenge

Research **PBFT (Practical Byzantine Fault Tolerance)**. How many message rounds does it require?
