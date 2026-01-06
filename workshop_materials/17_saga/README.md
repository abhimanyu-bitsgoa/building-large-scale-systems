# Module 17: Saga Pattern (The Distributed Undo)

In a monolithic app, you can use a Database Transaction: `BEGIN -> Write A -> Write B -> COMMIT`. If Write B fails, the DB "Rolls back" A automatically.

But in Microservices? Flight booking is in Service A. Hotel booking is in Service B. There is no shared database to "Roll back".

### The Solution: The Saga Pattern
A Saga is a sequence of local transactions. If one step fails, the system must trigger **Compensating Transactions** to undo the previous successful steps.

### Rules of a Saga
1. Each action `A` must have a corresponding "Undo" action `A-inv`.
2. The orchestrator tracks progress.
3. If failure happens at step `N`, run `Undo(N-1) -> Undo(N-2)... -> Undo(1)`.

### How to Run

Run the simulation:
```bash
python3 workshop_materials/17_saga/saga_orchestrator.py
```

### What to Observe
1. **Scenario 1 (SUCCESS)**:
   - Flight Booked -> Hotel Booked -> Success!
2. **Scenario 2 (FAILURE)**:
   - Flight Booked (Success).
   - Hotel Booking fails.
   - The Orchestrator calls `cancel_flight()`. 
   - Even though the systems are separate, the **State** is eventually consistent (No money was lost for a trip that didn't happen).
