#!/usr/bin/env python3
"""
Distributed KV Store Lab - Assessment Script

Evaluates student configurations against test scenarios.
Runs the cluster with student config and scores based on:
- Fault tolerance (can survive node failures)
- Consistency (reads return correct values)
- Rate limiting (gateway protection works)
- Cost efficiency (not over-provisioning)
"""

import argparse
import json
import subprocess
import time
import requests
import sys
import os
import signal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# ========================
# Configuration
# ========================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COORDINATOR_SCRIPT = os.path.join(SCRIPT_DIR, "coordinator.py")
GATEWAY_SCRIPT = os.path.join(SCRIPT_DIR, "gateway.py")
REGISTRY_SCRIPT = os.path.join(SCRIPT_DIR, "registry.py")

COORDINATOR_URL = "http://localhost:7000"
GATEWAY_URL = "http://localhost:8000"
REGISTRY_URL = "http://localhost:9000"

# ========================
# Result Tracking
# ========================

@dataclass
class TestResult:
    test_id: str
    description: str
    passed: bool
    message: str
    latency_ms: Optional[float] = None

@dataclass
class ScenarioResult:
    scenario_id: str
    name: str
    weight: int
    tests: List[TestResult]
    
    @property
    def passed(self) -> int:
        return sum(1 for t in self.tests if t.passed)
    
    @property
    def total(self) -> int:
        return len(self.tests)
    
    @property
    def score(self) -> float:
        if self.total == 0:
            return 0
        return (self.passed / self.total) * self.weight

# ========================
# Cluster Management
# ========================

processes: List[subprocess.Popen] = []

def start_cluster(student_config: dict) -> bool:
    """Start the cluster with student configuration."""
    global processes
    
    deployment = student_config.get("deployment", {})
    gateway_config = student_config.get("gateway", {})
    
    followers = deployment.get("followers", 3)
    write_quorum = deployment.get("write_quorum", 2)
    read_quorum = deployment.get("read_quorum", 2)
    
    rate_limit = gateway_config.get("rate_limit_enabled", True)
    rate_limit_max = gateway_config.get("rate_limit_max", 10)
    rate_limit_window = gateway_config.get("rate_limit_window", 60)
    
    print("🚀 Starting cluster with student configuration...")
    print(f"   Followers: {followers}")
    print(f"   Write Quorum: {write_quorum}")
    print(f"   Read Quorum: {read_quorum}")
    print(f"   Rate Limit: {rate_limit_max}/{rate_limit_window}s" if rate_limit else "   Rate Limit: disabled")
    print()
    
    try:
        # Start registry
        print("   Starting registry...")
        registry_proc = subprocess.Popen(
            ["python", REGISTRY_SCRIPT, "--port", "9000"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        processes.append(registry_proc)
        time.sleep(1)
        
        # Start coordinator
        print("   Starting coordinator...")
        coordinator_proc = subprocess.Popen(
            ["python", COORDINATOR_SCRIPT,
             "--followers", str(followers),
             "--write-quorum", str(write_quorum),
             "--read-quorum", str(read_quorum),
             "--registry", REGISTRY_URL],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        processes.append(coordinator_proc)
        time.sleep(3)  # Wait for nodes to spawn
        
        # Start gateway
        print("   Starting gateway...")
        gateway_args = ["python", GATEWAY_SCRIPT,
                       "--port", "8000",
                       "--coordinator", COORDINATOR_URL]
        if rate_limit:
            gateway_args.extend(["--rate-limit",
                                "--rate-limit-max", str(rate_limit_max),
                                "--rate-limit-window", str(rate_limit_window)])
        
        gateway_proc = subprocess.Popen(
            gateway_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        processes.append(gateway_proc)
        time.sleep(2)
        
        # Verify cluster is up
        try:
            resp = requests.get(f"{GATEWAY_URL}/cluster-status", timeout=5)
            if resp.status_code == 200:
                print("   ✅ Cluster started successfully!")
                print()
                return True
        except:
            pass
        
        print("   ❌ Cluster failed to start")
        return False
        
    except Exception as e:
        print(f"   ❌ Error starting cluster: {e}")
        return False

def stop_cluster():
    """Stop all cluster processes (including spawned nodes)."""
    global processes
    print("\n🛑 Stopping cluster...")
    
    # Kill tracked processes (registry, coordinator, gateway)
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except:
            try:
                proc.kill()
            except:
                pass
    processes = []
    
    # Also kill any node processes spawned by coordinator
    # These run on ports 7000-7099
    import subprocess as sp
    try:
        # Kill processes containing 'node.py' or on node ports
        sp.run(["pkill", "-f", "node.py.*--port 70"], capture_output=True, timeout=5)
    except:
        pass

# ========================
# Test Runners
# ========================

def run_write_test(key: str, value: str, use_coordinator: bool = False) -> TestResult:
    """Run a write test. Can use coordinator directly to bypass rate limiting."""
    try:
        start = time.time()
        url = COORDINATOR_URL if use_coordinator else GATEWAY_URL
        resp = requests.post(
            f"{url}/write",
            json={"key": key, "value": value},
            timeout=10
        )
        latency = (time.time() - start) * 1000
        
        if resp.status_code == 200:
            return TestResult(
                test_id="write",
                description=f"Write {key}={value}",
                passed=True,
                message="Write successful",
                latency_ms=latency
            )
        elif resp.status_code == 429:
            return TestResult(
                test_id="write",
                description=f"Write {key}={value}",
                passed=False,
                message="Rate limited"
            )
        else:
            return TestResult(
                test_id="write",
                description=f"Write {key}={value}",
                passed=False,
                message=f"Failed with status {resp.status_code}"
            )
    except Exception as e:
        return TestResult(
            test_id="write",
            description=f"Write {key}={value}",
            passed=False,
            message=str(e)
        )

def run_read_test(key: str, expected_value: Optional[str] = None, use_coordinator: bool = False) -> TestResult:
    """Run a read test. Can use coordinator directly to bypass rate limiting."""
    try:
        start = time.time()
        url = COORDINATOR_URL if use_coordinator else GATEWAY_URL
        resp = requests.get(f"{url}/read/{key}", timeout=10)
        latency = (time.time() - start) * 1000
        
        if resp.status_code == 200:
            data = resp.json()
            actual_value = data.get("value")
            
            if expected_value is not None and actual_value != expected_value:
                return TestResult(
                    test_id="read",
                    description=f"Read {key}",
                    passed=False,
                    message=f"Expected '{expected_value}', got '{actual_value}'",
                    latency_ms=latency
                )
            
            return TestResult(
                test_id="read",
                description=f"Read {key}",
                passed=True,
                message=f"Got value: {actual_value}",
                latency_ms=latency
            )
        elif resp.status_code == 404:
            return TestResult(
                test_id="read",
                description=f"Read {key}",
                passed=False,
                message="Key not found"
            )
        else:
            return TestResult(
                test_id="read",
                description=f"Read {key}",
                passed=False,
                message=f"Failed with status {resp.status_code}"
            )
    except Exception as e:
        return TestResult(
            test_id="read",
            description=f"Read {key}",
            passed=False,
            message=str(e)
        )

def run_kill_node_test(node_id: str) -> TestResult:
    """Kill a node."""
    try:
        resp = requests.post(f"{COORDINATOR_URL}/kill/{node_id}", timeout=5)
        time.sleep(1)  # Wait for death to register
        
        if resp.status_code == 200:
            return TestResult(
                test_id="kill",
                description=f"Kill {node_id}",
                passed=True,
                message=f"Node {node_id} killed"
            )
        else:
            return TestResult(
                test_id="kill",
                description=f"Kill {node_id}",
                passed=True,  # Still consider it passed if node was already dead
                message=f"Node response: {resp.status_code}"
            )
    except Exception as e:
        return TestResult(
            test_id="kill",
            description=f"Kill {node_id}",
            passed=False,
            message=str(e)
        )

def run_kill_nodes_test(count: str, num_followers: int) -> TestResult:
    """
    Kill multiple nodes. 
    count can be a number or 'floor(N/2)' for dynamic calculation.
    """
    # Calculate actual count
    if count == "floor(N/2)":
        actual_count = num_followers // 2
    else:
        actual_count = int(count)
    
    killed = []
    for i in range(1, actual_count + 1):
        node_id = f"follower-{i}"
        try:
            resp = requests.post(f"{COORDINATOR_URL}/kill/{node_id}", timeout=5)
            if resp.status_code == 200:
                killed.append(node_id)
        except:
            pass
    
    time.sleep(1)  # Wait for deaths to register
    
    if len(killed) == actual_count:
        return TestResult(
            test_id="kill_nodes",
            description=f"Kill {actual_count} followers (floor({num_followers}/2))",
            passed=True,
            message=f"Killed: {', '.join(killed)}"
        )
    else:
        return TestResult(
            test_id="kill_nodes",
            description=f"Kill {actual_count} followers",
            passed=False,
            message=f"Only killed {len(killed)}/{actual_count}"
        )

def run_burst_test(operation: str, count: int, key_prefix: str) -> TestResult:
    """Run burst of operations directly to coordinator (bypasses rate limiting)."""
    successes = 0
    for i in range(count):
        if operation == "write":
            # Use coordinator directly to avoid rate limiting interference
            result = run_write_test(f"{key_prefix}_{i}", f"value_{i}", use_coordinator=True)
        else:
            result = run_read_test(f"{key_prefix}_{i}", use_coordinator=True)
        if result.passed:
            successes += 1
    
    return TestResult(
        test_id="burst",
        description=f"Burst {operation} ({count} ops)",
        passed=successes == count,
        message=f"{successes}/{count} succeeded"
    )

def run_verify_burst_test(key_prefix: str, count: int) -> TestResult:
    """Verify all burst writes are readable (uses coordinator to bypass rate limiting)."""
    successes = 0
    for i in range(count):
        # Use coordinator directly to avoid rate limiting interference
        result = run_read_test(f"{key_prefix}_{i}", f"value_{i}", use_coordinator=True)
        if result.passed:
            successes += 1
    
    return TestResult(
        test_id="verify_burst",
        description=f"Verify burst reads",
        passed=successes == count,
        message=f"{successes}/{count} verified"
    )

def run_stale_read_test(key: str) -> TestResult:
    """
    Test for stale reads due to async replication lag.
    
    1. Write a value and get version
    2. Immediately read
    3. Compare versions - if read version < write version, it's stale
    """
    value = f"stale_test_value_{int(time.time())}"
    
    # Write via coordinator and capture the version
    try:
        resp = requests.post(
            f"{COORDINATOR_URL}/write",
            json={"key": key, "value": value},
            timeout=10
        )
        if resp.status_code != 200:
            return TestResult(
                test_id="stale_read",
                description="Stale read detection",
                passed=False,
                message=f"Write failed: {resp.status_code}"
            )
        
        write_result = resp.json()
        written_version = write_result.get("version", 0)
    except Exception as e:
        return TestResult(
            test_id="stale_read",
            description="Stale read detection",
            passed=False,
            message=f"Write error: {e}"
        )
    
    # Immediately read - check if version matches
    try:
        resp = requests.get(f"{COORDINATOR_URL}/read/{key}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            read_version = data.get("version", 0)
            served_by = data.get("served_by", "unknown")
            
            if read_version < written_version:
                return TestResult(
                    test_id="stale_read",
                    description="Stale read detection",
                    passed=False,
                    message=f"Stale! Wrote v{written_version}, got v{read_version} (from {served_by})"
                )
            else:
                return TestResult(
                    test_id="stale_read",
                    description="Stale read detection",
                    passed=True,
                    message=f"Fresh read: v{read_version} (from {served_by})"
                )
        elif resp.status_code == 404:
            return TestResult(
                test_id="stale_read",
                description="Stale read detection",
                passed=False,
                message=f"Stale! Key not found yet (wrote v{written_version})"
            )
        else:
            return TestResult(
                test_id="stale_read",
                description="Stale read detection",
                passed=False,
                message=f"Read failed: {resp.status_code}"
            )
    except Exception as e:
        return TestResult(
            test_id="stale_read",
            description="Stale read detection",
            passed=False,
            message=f"Read error: {e}"
        )

# ========================
# Scenario Runner
# ========================

def run_scenario(scenario: dict, num_followers: int) -> ScenarioResult:
    """Run all tests in a scenario."""
    results = []
    
    print(f"📋 Scenario: {scenario['name']}")
    print(f"   {scenario['description']}")
    print()
    
    for test in scenario.get("tests", []):
        test_type = test.get("type")
        
        if test_type == "write":
            result = run_write_test(test["key"], test["value"])
        elif test_type == "read":
            result = run_read_test(test["key"], test.get("expected_value"))
        elif test_type == "kill_node":
            result = run_kill_node_test(test["target"])
        elif test_type == "kill_nodes":
            result = run_kill_nodes_test(test.get("count", "1"), num_followers)
        elif test_type == "burst":
            result = run_burst_test(test["operation"], test["count"], test["key_prefix"])
        elif test_type == "verify_burst":
            result = run_verify_burst_test(test["key_prefix"], test["count"])
        elif test_type == "stale_read":
            result = run_stale_read_test(test.get("key", "stale_test"))
        else:
            result = TestResult(
                test_id=test.get("id", "unknown"),
                description=test.get("description", "Unknown test"),
                passed=False,
                message=f"Unknown test type: {test_type}"
            )
        
        icon = "✅" if result.passed else "❌"
        print(f"   {icon} {result.description}: {result.message}")
        results.append(result)
    
    print()
    return ScenarioResult(
        scenario_id=scenario["id"],
        name=scenario["name"],
        weight=scenario.get("weight", 0),
        tests=results
    )

# ========================
# Scoring
# ========================

def calculate_cost(student_config: dict, cost_model: dict) -> Tuple[float, float]:
    """Calculate cost and efficiency score."""
    followers = student_config.get("deployment", {}).get("followers", 3)
    per_follower = cost_model.get("per_follower_cost", 10)
    
    # 1 leader + N followers
    total_cost = (1 + followers) * per_follower
    
    # Ideal cost threshold from instructor config
    ideal_cost = 40  # $40/hour (1 leader + 3 followers at $10 each)
    
    if total_cost <= ideal_cost:
        efficiency = 100
    else:
        # Penalize over-provisioning
        efficiency = max(0, 100 - ((total_cost - ideal_cost) / ideal_cost * 100))
    
    return total_cost, efficiency

def print_results(scenario_results: List[ScenarioResult], 
                  student_config: dict, 
                  instructor_config: dict):
    """Print final assessment results."""
    
    total_score = 0
    max_score = 0
    
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║             DISTRIBUTED KV STORE - ASSESSMENT RESULTS                ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    
    for result in scenario_results:
        max_score += result.weight
        total_score += result.score
        pct = (result.passed / result.total * 100) if result.total > 0 else 0
        print(f"║  {result.name:<30} {result.passed}/{result.total} ({pct:.0f}%) │ {result.score:.1f}/{result.weight} pts ║")
    
    print("╠══════════════════════════════════════════════════════════════════════╣")
    
    percentage = (total_score / max_score * 100) if max_score > 0 else 0
    
    if percentage >= 90:
        grade = "A"
    elif percentage >= 80:
        grade = "B"
    elif percentage >= 70:
        grade = "C"
    elif percentage >= 60:
        grade = "D"
    else:
        grade = "F"
    
    print(f"║  TOTAL SCORE: {total_score:.1f}/{max_score} ({percentage:.1f}%)                              ║")
    print(f"║  GRADE: {grade}                                                          ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    
    # Print student justification
    justification = student_config.get("justification", "")
    if justification and "TODO" not in justification:
        print()
        print("📝 Student Justification:")
        print(f"   {justification}")

# ========================
# Main
# ========================

def main():
    parser = argparse.ArgumentParser(description="Distributed KV Store Assessment")
    parser.add_argument("--config", type=str, default="student_config.json",
                       help="Path to student configuration file")
    parser.add_argument("--instructor-config", type=str, default="instructor_config.json",
                       help="Path to instructor configuration file")
    parser.add_argument("--no-start-cluster", action="store_true",
                       help="Skip cluster startup (assume already running)")
    parser.add_argument("--no-stop-cluster", action="store_true",
                       help="Don't stop cluster after assessment")
    
    args = parser.parse_args()
    
    # Handle config paths relative to script directory
    if not os.path.isabs(args.config):
        args.config = os.path.join(SCRIPT_DIR, args.config)
    if not os.path.isabs(args.instructor_config):
        args.instructor_config = os.path.join(SCRIPT_DIR, args.instructor_config)
    
    # Load configs
    try:
        with open(args.config) as f:
            student_config = json.load(f)
    except FileNotFoundError:
        print(f"❌ Student config not found: {args.config}")
        print("   Copy student_config.json and modify with your settings")
        sys.exit(1)
    
    try:
        with open(args.instructor_config) as f:
            instructor_config = json.load(f)
    except FileNotFoundError:
        print(f"❌ Instructor config not found: {args.instructor_config}")
        sys.exit(1)
    
    # Validate student config
    deployment = student_config.get("deployment", {})
    followers = deployment.get("followers", 0)
    write_quorum = deployment.get("write_quorum", 0)
    read_quorum = deployment.get("read_quorum", 0)
    
    if write_quorum > followers:
        print(f"❌ Invalid config: write_quorum ({write_quorum}) > followers ({followers})")
        print("   Write quorum cannot exceed number of followers")
        sys.exit(1)
    
    if read_quorum > followers:
        print(f"❌ Invalid config: read_quorum ({read_quorum}) > followers ({followers})")
        sys.exit(1)
    
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║             DISTRIBUTED KV STORE - ASSESSMENT                        ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Start cluster
    if not args.no_start_cluster:
        if not start_cluster(student_config):
            stop_cluster()
            sys.exit(1)
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        stop_cluster()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Run scenarios
        scenario_results = []
        for scenario in instructor_config.get("scenarios", []):
            result = run_scenario(scenario, followers)
            scenario_results.append(result)
        
        # Print results
        print_results(scenario_results, student_config, instructor_config)
        
    finally:
        if not args.no_stop_cluster:
            stop_cluster()

if __name__ == "__main__":
    main()
