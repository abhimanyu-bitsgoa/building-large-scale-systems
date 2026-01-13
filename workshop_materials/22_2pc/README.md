# Module 22: 2-Phase Commit (2PC)

We previously looked at **Sagas** (Module 17), which use "Eventual Consistency" and compensating actions to undo failures. But what if you need **Strict Consistency**? 

For example, when moving money between two different banks, you absolutely cannot have a state where money has left Bank A but hasn't arrived at Bank B, even for a second.

### The Solution: 2-Phase Commit
2PC is a protocol that ensures an "All or Nothing" atomicity across multiple nodes. It uses a **Coordinator** to manage the process in two phases:

#### Phase 1: Prepare (Voting)
1. The Coordinator asks all nodes: "Are you ready to commit this change?"
2. Each node checks its local state (e.g. "Do I have enough balance?").
3. Each node sends a "Vote" (READY or ABORT).

#### Phase 2: Execution (Decision)
1. If **ALL** nodes voted READY: The Coordinator sends a `COMMIT` signal. The change becomes permanent.
2. If **ANY** node voted ABORT: The Coordinator sends a `ROLLBACK` signal. Everyone discards the changes.

### 2PC vs Sagas
- **2PC**: Consistent, but blocks resources until the final decision (Slow).
- **Sagas**: Highly available and non-blocking, but allows "Temporary Inconsistency" (Fast).

### How to Run

Run the simulation:
```bash
python3 workshop_materials/22_2pc/two_phase_commit.py
```

### What to Observe
1. **Scenario 1 (Success)**: Both nodes vote READY, and both commit.
2. **Scenario 2 (Partial Failure)**: Node Beta crashes or votes ABORT during the prepare phase. The Coordinator forces both nodes to Rollback. The money never leaves Bank Alpha.
