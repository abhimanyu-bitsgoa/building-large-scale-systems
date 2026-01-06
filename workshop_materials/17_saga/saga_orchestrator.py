import asyncio
import random

# --- The Services ---

async def book_flight():
    print("✈️  Step 1: Booking Flight...")
    await asyncio.sleep(1)
    # 90% success rate
    if random.random() < 0.1:
        print("❌ Flight Booking FAILED!")
        return False
    print("✅ Flight Booked.")
    return True

async def cancel_flight():
    print("🔄 [UNDO] Cancelling Flight...")
    await asyncio.sleep(1)
    print("✅ Flight Refunded.")

async def book_hotel(should_fail=False):
    print("🏨 Step 2: Booking Hotel...")
    await asyncio.sleep(1)
    if should_fail:
        print("❌ Hotel Booking FAILED!")
        return False
    print("✅ Hotel Booked.")
    return True

async def cancel_hotel():
    print("🔄 [UNDO] Cancelling Hotel...")
    await asyncio.sleep(1)
    print("✅ Hotel Refunded.")

# --- The Orchestrator (Saga) ---

async def trip_saga(fail_at_hotel=False):
    print(f"\n🚀 Starting Trip Saga (Fail at Hotel: {fail_at_hotel})")
    print("-" * 45)
    
    # Track which steps were successful to know what to undo
    history = []
    
    # -- STEP 1 --
    if await book_flight():
        history.append("FLIGHT")
    else:
        print("🚨 SAGA ABORTED: Flight failed at start.")
        return False
    
    # -- STEP 2 --
    if await book_hotel(should_fail=fail_at_hotel):
        history.append("HOTEL")
    else:
        print("🚨 SAGA FAILED at Hotel. Initiating Rollback...")
        # COMPENSATING ACTIONS (The Undo)
        for step in reversed(history):
            if step == "FLIGHT":
                await cancel_flight()
            if step == "HOTEL":
                await cancel_hotel()
        print("🏁 ROLLBACK COMPLETE. System is consistent.")
        return False

    print("🎉 SAGA COMPLETE: Trip booked successfully!")
    return True

if __name__ == "__main__":
    print("=== THE SAGA PATTERN DEMO ===")
    
    async def run_demos():
        # 1. Success case
        await trip_saga(fail_at_hotel=False)
        
        await asyncio.sleep(2)
        print("\n" + "="*45)
        
        # 2. Failure case with undo
        await trip_saga(fail_at_hotel=True)

    asyncio.run(run_demos())
