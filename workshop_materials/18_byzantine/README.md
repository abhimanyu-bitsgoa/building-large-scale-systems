# Module 18: Byzantine Faults (The Traitor Node)

Most distributed systems assume nodes are either **Alive** or **Dead** (Crash-stop failure). But what if a node is alive and healthy, but sends **Wrong** or **Malicious** data?

This is a **Byzantine Fault**.

### The Problem
If a client asks 3 nodes for a balance and gets:
- Node 1: "$100"
- Node 2: "$100"
- Node 3: "$9,999,999"

Who should the client trust? If Node 3 is compromised or has a buggy CPU, it's a "Traitor".

### Byzantine Fault Tolerance (BFT)
A system is Byzantine Fault Tolerant if it can reach a correct consensus even when some nodes are lying. Mathematically, to tolerate $F$ traitors, you usually need $3F + 1$ total nodes.

### How to Run

Run the simulation:
```bash
python3 workshop_materials/18_byzantine/byzantine_demo.py
```

### What to Observe
1. **Scenario 1 (1 Traitor)**:
   - 2 nodes say "ATTACK", 1 node says "RETREAT".
   - The majority still wins. The "Traitor" is ignored.
2. **Scenario 2 (2 Traitors)**:
   - 1 node says "ATTACK", 2 nodes say "RETREAT".
   - The system is now compromised. In this simple demo, the traitors "won" because they have the majority. This shows why critical systems (like Blockchain or Spacecraft) need higher node counts and cryptographic signatures to prevent this!
