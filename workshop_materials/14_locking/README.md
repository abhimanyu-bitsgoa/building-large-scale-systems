# Module 14: Distributed Locking (The Ticket Race)

In a single-server app, you can use a "Mutex" or "Semaphore" to stop two threads from touching the same data. But in a distributed system, your code is running on 10 different machines. Memory is not shared.

How do you prevent two users from booking the **last seat** on a plane at the exact same millisecond?

### Distributed Locking
You use an external "Lock Coordinator" (like Redis, Zookeeper, or Etcd). Before any node does a sensitive action, it must:
1. "Acquire" a global lock.
2. Perform the action.
3. "Release" the lock.

If another node tries to acquire the same lock, it's told "No, someone else has it".

### How to Run

1. **Start the Lock Server**:
   ```bash
   python3 workshop_materials/14_locking/lock_server.py
   ```

2. **Run the Visualizer**:
   ```bash
   python3 workshop_materials/14_locking/visualize_locking.py
   ```

3. **Simulate the Race**:
   Open two terminals and run these as close together as possible:
   **Terminal A**:
   ```bash
   python3 workshop_materials/14_locking/book_ticket.py --id Node_Alpha
   ```
   **Terminal B**:
   ```bash
   python3 workshop_materials/14_locking/book_ticket.py --id Node_Beta
   ```

### What to Observe
- One node will succeed and say "Lock ACQUIRED!".
- The other node will immediately fail and say "Permission DENIED".
- The Successful node holds the lock for 2 seconds (simulating work) and then releases it.
- If a node crashes while holding a lock, the `ttl` (Time To Live) ensures the lock eventually expires so the system doesn't stay stuck forever.
