import time

class LWWRegister:
    """Last-Writer-Wins Register."""
    def __init__(self, value=None, timestamp=0):
        self.value = value
        self.timestamp = timestamp

    def set(self, value):
        self.value = value
        self.timestamp = time.time()

    def merge(self, other):
        """Merge by taking the value with the higher timestamp."""
        if other.timestamp > self.timestamp:
            self.value = other.value
            self.timestamp = other.timestamp

class GSet:
    """Grow-only Set."""
    def __init__(self, initial_items=None):
        self.items = set(initial_items or [])

    def add(self, item):
        self.items.add(item)

    def merge(self, other):
        """Merge by taking the union of both sets."""
        self.items = self.items.union(other.items)

    def __str__(self):
        return f"{sorted(list(self.items))}"

def demo():
    print("=== CRDT DEMO: G-SET ===")
    node_a = GSet(["Apple"])
    node_b = GSet(["Banana"])
    
    print(f"Node A: {node_a}")
    print(f"Node B: {node_b}")
    
    print("Merging A into B...")
    node_b.merge(node_a)
    print(f"Result: {node_b}")
    
    print("\n=== CRDT DEMO: LWW-REGISTER ===")
    reg_a = LWWRegister("Hello", timestamp=100)
    reg_b = LWWRegister("World", timestamp=105) # "World" happened later
    
    print(f"Reg A: '{reg_a.value}' (t={reg_a.timestamp})")
    print(f"Reg B: '{reg_b.value}' (t={reg_b.timestamp})")
    
    print("Merging A and B...")
    reg_a.merge(reg_b)
    print(f"Result: '{reg_a.value}'")

if __name__ == "__main__":
    demo()
