# Module 12: Backpressure

## 🎯 The Scenario

Your producer generates 1,000 messages per second. Your consumer can only process 100 messages per second.

The queue grows: 900... 9,000... 90,000... Eventually **your server runs out of memory and crashes**.

*What should happen when the consumer can't keep up?*

---

## 🧠 Pause and Think

1. Should you drop messages when the queue is full?
2. Should you slow down the producer?
3. Should you add more consumers?

---

## 💡 The Concept

**Backpressure** is when a slow consumer tells a fast producer: "Slow down, I can't keep up!"

### Without Backpressure
```
Producer: 🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀 (100/sec)
Queue:    [💾💾💾💾💾💾💾💾💾💾💾💾💾💾💾...] (growing forever)
Consumer: 🐢 (10/sec)
Result:   💥 Out of memory!
```

### With Backpressure
```
Producer: 🚀🚀🚀🚀... (blocked when queue full)
Queue:    [💾💾💾💾💾] (bounded size)
Consumer: 🐢 (10/sec, at its own pace)
Result:   ✅ Stable system
```

### Strategies
| Strategy | Behavior |
|----------|----------|
| **Block** | Producer waits until queue has space |
| **Drop** | Newest messages are dropped |
| **Sample** | Keep only 1 in N messages |
| **Load Shed** | Return errors to clients |

---

## 🚀 How to Run

### Step 1: Start Consumer (No Backpressure)
```bash
python3 workshop_materials/12_backpressure/consumer.py --port 12000
```

### Step 2: Run Visualizer
```bash
python3 workshop_materials/12_backpressure/visualize_backpressure.py
```

### Step 3: Start Producer
```bash
python3 workshop_materials/12_backpressure/producer.py --rate 0.05
```

**What you'll see:** Buffer fills up, messages get dropped.

---

### Now Try With Backpressure

```bash
# Restart consumer with backpressure enabled
python3 workshop_materials/12_backpressure/consumer.py --port 12000 --backpressure
```

**What you'll see:** Buffer stays bounded, "Dropped" stays at 0, throughput slows to match consumer speed.

---

## 🎮 Micro-Challenge

1. Run without backpressure at `--rate 0.01` (very fast producer)
2. Count how many messages are dropped in 30 seconds
3. Enable backpressure and repeat
4. **Question:** What's the trade-off? (Hint: What happens to producer latency?)

---

## 📚 The Real Incident

### OpenAI — December 2024 (API Server Overload)

OpenAI's telemetry service was sending data faster than the Kubernetes API server could handle. Without proper backpressure:

1. Telemetry flooded the API server
2. API server couldn't respond to health checks
3. Control plane stalled
4. ChatGPT went offline

The irony: The system that was supposed to *monitor* health broke the *actual* health checks.

**Lesson:** Internal services need rate limits and backpressure just like external APIs.

---

## 🏆 Challenge

Implement **Adaptive Backpressure**:

Instead of a fixed queue size, dynamically adjust based on:
- Consumer processing speed (measure it!)
- Memory usage
- Latency targets

When the system is fast, allow a larger queue. When it slows down, shrink the queue immediately.
