# Module 13: Replication Lag (Read-Your-Writes)

In a distributed database, writes usually go to a "Primary" node, which then "replicates" that data to "Secondary" nodes. 

But what happens if you write a profile update and then immediately refresh the page? If your refresh (read) hits a Secondary node that hasn't caught up yet, you'll see your **old** profile. This is **Replication Lag**.

### The Problem: Ghost Updates
A user updates their name to "Alice". The Primary accepts it. The user refreshes. The Load Balancer sends the read to Secondary 1. Secondary 1 hasn't received the replication yet. The user still sees their old name.

### How to Run

1. **Start the Primary Node**:
   ```bash
   python3 workshop_materials/13_replication/primary.py --port 13000 --secondaries 13001,13002 --delay 5
   ```

2. **Start the Secondary Nodes** (separate terminals):
   ```bash
   python3 workshop_materials/13_replication/secondary.py --port 13001 --id 1
   python3 workshop_materials/13_replication/secondary.py --port 13002 --id 2
   ```

3. **Run the Visualizer**:
   ```bash
   python3 workshop_materials/13_replication/visualize_lag.py
   ```

4. **Trigger a Write**:
   ```bash
   curl -X POST http://localhost:13000/write \
     -H "Content-Type: application/json" \
     -d '{"key": "user_1", "value": "Alice"}'
   ```

### What to Observe
- The Primary updates immediately.
- The Secondaries stay as "NONE" for 5 full seconds.
- This is why "Read-Your-Writes" consistency is a huge challenge in large-scale systems (often solved by pinning a user to the Primary for a short duration after a write).
