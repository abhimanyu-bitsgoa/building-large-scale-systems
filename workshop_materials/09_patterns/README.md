# Module 09: Circuit Breaker Pattern

## 🎯 The Scenario

Your checkout service calls the Payment service. The Payment service is having a bad day—every request takes 30 seconds and then fails.

You have 1,000 users trying to check out. Each one waits 30 seconds... then fails. Meanwhile, your checkout service threads are exhausted. Soon **your entire website is unresponsive**.

*How do you stop one failing service from taking down everything?*

---

## 🧠 Pause and Think

1. If you know a service is failing, why keep hitting it?
2. How do you know when to "give up" and when to "try again"?
3. What should happen when the failing service recovers?

---

## 💡 The Concept

A **Circuit Breaker** is like an electrical circuit breaker: it "trips" when there's a problem.

### The Three States

```
     ┌──────────────────────────────────────┐
     │                                      │
     ▼                                      │
┌─────────┐    Failures > threshold    ┌─────────┐
│ CLOSED  │ ─────────────────────────► │  OPEN   │
└─────────┘                            └─────────┘
     ▲                                      │
     │                                      │ Timeout expires
     │                                      ▼
     │                               ┌───────────┐
     │  Success                      │ HALF-OPEN │
     └───────────────────────────────┴───────────┘
                  Failure (back to OPEN)
```

- **CLOSED:** Normal operation. Requests pass through.
- **OPEN:** Failing. All requests **immediately fail** (fast-fail). No waiting.
- **HALF-OPEN:** After timeout, allow ONE request through. If it succeeds, close. If it fails, reopen.

---

## 🚀 How to Run

### Step 1: Start the Flaky Server
```bash
python3 workshop_materials/09_patterns/flaky_server.py
```

### Step 2: Run the Visualizer
```bash
cd workshop_materials/09_patterns
python3 visualize_breaker.py
```

### Step 3: Trigger Failure
```bash
curl -X POST http://localhost:9001/fail
```

**Watch the visualizer:** After 3 failures, the circuit OPENS. Errors now say "(Fast Fail)"—no waiting!

### Step 4: Recover
```bash
curl -X POST http://localhost:9001/recover
```

**Watch the visualizer:** After 5 seconds, state moves to HALF-OPEN. One successful request closes the circuit.

---

## 🎮 Micro-Challenge

Before triggering `/fail`:
1. Predict: Exactly how many requests will fail before the circuit opens?
2. Time yourself: How long until you see "OPEN" in the visualizer?

---

## 📚 The Real Incident

### The Netflix Origin of Circuit Breakers

Netflix engineers invented the circuit breaker pattern (popularized in Hystrix) after experiencing cascading failures:

1. A single downstream service starts timing out
2. Calling services exhaust their thread pools waiting
3. Other services can't get threads to process requests
4. The entire system halts

With circuit breakers:
- Once a service is known-bad, stop calling it immediately
- Return a fallback (cached data, error message, degraded experience)
- Periodically check if it's recovered

**Lesson:** "Fail fast" is better than "wait and fail." Circuit breakers prevent cascading failures by **isolating** broken components.

---

## 🏆 Challenge

Implement a **Bulkhead** pattern alongside the circuit breaker:

Instead of one shared thread pool, create separate pools for each downstream service. If Payment is exhausting its threads, Inventory and Shipping can still operate.
