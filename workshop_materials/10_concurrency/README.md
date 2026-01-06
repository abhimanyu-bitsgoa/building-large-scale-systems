# Module 10: Thundering Herd (Cache Stampede)

What happens when a very popular cache key (e.g., the homepage data) expires at the exact same moment that 10,000 users hit your site?

They all see "Cache Miss" and they all hit your Database at the same time. This is the **Thundering Herd** (or Cache Stampede). It can crush even the strongest databases.

### The Problem: The Stampede
Without protection, every concurrent request for the same missing key triggers a separate, expensive Database query.

### The Solution: Single Flight
Single Flight is a technique where the system detects that a request for `key_X` is already in progress. Instead of starting a second request, it makes all subsequent callers wait for the *first* request to finish, and then shares the result with everyone.

### How to Run

Run the simulation script:
```bash
python3 workshop_materials/10_concurrency/cache_stampede.py
```

### What to Observe
1. **Scenario 1 (STAMPEDE)**: 
   - You will see 5 clients all trigger a DB query simultaneously.
   - **Total DB Queries: 5**.
   - Your database is crying. 😭

2. **Scenario 2 (SINGLE_FLIGHT)**:
   - Client 0 starts the query.
   - Clients 1-4 detect the ongoing request and wait.
   - **Total DB Queries: 1**.
   - Your database is happy! 😊
