# Module 20: Bloom Filters

## 🎯 The Scenario

You have 1 billion usernames. Someone tries to register "alice123".

- **Option A:** Query database (slow disk I/O)
- **Option B:** Keep all usernames in RAM (100GB+ memory)
- **Option C:** Bloom Filter (50MB memory, instant lookup)

*How does 50MB represent 1 billion items?*

---

## 💡 The Concept

### Probabilistic Data Structure
A Bloom Filter tells you:
- **"Definitely not in set"** → 100% accurate
- **"Probably in set"** → Might be a false positive

### How It Works
1. Bit array of size M (all zeros)
2. K hash functions
3. On insert: set K bit positions to 1
4. On lookup: if ALL K positions are 1, "probably yes"; if ANY is 0, "definitely no"

---

## 🚀 How to Run

```bash
python3 workshop_materials/20_bloom/visualize_bloom.py
```

**What you'll see:**
- Adding items fills the bit array
- False positives occur when bits happen to overlap

---

## 📚 The Real Use Case

- **Cassandra:** Bloom filters on SSTables prevent unnecessary disk reads
- **Chrome:** Safe Browsing uses Bloom filters to check malicious URLs locally

---

## 🏆 Challenge

Calculate: For 1% false positive rate with 1 million items, how many bits do you need? (Hint: m = -n*ln(p) / (ln(2))²)
