# Module 15: Poison Pills & Dead Letter Queues (DLQ)

In a message-based system (like RabbitMQ, SQS, or Kafka), what happens if a message is "bad"? 
Maybe it has malformed JSON, or a negative number where a positive one should be.

Your worker picks it up -> Crashes -> Message goes back to the queue (Automatic Retry) -> Worker picks it up again -> Crashes again.

This is an **Infinite Retry Loop**. It wastes CPU, fills up logs, and can eventually crash your entire worker farm.

### The Solution: Dead Letter Queue (DLQ)
We track how many times a specific message has failed. If it fails more than $N$ times (e.g., 3), we decide it's a "Poison Pill" and move it to a separate side-queue called a **Dead Letter Queue**.

This allows the system to:
1. Continue processing other "healthy" messages.
2. Alert an engineer to look at the "Dead" messages manually.

### How to Run

Run the simulation:
```bash
python3 workshop_materials/15_dead_letter/queue_processor.py
```

### What to Observe
- Message 1 (Normal) succeeds instantly.
- Message 2 (**POISON_PILL**) fails. It gets retried.
- You'll see Message 3 and 4 get processed *between* retries of Message 2.
- After 3 failures, Message 2 is moved to the **DLQ**, and the program finishes successfully. 
- Without a DLQ, this program would run forever!
