import hashlib

class BloomFilter:
    def __init__(self, size=100, num_hashes=3):
        self.size = size
        self.bit_array = [0] * size
        self.num_hashes = num_hashes

    def _hashes(self, item):
        """Generate multiple indices for an item using different salts."""
        indices = []
        for i in range(self.num_hashes):
            # Using MD5 with a salt to simulate multiple hash functions
            h = hashlib.md5(f"{i}:{item}".encode()).hexdigest()
            # Convert hex to int and map to array size
            index = int(h, 16) % self.size
            indices.append(index)
        return indices

    def add(self, item):
        """Add an item to the filter by setting bits at hashed indices."""
        indices = self._hashes(item)
        for idx in indices:
            self.bit_array[idx] = 1

    def contains(self, item):
        """
        Check if an item is likely in the filter.
        Returns False -> DEFINITELY NO
        Returns True  -> PROBABLY YES (Potential False Positive)
        """
        indices = self._hashes(item)
        for idx in indices:
            if self.bit_array[idx] == 0:
                return False
        return True

    def get_fill_ratio(self):
        return sum(self.bit_array) / self.size

if __name__ == "__main__":
    # Quick CLI test
    bf = BloomFilter(size=20, num_hashes=2)
    print("Empty filter. Contains 'apple'?", bf.contains("apple"))
    
    bf.add("apple")
    print("Added 'apple'. Contains 'apple'?", bf.contains("apple"))
    print("Contains 'banana'?", bf.contains("banana"))
