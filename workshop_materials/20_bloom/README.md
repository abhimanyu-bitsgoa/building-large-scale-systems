# Module 20: Bloom Filters (The Fast Forgetter)

How do you check if a username exists in a database with 1 billion users? 
- **Option A**: Search the database (Disk I/O = Slow).
- **Option B**: Keep all usernames in a Hash Set (RAM = Very Expensive).
- **Option C**: **Bloom Filter** (RAM = Tiny, Speed = Instant).

A Bloom Filter is a **probabilistic data structure**. It can tell you:
1. "Definitely No" (The item is 100% not in the set).
2. "Probably Yes" (The item might be in the set, or it might be a **False Positive**).

### How it Works
1. You have a bit-array of size $M$, initially all 0s.
2. When you add an item, you run it through $K$ hash functions. Each hash gives you an index. You set those bits to 1.
3. When you check for an item, you hash it again. If **any** of those bits are 0, the item is definitely not there. If they are all 1, it might be.

### How to Run

Run the visualizer:
```bash
python3 workshop_materials/20_bloom/visualize_bloom.py
```

### What to Observe
- As you add fruits, notice the bit array filling up.
- When we test for "pizza", the bits it hashes to might already be '1' because of other fruits (like apple or banana). 
- If this happens, the filter says "Probably Yes" even though we never added pizza! This is a **False Positive**.
- In the real world, we use Bloom Filters as a "Shield" in front of databases. If the filter says "No", we don't even bother hitting the disk.
