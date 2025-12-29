import time
import random
import os
import signal
import psutil

def kill_random_node():
    # Find all processes running 'node.py'
    targets = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and "node.py" in " ".join(cmdline):
                targets.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    if not targets:
        print("No nodes found to kill! (Is your cluster running?)")
        return

    victim = random.choice(targets)
    try:
        print(f"🔫 Killing process {victim.pid} ({' '.join(victim.info['cmdline'])})")
        os.kill(victim.pid, signal.SIGKILL)
    except Exception as e:
        print(f"Failed to kill: {e}")

if __name__ == "__main__":
    print("😈 Chaos Script Started... (Press Ctrl+C to stop)")
    try:
        while True:
            time.sleep(10)
            kill_random_node()
    except KeyboardInterrupt:
        print("Chaos stopped.")
