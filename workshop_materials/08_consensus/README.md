# Module 08: Leader Election (Bully Algorithm)

In a distributed system, sometimes you need one node to be "the boss" (e.g., to coordinate writes, manage a database, or assign tasks). But what happens if the leader dies?

The cluster must **Elect** a new one.

### The Bully Algorithm
This algorithm is called "Bully" because nodes with higher IDs will always "bully" their way into leadership over lower-ID nodes.

1. **Failure Detection**: When a node notices the leader isn't responding, it starts an election.
2. **The "Election" Message**: It asks all nodes with a higher ID: "Are any of you alive?".
3. **The "Alive" Response**: If a higher node is alive, it says "Yes, I'll take it from here" and starts its own election.
4. **Victory**: If no higher node responds, the initiating node declares itself the leader and tells everyone ("Coordinator" message).
5. **The Bully**: If a highest-ID node recovers, it immediately starts an election and takes over.

### How to Run

1. **Start 3 Bully Nodes**:
   ```bash
   # In Terminal 1
   python3 workshop_materials/08_consensus/bully_node.py --port 8001 --id 1 --nodes 1:8001,2:8002,3:8003
   
   # In Terminal 2
   python3 workshop_materials/08_consensus/bully_node.py --port 8002 --id 2 --nodes 1:8001,2:8002,3:8003

   # In Terminal 3
   python3 workshop_materials/08_consensus/bully_node.py --port 8003 --id 3 --nodes 1:8001,2:8002,3:8003
   ```

2. **Run the Visualizer**:
   ```bash
   python3 workshop_materials/08_consensus/visualize_election.py
   ```

3. **Kill the Leader**:
   Kill Node 3 (the highest ID). Watch Node 1 and 2 detect the crash and elect Node 2.

4. **The Bully Returns**:
   Restart Node 3. Watch it take leadership back from Node 2 instantly!
