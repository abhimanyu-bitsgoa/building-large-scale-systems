import asyncio
import random
from collections import Counter

class Node:
    def __init__(self, id, is_malicious=False):
        self.id = id
        self.is_malicious = is_malicious
        self.true_state = "ATTACK"

    async def get_vote(self):
        await asyncio.sleep(random.random()) # Random network latency
        if self.is_malicious:
            # A malicious node might lie to cause confusion
            # For example, it returns "RETREAT" when it should say "ATTACK"
            return "RETREAT"
        return self.true_state

async def reach_consensus(nodes, threshold):
    print(f"🕵️  Orchestrator: Collecting votes from {len(nodes)} nodes...")
    
    votes = []
    tasks = [n.get_vote() for n in nodes]
    results = await asyncio.gather(*tasks)
    
    for i, vote in enumerate(results):
        print(f"   [Node {i}] voted: {vote} {'(😈 MALICIOUS)' if nodes[i].is_malicious else ''}")
        votes.append(vote)

    # Simple majority / threshold check
    count = Counter(votes)
    winner, winner_count = count.most_common(1)[0]
    
    print("-" * 45)
    print(f"🔍 ANALYSIS: Majority choice is '{winner}' with {winner_count} votes.")
    
    if winner_count >= threshold:
        print(f"✅ CONSENSUS REACHED: Cluster will {winner}!")
        return winner
    else:
        print("❌ FAILURE: Could not reach consensus. Too many traitors!")
        return None

async def main():
    print("=== BYZANTINE FAULT TOLERANCE DEMO ===")
    
    # scenario 1: 3 nodes, 1 malicious (Majority still wins)
    print("\nScenario 1: 3 Nodes (1 Traitor)")
    nodes_1 = [Node(0), Node(1), Node(2, is_malicious=True)]
    await reach_consensus(nodes_1, threshold=2)
    
    await asyncio.sleep(2)
    
    # scenario 2: 3 nodes, 2 malicious (Byzantine failure!)
    print("\nScenario 2: 3 Nodes (2 Traitors)")
    nodes_2 = [Node(0), Node(1, is_malicious=True), Node(2, is_malicious=True)]
    await reach_consensus(nodes_2, threshold=2)

if __name__ == "__main__":
    asyncio.run(main())
