# Module 22: 2-Phase Commit (2PC)

## 🎯 The Scenario

Transfer $100 from Bank A to Bank B.

1. Bank A: "Deducted $100" ✓
2. Bank B: "System error, can't credit" ✗

**Money disappeared.** Bank A debited but Bank B never credited.

*How do you ensure all-or-nothing across separate databases?*

---

## 💡 The Concept

### The Problem
No shared transaction across independent databases.

### 2-Phase Commit

**Phase 1: Prepare (Voting)**
```
Coordinator → Bank A: "Can you deduct $100?"
Bank A → Coordinator: "READY (locked funds)"

Coordinator → Bank B: "Can you credit $100?"
Bank B → Coordinator: "READY (prepared slot)"
```

**Phase 2: Commit/Abort**
```
If ALL voted READY:
  Coordinator → All: "COMMIT"
  
If ANY voted ABORT:
  Coordinator → All: "ROLLBACK"
```

---

## 🚀 How to Run

```bash
python3 workshop_materials/22_2pc/two_phase_commit.py
```

**What you'll see:**
- **Success:** Both nodes prepare, both commit
- **Failure:** One node aborts, both rollback

---

## 📚 2PC vs Sagas

| Feature | 2PC | Saga |
|---------|-----|------|
| Consistency | Strong | Eventual |
| Performance | Blocking | Non-blocking |
| Failure mode | Coordinator down = stuck | Compensate |
| Use case | Financial transactions | Long-running workflows |

---

## 🏆 Challenge

What happens if the Coordinator crashes after sending PREPARE but before sending COMMIT? Research **3-Phase Commit** for the solution.
