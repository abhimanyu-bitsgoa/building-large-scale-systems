# Module 2: Load Balancing & Rate Limiting

## Goal
Protect your system from overload and distribute traffic evenly.

## Key Concepts
- **Load Balancing**: Distributing requests across multiple nodes
- **Rate Limiting**: Preventing abuse by limiting request frequency
- **Token Bucket**: A common rate limiting algorithm

## Files
- `visualize_load_balance.py`: Shows traffic distribution
- `visualize_rate_limit.py`: Demonstrates rate limiting in action
- `rate_limit_middleware.py`: Token Bucket implementation

## Exercise

### 1. Test Load Balancing Visualization
Start 3 nodes, then run:
```bash
python3 workshop_materials/02_networking/visualize_load_balance.py
```
You'll see a live bar chart showing request distribution.

### 2. Add Rate Limiting to Your Node
Edit your `node.py`:
```python
from workshop_materials.networking.rate_limit_middleware import RateLimitMiddleware

# Add before uvicorn.run()
app.add_middleware(RateLimitMiddleware, requests_per_second=5)
```

### 3. Test Rate Limiting
Start your rate-limited node on port 5001, then:
```bash
python3 workshop_materials/02_networking/visualize_rate_limit.py
```
Watch the "Bad Actor" get blocked with 429 errors!

## Challenge
Implement a **Fixed Window** rate limiting strategy and swap it in using the Strategy Pattern.
