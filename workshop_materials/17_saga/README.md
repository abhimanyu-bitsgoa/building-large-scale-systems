# Module 17: Saga Pattern

## 🎯 The Scenario

User books a trip: Flight + Hotel + Car Rental.

1. Flight Service: "Flight booked! ✓"
2. Hotel Service: "No rooms available! ✗"

The flight is booked, but the hotel isn't. **The user has a useless flight.**

*How do you "rollback" across independent services?*

---

## 💡 The Concept

### The Problem
Unlike a database transaction, you can't `ROLLBACK` across microservices. Each service has its own database.

### Saga Pattern
A sequence of local transactions with **compensating actions**.

```
book_flight() → book_hotel() → book_car()
       ↓             ↓
   cancel_flight() ← if hotel fails, undo flight
```

### Saga Types
| Type | Description |
|------|-------------|
| **Choreography** | Each service triggers the next. Decentralized. |
| **Orchestration** | A central coordinator directs everything. |

---

## 🚀 How to Run

```bash
python3 workshop_materials/17_saga/saga_orchestrator.py
```

**What you'll see:**
1. **Success scenario:** Flight → Hotel → Success!
2. **Failure scenario:** Flight booked → Hotel fails → Flight cancelled (compensation)

---

## 📚 The Real Use Case

Uber uses Sagas for ride matching:
1. Match rider with driver
2. Deduct payment hold
3. Start ride

If Step 2 fails (card declined), Step 1 is compensated (unmatch driver).

---

## 🏆 Challenge

Implement a Saga for e-commerce order:
1. Reserve inventory
2. Process payment
3. Schedule shipping

What's the compensating action for each step?
