# Module 16: Clock Skew (The Time Traveler)

In a distributed system, you can almost **never** trust `time.time()`. 

Crystals in motherboards vibrate at slightly different frequencies. Some clocks run fast, some run slow. This is called **Clock Skew**. If your system relies on "Last Write Wins" based on timestamps, clock skew can cause data loss.

### The Problem
1. **Node A** (Clock perfectly on time) writes `User.name = "Alice"` at 10:00:00AM.
2. **Node B** (Clock is 5 minutes behind) receives a write `User.name = "Bob"` at 10:01:00AM. But Node B thinks the time is 09:56:00AM.
3. If Node B checks its database and sees a version from 10:00:00AM, it might **discard** the update "Bob" because 09:56 is *earlier* than 10:00, even though "Bob" happened later in the real world!

### How to Run

1. **Start Node A** (Correct Clock):
   ```bash
   python3 workshop_materials/16_clocks/skewed_node.py --port 16001 --offset 0
   ```

2. **Start Node B** (5 Minutes Behind):
   ```bash
   python3 workshop_materials/16_clocks/skewed_node.py --port 16002 --offset -300
   ```

3. **Scenario: The "Time Traveler" Write**:
   First, write to Node A:
   ```bash
   curl -X POST "http://localhost:16001/write/user_1?value=Alice"
   ```
   Now, try to write a "newer" value to Node B:
   ```bash
   curl -X POST "http://localhost:16002/write/user_1?value=Bob"
   ```

### What to Observe
- Even though you sent "Bob" *after* "Alice", Node B will **REJECT** it. 
- It thinks the write is from the past because its clock is skewed.
- This is why systems like Google Spanner use "TrueTime" (GPS + Atomic Clocks) to bound this error, or why many systems prefer **Logical Clocks** (like Vector Clocks) instead of wall-clock time.
