from bloom_filter import BloomFilter
import os
import time

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def draw_filter(bf):
    rows = 4
    cols = bf.size // rows
    
    print("Bit Array Status:")
    for r in range(rows):
        line = ""
        for c in range(cols):
            idx = r * cols + c
            char = "█" if bf.bit_array[idx] == 1 else "."
            line += char + " "
        print(line)
    print("-" * 20)

def main():
    bf = BloomFilter(size=40, num_hashes=3)
    added_items = []
    
    test_items = ["apple", "banana", "cherry", "date", "elderberry", "fig", "grape"]
    
    for item in test_items:
        clear_screen()
        print("        🌸  BLOOM FILTER VISUALIZER  🌸")
        print("="*45)
        print(f"Action: Adding '{item}'")
        bf.add(item)
        added_items.append(item)
        
        draw_filter(bf)
        print(f"Fill Ratio: {bf.get_fill_ratio()*100:.1f}%")
        print("\nItems in Set:", ", ".join(added_items))
        
        time.sleep(1.5)

    # Now test for things NOT in the set
    non_items = ["pizza", "burger", "sushi", "taco"]
    for item in non_items:
        clear_screen()
        print("        🌸  BLOOM FILTER VISUALIZER  🌸")
        print("="*45)
        print(f"Action: Testing for '{item}' (Not in set)")
        
        is_in = bf.contains(item)
        draw_filter(bf)
        
        if is_in:
            print(f"🔍 Result for '{item}': PROBABLY YES (⚠️ FALSE POSITIVE!)")
        else:
            print(f"🔍 Result for '{item}': DEFINITELY NO")
            
        time.sleep(2)

    print("\nSimulation complete. Press Ctrl+C to exit.")
    while True: time.sleep(1)

if __name__ == "__main__":
    main()
