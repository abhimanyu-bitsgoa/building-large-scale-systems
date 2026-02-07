"""
Distributed KV Store Lab - Assessment Script

Automated testing and grading for student configurations.
Tests quorum behavior, rate limiting, failure recovery, and catchup.

Usage:
    python assessment.py --config student_config.json
    
    # Or with manual cluster (if already running):
    python assessment.py --config student_config.json --no-start-cluster
"""

import json
import time
import requests
import argparse
import subprocess
import sys
import os
import signal
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Optional YAML support
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# ========================
# Configuration
# ========================

GATEWAY_URL = "http://localhost:8000"
COORDINATOR_URL = "http://localhost:7000"
REGISTRY_URL = "http://localhost:9000"

STARTUP_WAIT = 5  # seconds to wait for cluster to start


# ========================
# Student Config Schema
# ========================

@dataclass
class ClusterConfig:
    followers: int = 3
    write_quorum: int = 2
    read_quorum: int = 1


@dataclass
class GatewayConfig:
    rate_limit_enabled: bool = True
    rate_limit_max: int = 10
    rate_limit_window: int = 60


@dataclass
class StudentConfig:
    cluster: ClusterConfig = field(default_factory=ClusterConfig)
    gateway: GatewayConfig = field(default_factory=GatewayConfig)
    justification: str = ""
    
    @classmethod
    def from_file(cls, path: str) -> "StudentConfig":
        """Load config from JSON or YAML file."""
        with open(path, 'r') as f:
            if path.endswith('.yaml') or path.endswith('.yml'):
                if not YAML_AVAILABLE:
                    raise ImportError("PyYAML not installed. Use JSON format or: pip install pyyaml")
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        cluster = ClusterConfig(**data.get("cluster", {}))
        gateway = GatewayConfig(**data.get("gateway", {}))
        justification = data.get("justification", "")
        
        return cls(cluster=cluster, gateway=gateway, justification=justification)


# ========================
# Test Results
# ========================

@dataclass
class TestResult:
    name: str
    passed: bool
    message: str = ""
    details: Dict = field(default_factory=dict)


@dataclass
class TestCategory:
    name: str
    results: List[TestResult] = field(default_factory=list)
    
    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)
    
    @property
    def total_count(self) -> int:
        return len(self.results)


# ========================
# Cluster Manager
# ========================

class ClusterManager:
    """Manages starting and stopping the distributed KV store cluster."""
    
    def __init__(self, config: StudentConfig):
        self.config = config
        self.processes: List[subprocess.Popen] = []
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
    
    def start(self) -> bool:
        """Start registry, coordinator, and gateway."""
        print("🚀 Starting cluster...")
        
        # Start registry
        registry_cmd = [
            sys.executable,
            os.path.join(self.base_dir, "registry.py"),
            "--port", "9000"
        ]
        self.processes.append(subprocess.Popen(
            registry_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        ))
        time.sleep(1)
        
        # Start coordinator
        coord_cmd = [
            sys.executable,
            os.path.join(self.base_dir, "coordinator.py"),
            "--followers", str(self.config.cluster.followers),
            "--write-quorum", str(self.config.cluster.write_quorum),
            "--read-quorum", str(self.config.cluster.read_quorum),
            "--registry", REGISTRY_URL
        ]
        self.processes.append(subprocess.Popen(
            coord_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        ))
        time.sleep(2)
        
        # Start gateway
        gateway_cmd = [
            sys.executable,
            os.path.join(self.base_dir, "gateway.py"),
            "--port", "8000",
            "--coordinator", COORDINATOR_URL
        ]
        if self.config.gateway.rate_limit_enabled:
            gateway_cmd.extend([
                "--rate-limit",
                "--rate-limit-max", str(self.config.gateway.rate_limit_max),
                "--rate-limit-window", str(self.config.gateway.rate_limit_window)
            ])
        
        self.processes.append(subprocess.Popen(
            gateway_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        ))
        
        print(f"   Waiting {STARTUP_WAIT}s for cluster to initialize...")
        time.sleep(STARTUP_WAIT)
        
        # Verify cluster is up
        try:
            resp = requests.get(f"{GATEWAY_URL}/health", timeout=5)
            if resp.status_code == 200:
                print("✅ Cluster started successfully")
                return True
        except:
            pass
        
        print("❌ Cluster failed to start")
        return False
    
    def stop(self):
        """Stop all cluster processes."""
        print("\n🛑 Stopping cluster...")
        for p in self.processes:
            try:
                p.terminate()
                p.wait(timeout=5)
            except:
                p.kill()
        self.processes.clear()
        print("   Cluster stopped")


# ========================
# Test Runner
# ========================

class TestRunner:
    """Runs all test categories and collects results."""
    
    def __init__(self, config: StudentConfig):
        self.config = config
        self.categories: List[TestCategory] = []
    
    def run_all(self) -> List[TestCategory]:
        """Run all test categories."""
        print("\n" + "=" * 60)
        print("               RUNNING ASSESSMENT TESTS")
        print("=" * 60 + "\n")
        
        # Rate Limiting Tests - RUN FIRST on fresh window
        if self.config.gateway.rate_limit_enabled:
            self.categories.append(self._run_rate_limit_tests())
            # Wait for rate limit window to reset before other tests
            window = self.config.gateway.rate_limit_window
            print(f"\n⏳ Waiting {window}s for rate limit window to reset...")
            time.sleep(window + 1)
        
        # Quorum Write Tests - uses coordinator directly
        self.categories.append(self._run_quorum_write_tests())
        
        # Quorum Read Tests - uses coordinator directly
        self.categories.append(self._run_quorum_read_tests())
        
        # Failure Recovery Tests - uses coordinator directly
        self.categories.append(self._run_failure_tests())
        
        # Catchup Tests - uses coordinator directly
        self.categories.append(self._run_catchup_tests())
        
        return self.categories
    
    def _run_quorum_write_tests(self) -> TestCategory:
        """Test quorum write behavior using coordinator directly."""
        print("📝 Running Quorum Write Tests...")
        category = TestCategory(name="Quorum Write Tests")
        
        # Test 1: Write succeeds with quorum (via coordinator)
        try:
            resp = requests.post(
                f"{COORDINATOR_URL}/write",
                json={"key": "test_write_1", "value": "hello"},
                timeout=10
            )
            passed = resp.status_code == 200
            category.results.append(TestResult(
                name="Write succeeds with quorum",
                passed=passed,
                message=f"Status: {resp.status_code}",
                details=resp.json() if passed else {}
            ))
        except Exception as e:
            category.results.append(TestResult(
                name="Write succeeds with quorum",
                passed=False,
                message=f"Error: {e}"
            ))
        
        # Test 2: Verify sync acks match W
        try:
            resp = requests.post(
                f"{COORDINATOR_URL}/write",
                json={"key": "test_write_2", "value": "world"},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                sync_acks = data.get("sync_acks", 0)
                passed = sync_acks >= self.config.cluster.write_quorum
                category.results.append(TestResult(
                    name=f"Sync acks meet quorum (W={self.config.cluster.write_quorum})",
                    passed=passed,
                    message=f"Got {sync_acks} acks",
                    details=data
                ))
            else:
                category.results.append(TestResult(
                    name=f"Sync acks meet quorum (W={self.config.cluster.write_quorum})",
                    passed=False,
                    message=f"Write failed: {resp.status_code}"
                ))
        except Exception as e:
            category.results.append(TestResult(
                name=f"Sync acks meet quorum (W={self.config.cluster.write_quorum})",
                passed=False,
                message=f"Error: {e}"
            ))
        
        # Test 3: Write version increments correctly
        try:
            resp1 = requests.post(
                f"{COORDINATOR_URL}/write",
                json={"key": "version_test", "value": "v1"},
                timeout=10
            )
            resp2 = requests.post(
                f"{COORDINATOR_URL}/write",
                json={"key": "version_test", "value": "v2"},
                timeout=10
            )
            if resp1.status_code == 200 and resp2.status_code == 200:
                v1 = resp1.json().get("version", 0)
                v2 = resp2.json().get("version", 0)
                passed = v2 > v1
                category.results.append(TestResult(
                    name="Version increments on write",
                    passed=passed,
                    message=f"v1={v1}, v2={v2}",
                    details={"version_1": v1, "version_2": v2}
                ))
            else:
                category.results.append(TestResult(
                    name="Version increments on write",
                    passed=False,
                    message="Write failed"
                ))
        except Exception as e:
            category.results.append(TestResult(
                name="Version increments on write",
                passed=False,
                message=f"Error: {e}"
            ))
        
        self._print_category_results(category)
        return category
    
    def _run_quorum_read_tests(self) -> TestCategory:
        """Test quorum read behavior using coordinator directly."""
        print("\n📖 Running Quorum Read Tests...")
        category = TestCategory(name="Quorum Read Tests")
        
        # Ensure we have data to read (via coordinator)
        requests.post(f"{COORDINATOR_URL}/write", json={"key": "read_test", "value": "data"}, timeout=10)
        time.sleep(1)  # Allow replication
        
        # Test 1: Read returns data (via coordinator)
        try:
            resp = requests.get(f"{COORDINATOR_URL}/read/read_test", timeout=10)
            passed = resp.status_code == 200 and resp.json().get("value") == "data"
            category.results.append(TestResult(
                name="Read returns correct data",
                passed=passed,
                message=f"Status: {resp.status_code}",
                details=resp.json() if resp.status_code == 200 else {}
            ))
        except Exception as e:
            category.results.append(TestResult(
                name="Read returns correct data",
                passed=False,
                message=f"Error: {e}"
            ))
        
        # Test 2: Read from followers (check served_by)
        try:
            resp = requests.get(f"{COORDINATOR_URL}/read/read_test", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                served_by = data.get("served_by", "")
                passed = "follower" in served_by.lower() or served_by != "leader"
                category.results.append(TestResult(
                    name="Read routes to followers first",
                    passed=passed,
                    message=f"Served by: {served_by}",
                    details=data
                ))
            else:
                category.results.append(TestResult(
                    name="Read routes to followers first",
                    passed=False,
                    message=f"Read failed: {resp.status_code}"
                ))
        except Exception as e:
            category.results.append(TestResult(
                name="Read routes to followers first",
                passed=False,
                message=f"Error: {e}"
            ))
        
        # Test 3: Quorum responses
        try:
            resp = requests.get(f"{COORDINATOR_URL}/read/read_test", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                quorum_responses = data.get("quorum_responses", 0)
                passed = quorum_responses >= self.config.cluster.read_quorum
                category.results.append(TestResult(
                    name=f"Read quorum met (R={self.config.cluster.read_quorum})",
                    passed=passed,
                    message=f"Got {quorum_responses} responses",
                    details=data
                ))
            else:
                category.results.append(TestResult(
                    name=f"Read quorum met (R={self.config.cluster.read_quorum})",
                    passed=False,
                    message=f"Read failed: {resp.status_code}"
                ))
        except Exception as e:
            category.results.append(TestResult(
                name=f"Read quorum met (R={self.config.cluster.read_quorum})",
                passed=False,
                message=f"Error: {e}"
            ))
        
        # Test 4: Read non-existent key returns 404
        try:
            resp = requests.get(f"{COORDINATOR_URL}/read/nonexistent_key_xyz", timeout=10)
            passed = resp.status_code == 404
            category.results.append(TestResult(
                name="Read non-existent key returns 404",
                passed=passed,
                message=f"Status: {resp.status_code}",
                details={}
            ))
        except Exception as e:
            category.results.append(TestResult(
                name="Read non-existent key returns 404",
                passed=False,
                message=f"Error: {e}"
            ))
        
        self._print_category_results(category)
        return category
    
    def _run_rate_limit_tests(self) -> TestCategory:
        """Test rate limiting behavior."""
        print("\n🛡️ Running Rate Limit Tests...")
        category = TestCategory(name="Rate Limit Tests")
        
        max_req = self.config.gateway.rate_limit_max
        
        # Test 1: Basic limit enforcement
        allowed_count = 0
        rejected_at = None
        
        try:
            for i in range(max_req + 5):
                resp = requests.get(f"{GATEWAY_URL}/read/rate_test_{i}", timeout=5)
                if resp.status_code == 200 or resp.status_code == 404:
                    allowed_count += 1
                elif resp.status_code == 429:
                    rejected_at = i + 1
                    break
            
            passed = rejected_at is not None and abs(allowed_count - max_req) <= 1
            category.results.append(TestResult(
                name=f"Rate limit enforced at {max_req} requests",
                passed=passed,
                message=f"Allowed: {allowed_count}, Rejected at request #{rejected_at}" if rejected_at else f"Never rejected (allowed {allowed_count})",
                details={"allowed": allowed_count, "limit": max_req}
            ))
        except Exception as e:
            category.results.append(TestResult(
                name=f"Rate limit enforced at {max_req} requests",
                passed=False,
                message=f"Error: {e}"
            ))
        
        # Test 2: Rate limit headers present
        try:
            # Make a request that gets rate limited
            for _ in range(max_req + 2):
                resp = requests.get(f"{GATEWAY_URL}/read/header_test", timeout=5)
            
            has_headers = "X-RateLimit-Limit" in resp.headers or "Retry-After" in resp.headers
            category.results.append(TestResult(
                name="Rate limit headers present",
                passed=has_headers,
                message="Headers found" if has_headers else "Headers missing",
                details=dict(resp.headers)
            ))
        except Exception as e:
            category.results.append(TestResult(
                name="Rate limit headers present",
                passed=False,
                message=f"Error: {e}"
            ))
        
        self._print_category_results(category)
        return category
    
    def _run_failure_tests(self) -> TestCategory:
        """Test failure recovery behavior using coordinator directly."""
        print("\n💥 Running Failure Recovery Tests...")
        category = TestCategory(name="Failure Recovery Tests")
        
        c = self.config.cluster
        
        # Test 1: Write after killing one follower (if quorum allows)
        if c.followers > c.write_quorum:
            try:
                # Kill one follower
                requests.post(f"{COORDINATOR_URL}/kill/follower-1", timeout=5)
                time.sleep(2)  # Wait for health check
                
                # Try to write via coordinator (bypasses gateway rate limit)
                resp = requests.post(
                    f"{COORDINATOR_URL}/write",
                    json={"key": "failure_test_1", "value": "resilient"},
                    timeout=10
                )
                passed = resp.status_code == 200
                category.results.append(TestResult(
                    name="Write succeeds after 1 follower killed",
                    passed=passed,
                    message=f"Status: {resp.status_code}",
                    details=resp.json() if passed else {}
                ))
            except Exception as e:
                category.results.append(TestResult(
                    name="Write succeeds after 1 follower killed",
                    passed=False,
                    message=f"Error: {e}"
                ))
        
        # Test 2: Read still works after failure
        try:
            resp = requests.get(f"{COORDINATOR_URL}/read/failure_test_1", timeout=10)
            passed = resp.status_code == 200
            category.results.append(TestResult(
                name="Read works after follower killed",
                passed=passed,
                message=f"Status: {resp.status_code}",
                details=resp.json() if passed else {}
            ))
        except Exception as e:
            category.results.append(TestResult(
                name="Read works after follower killed",
                passed=False,
                message=f"Error: {e}"
            ))
        
        # Test 3: Quorum lost detection
        try:
            # Kill enough followers to break quorum
            alive_followers = c.followers - 1  # Already killed 1
            to_kill = alive_followers - c.write_quorum + 1
            
            for i in range(2, 2 + to_kill):
                requests.post(f"{COORDINATOR_URL}/kill/follower-{i}", timeout=5)
            time.sleep(2)
            
            # Try to write - should fail with 503
            resp = requests.post(
                f"{COORDINATOR_URL}/write",
                json={"key": "failure_test_2", "value": "should_fail"},
                timeout=10
            )
            passed = resp.status_code == 503
            category.results.append(TestResult(
                name="Quorum lost correctly detected",
                passed=passed,
                message=f"Status: {resp.status_code} (expected 503)",
                details={}
            ))
        except Exception as e:
            category.results.append(TestResult(
                name="Quorum lost correctly detected",
                passed=False,
                message=f"Error: {e}"
            ))
        
        # Respawn followers for remaining tests
        for i in range(1, c.followers + 1):
            try:
                requests.post(f"{COORDINATOR_URL}/spawn", timeout=5)
            except:
                pass
        time.sleep(3)
        
        self._print_category_results(category)
        return category
    
    def _run_catchup_tests(self) -> TestCategory:
        """Test catchup behavior using coordinator directly."""
        print("\n🔄 Running Catchup Tests...")
        category = TestCategory(name="Catchup Tests")
        
        # Test 1: Write data, spawn new follower, verify it has data
        try:
            # Write some data via coordinator
            unique_key = f"catchup_test_{int(time.time())}"
            requests.post(
                f"{COORDINATOR_URL}/write",
                json={"key": unique_key, "value": "catchup_value"},
                timeout=10
            )
            time.sleep(1)
            
            # Spawn a new follower
            spawn_resp = requests.post(f"{COORDINATOR_URL}/spawn", timeout=5)
            time.sleep(3)  # Wait for catchup
            
            # Read the data via coordinator
            read_resp = requests.get(f"{COORDINATOR_URL}/read/{unique_key}", timeout=10)
            
            passed = read_resp.status_code == 200 and read_resp.json().get("value") == "catchup_value"
            category.results.append(TestResult(
                name="New follower receives data via catchup",
                passed=passed,
                message=f"Read status: {read_resp.status_code}",
                details=read_resp.json() if read_resp.status_code == 200 else {}
            ))
        except Exception as e:
            category.results.append(TestResult(
                name="New follower receives data via catchup",
                passed=False,
                message=f"Error: {e}"
            ))
        
        # Test 2: Snapshot endpoint works
        try:
            # Get status to find leader URL
            status_resp = requests.get(f"{COORDINATOR_URL}/status", timeout=5)
            if status_resp.status_code == 200:
                leader_url = status_resp.json().get("leader", {}).get("url")
                if leader_url:
                    snapshot_resp = requests.get(f"{leader_url}/snapshot", timeout=5)
                    passed = snapshot_resp.status_code == 200 and "data" in snapshot_resp.json()
                    category.results.append(TestResult(
                        name="Snapshot endpoint returns full state",
                        passed=passed,
                        message=f"Status: {snapshot_resp.status_code}",
                        details={"keys_in_snapshot": len(snapshot_resp.json().get("data", {}))}
                    ))
                else:
                    category.results.append(TestResult(
                        name="Snapshot endpoint returns full state",
                        passed=False,
                        message="Could not find leader URL"
                    ))
            else:
                category.results.append(TestResult(
                    name="Snapshot endpoint returns full state",
                    passed=False,
                    message=f"Status check failed: {status_resp.status_code}"
                ))
        except Exception as e:
            category.results.append(TestResult(
                name="Snapshot endpoint returns full state",
                passed=False,
                message=f"Error: {e}"
            ))
        
        # Test 3: Cluster status endpoint works
        try:
            resp = requests.get(f"{COORDINATOR_URL}/status", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                has_leader = data.get("leader") is not None
                has_followers = len(data.get("followers", [])) > 0
                has_quorum_info = "quorum" in data
                passed = has_leader and has_followers and has_quorum_info
                category.results.append(TestResult(
                    name="Cluster status endpoint works",
                    passed=passed,
                    message=f"Leader: {has_leader}, Followers: {has_followers}",
                    details=data
                ))
            else:
                category.results.append(TestResult(
                    name="Cluster status endpoint works",
                    passed=False,
                    message=f"Status: {resp.status_code}"
                ))
        except Exception as e:
            category.results.append(TestResult(
                name="Cluster status endpoint works",
                passed=False,
                message=f"Error: {e}"
            ))
        
        self._print_category_results(category)
        return category
    
    def _print_category_results(self, category: TestCategory):
        """Print results for a category."""
        for result in category.results:
            icon = "✅" if result.passed else "❌"
            print(f"   {icon} {result.name}: {result.message}")


# ========================
# Grader
# ========================

class Grader:
    """Calculate scores and generate report."""
    
    def __init__(self, config: StudentConfig, categories: List[TestCategory]):
        self.config = config
        self.categories = categories
    
    def get_score(self) -> Tuple[int, int]:
        """Get (passed, total) counts."""
        passed = sum(c.passed_count for c in self.categories)
        total = sum(c.total_count for c in self.categories)
        return passed, total
    
    def get_grade(self) -> str:
        """Get letter grade."""
        passed, total = self.get_score()
        if total == 0:
            return "N/A"
        
        pct = passed / total
        if pct >= 0.9:
            return "A"
        elif pct >= 0.8:
            return "B"
        elif pct >= 0.7:
            return "C"
        elif pct >= 0.6:
            return "D"
        else:
            return "F"
    
    def generate_feedback(self) -> List[str]:
        """Generate feedback based on config and results."""
        feedback = []
        c = self.config.cluster
        
        # Check quorum configuration
        if c.followers >= c.write_quorum + 1:
            feedback.append(f"✓ Good fault tolerance: can lose {c.followers - c.write_quorum} follower(s)")
        else:
            feedback.append(f"⚠ Tight quorum: no room for follower failures")
        
        if c.read_quorum == 1:
            feedback.append("✓ R=1 provides fast reads (eventual consistency)")
        elif c.read_quorum > 1:
            feedback.append(f"✓ R={c.read_quorum} provides stronger read consistency")
        
        if self.config.gateway.rate_limit_enabled:
            feedback.append("✓ Rate limiting protects cluster from overload")
        else:
            feedback.append("⚠ Rate limiting disabled - cluster vulnerable to overload")
        
        return feedback
    
    def print_report(self):
        """Print the full grading report."""
        passed, total = self.get_score()
        grade = self.get_grade()
        c = self.config.cluster
        g = self.config.gateway
        
        print("\n")
        print("╔" + "═" * 68 + "╗")
        print("║" + "DISTRIBUTED KV STORE - ASSESSMENT RESULTS".center(68) + "║")
        print("╠" + "═" * 68 + "╣")
        
        config_line = f"Config: W={c.write_quorum}, R={c.read_quorum}, Followers={c.followers}"
        if g.rate_limit_enabled:
            config_line += f", Rate Limit={g.rate_limit_max}/{g.rate_limit_window}s"
        print("║  " + config_line.ljust(66) + "║")
        
        print("╠" + "═" * 68 + "╣")
        
        for category in self.categories:
            print("║" + " " * 68 + "║")
            print("║  " + category.name.upper().ljust(66) + "║")
            
            for result in category.results:
                icon = "✅" if result.passed else "❌"
                line = f"{icon} {result.name}"
                if len(line) > 64:
                    line = line[:61] + "..."
                print("║  ├─ " + line.ljust(62) + "║")
        
        print("║" + " " * 68 + "║")
        print("╠" + "═" * 68 + "╣")
        print("║  " + f"SCORE: {passed}/{total} tests passed".ljust(66) + "║")
        print("║  " + f"GRADE: {grade}".ljust(66) + "║")
        print("║" + " " * 68 + "║")
        print("║  " + "FEEDBACK:".ljust(66) + "║")
        
        for fb in self.generate_feedback():
            if len(fb) > 64:
                fb = fb[:61] + "..."
            print("║  " + f"• {fb}".ljust(66) + "║")
        
        print("╚" + "═" * 68 + "╝")


# ========================
# Main Entry Point
# ========================

def main():
    parser = argparse.ArgumentParser(description="Distributed KV Store - Assessment Script")
    parser.add_argument("--config", type=str, required=True, help="Path to student config YAML")
    parser.add_argument("--no-start-cluster", action="store_true", 
                        help="Don't start cluster (assumes it's already running)")
    
    args = parser.parse_args()
    
    # Load student config
    print("\n📋 Loading student configuration...")
    try:
        config = StudentConfig.from_file(args.config)
        print(f"   Cluster: {config.cluster.followers} followers, W={config.cluster.write_quorum}, R={config.cluster.read_quorum}")
        print(f"   Gateway: Rate limit {'enabled' if config.gateway.rate_limit_enabled else 'disabled'}")
        if config.gateway.rate_limit_enabled:
            print(f"            {config.gateway.rate_limit_max} requests per {config.gateway.rate_limit_window}s")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        sys.exit(1)
    
    cluster_manager = None
    
    try:
        # Start cluster if needed
        if not args.no_start_cluster:
            cluster_manager = ClusterManager(config)
            if not cluster_manager.start():
                print("❌ Failed to start cluster. Exiting.")
                sys.exit(1)
        else:
            print("\n⏭️ Skipping cluster startup (--no-start-cluster)")
        
        # Run tests
        runner = TestRunner(config)
        categories = runner.run_all()
        
        # Generate report
        grader = Grader(config, categories)
        grader.print_report()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Assessment interrupted")
    finally:
        if cluster_manager:
            cluster_manager.stop()


if __name__ == "__main__":
    main()
