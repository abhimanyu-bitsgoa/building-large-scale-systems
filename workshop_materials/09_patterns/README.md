# Module 09: Circuit Breaker Pattern

If a downstream service is failing or slow, why keep hitting it? 
Hitting a failing service just wastes resources, increases latency, and can cause **Cascading Failures** across your entire system.

The **Circuit Breaker** pattern protects your system by "opening the circuit" when failures cross a threshold.

### The States
1. **CLOSED**: Everything is normal. Requests go through.
2. **OPEN**: Too many failures happened. The breaker "trips" and blocks all requests immediately (Fast Fail). This gives the failing service time to recover.
3. **HALF-OPEN**: After a timeout, the breaker lets *one* request through. If it succeeds, the circuit is CLOSED. If it fails, it goes back to OPEN.

### How to Run

1. **Start the Flaky Server**:
   ```bash
   python3 workshop_materials/09_patterns/flaky_server.py
   ```

2. **Run the Visualizer**:
   ```bash
   # Make sure you are in the same directory as circuit_breaker.py or it's in your PYTHONPATH
   cd workshop_materials/09_patterns
   python3 visualize_breaker.py
   ```

3. **Trigger a Failure**:
   Tell the server to start failing:
   ```bash
   curl -X POST http://localhost:9001/fail
   ```
   Watch the visualizer count 3 failures and then switch to **OPEN**. Notice how the error message changes to "(Fast Fail)".

4. **Recover**:
   ```bash
   curl -X POST http://localhost:9001/recover
   ```
   Wait 5 seconds. You'll see the state move to **HALF-OPEN**, then back to **CLOSED**!
