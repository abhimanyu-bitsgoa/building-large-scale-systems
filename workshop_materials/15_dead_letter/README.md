# Module 15: Poison Pills & Dead Letter Queues

## 🎯 The Scenario

Your message queue has 1 million messages. Message #500 has malformed JSON.

Your worker:
1. Picks up message #500
2. Tries to parse it → crashes
3. Message goes back to queue (auto-retry)
4. Picks up message #500 again → crashes again

**You're stuck in an infinite loop.** Messages #501-#1,000,000 never get processed.

*How do you get past the bad message?*

---

## 💡 The Concept

### Poison Pill
A message that causes workers to fail repeatedly. Like one bad pill in a bottle.

### Dead Letter Queue (DLQ)
After N failures, move the message to a side queue for human review.

```
Main Queue: [msg1, msg2, POISON, msg4, msg5]
              ↓
Worker: processes msg1 ✓
Worker: processes msg2 ✓
Worker: processes POISON ✗ (retry 1)
Worker: processes POISON ✗ (retry 2)
Worker: processes POISON ✗ (retry 3)
System: "POISON failed 3x, moving to DLQ"
Worker: processes msg4 ✓ (continues!)
```

---

## 🚀 How to Run

```bash
python3 workshop_materials/15_dead_letter/queue_processor.py
```

**What you'll see:**
- Normal messages succeed immediately
- Poison message fails, retries, eventually moves to DLQ
- Other messages continue processing

---

## 📚 The Real Impact

Every major message queue system has DLQ support because poison pills are inevitable:
- AWS SQS, Google Pub/Sub, RabbitMQ, Kafka (via error topics)

Without DLQ, one bad message = complete system halt.

---

## 🏆 Challenge

Implement **Exponential Backoff** for retries:
- Retry 1: Wait 1 second
- Retry 2: Wait 2 seconds
- Retry 3: Wait 4 seconds

This gives transient issues time to resolve.
