# Module 3 & 4: Sharding & Consistent Hashing

## Goal
Learn how to partition data across nodes efficiently.

## Key Concepts
- **Sharding**: Splitting data across multiple nodes based on a key
- **Modulo Sharding**: Naive approach (`key % N`)
- **Consistent Hashing**: Minimizes data movement when adding/removing nodes
- **Virtual Nodes**: Improves distribution in Consistent Hashing

## Files
- `sharding_lib.py`: Strategy implementations (Modulo & Consistent)
- `router.py`: The routing logic (students code here)
- `visualize_rebalancing.py`: Shows key movement comparison

## Exercise

### 1. Run the Visualization
```bash
python3 workshop_materials/03_sharding/visualize_rebalancing.py
```

**Expected Output:**
- **Modulo**: ~75% keys moved when adding Node D
- **Consistent Hashing**: ~25% keys moved

### 2. Try the Router
```bash
python3 workshop_materials/03_sharding/router.py
```

### 3. Swap Strategies
Edit `router.py` line 7-8:
```python
# Comment out Modulo
# self.strategy = ModuloStrategy()

# Uncomment Consistent Hashing
self.strategy = ConsistentHashingStrategy(self.nodes)
```

Run `router.py` again and add a 4th node. Notice the difference!

## Challenge
Implement a **Rendezvous Hashing** (Highest Random Weight) strategy and compare it to Consistent Hashing.
