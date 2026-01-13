import asyncio
import random

class Participant:
    def __init__(self, name, balance=100):
        self.name = name
        self.balance = balance
        self.reserved = 0
        self.is_prepared = False

    async def prepare(self, amount, should_fail=False):
        """Phase 1: Voting."""
        print(f"  [{self.name}] Received PREPARE for ${amount}")
        await asyncio.sleep(1)
        
        if should_fail:
            print(f"  [{self.name}] ❌ VOTE: ABORT (Insufficient Funds or Disk Error)")
            return False
            
        if self.balance >= amount:
            self.reserved = amount
            self.is_prepared = True
            print(f"  [{self.name}] ✅ VOTE: READY")
            return True
        else:
            print(f"  [{self.name}] ❌ VOTE: ABORT (Insufficient Funds)")
            return False

    async def commit(self):
        """Phase 2: Execution."""
        if not self.is_prepared:
            return
        
        self.balance -= self.reserved
        self.reserved = 0
        self.is_prepared = False
        print(f"  [{self.name}] 🎉 COMMIT: Final Balance ${self.balance}")

    async def rollback(self):
        """Phase 2: Execution (On Failure)."""
        print(f"  [{self.name}] 🔄 ROLLBACK: Releasing reservation of ${self.reserved}")
        self.reserved = 0
        self.is_prepared = False

async def orchestrate_transaction(participants, amount, fail_at_node=None):
    print(f"\n🚀 COORDINATOR: Starting 2PC Transaction for ${amount}")
    print("-" * 45)
    
    # --- PHASE 1: PREPARE ---
    print("PHASE 1: Preparing Participants...")
    prepare_tasks = []
    for i, p in enumerate(participants):
        should_fail = (fail_at_node == i)
        prepare_tasks.append(p.prepare(amount, should_fail))
    
    results = await asyncio.gather(*prepare_tasks)
    
    # --- PHASE 2: DECISION ---
    if all(results):
        print("\n🏆 DECISION: GLOBAL COMMIT")
        commit_tasks = [p.commit() for p in participants]
        await asyncio.gather(*commit_tasks)
        return True
    else:
        print("\n🚨 DECISION: GLOBAL ABORT (One or more nodes failed)")
        rollback_tasks = [p.rollback() for p in participants]
        await asyncio.gather(*rollback_tasks)
        return False

async def main():
    bank_a = Participant("Bank_Alpha", balance=500)
    bank_b = Participant("Bank_Beta", balance=500)
    
    participants = [bank_a, bank_b]
    
    # Case 1: Success
    await orchestrate_transaction(participants, 200)
    
    await asyncio.sleep(2)
    print("\n" + "="*45)
    
    # Case 2: Failure (Node Beta fails during prepare)
    await orchestrate_transaction(participants, 400, fail_at_node=1)

if __name__ == "__main__":
    asyncio.run(main())
