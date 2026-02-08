"""
Multi-Region Distributed KV Store Assessment

Tests student configurations for cost, latency, availability, and consistency.
Simulates multi-region deployment with realistic latency.

Usage:
    python assessment.py --config student_config.yaml
    python assessment.py --config student_config.yaml --ideal  # Run ideal baseline
"""

import json
import time
import requests
import argparse
import subprocess
import sys
import os
import random
import statistics
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
# Constants
# ========================

COORDINATOR_URL = "http://localhost:7000"
REGISTRY_URL = "http://localhost:9000"

# Latency matrix (ms) - one-way latency between regions
# Format: LATENCY[from_region][to_region]
LATENCY_MS = {
    "us": {"us": 3, "eu": 120, "asia": 200},
    "eu": {"us": 120, "eu": 3, "asia": 95},
    "asia": {"us": 200, "eu": 95, "asia": 3},
}

# Node pricing (dollars per node per region)
NODE_COST = {
    "asia": 10,
    "us": 12,
    "eu": 15,
}


# ========================
# Student Config Schema
# ========================

@dataclass
class StudentConfig:
    # Leader deployment
    leader_region: str = "us"
    
    # Followers per region
    followers: Dict[str, int] = field(default_factory=lambda: {"us": 0, "eu": 1, "asia": 1})
    
    # Quorum
    write_quorum: int = 2
    read_quorum: int = 2
    
    # Workload (set by instructor)
    rw_ratio: int = 80  # percentage reads
    total_requests: int = 100
    stale_reads_allowed: bool = False
    
    # Justification
    justification: str = ""
    
    @classmethod
    def from_file(cls, path: str) -> "StudentConfig":
        """Load config from JSON or YAML file."""
        with open(path, 'r') as f:
            if path.endswith('.yaml') or path.endswith('.yml'):
                if not YAML_AVAILABLE:
                    raise ImportError("PyYAML not installed. Use JSON or: pip install pyyaml")
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        config = cls()
        
        if "leader_region" in data:
            config.leader_region = data["leader_region"]
        if "followers" in data:
            config.followers = data["followers"]
        if "quorum" in data:
            config.write_quorum = data["quorum"].get("write_quorum", 2)
            config.read_quorum = data["quorum"].get("read_quorum", 2)
        if "justification" in data:
            config.justification = data["justification"]
        
        return config
    
    def get_all_regions(self) -> List[str]:
        """Get all regions with nodes (leader + followers)."""
        regions = set()
        regions.add(self.leader_region)
        for region, count in self.followers.items():
            if count > 0:
                regions.add(region)
        return list(regions)
    
    def get_total_followers(self) -> int:
        """Get total follower count."""
        return sum(self.followers.values())
    
    def calculate_cost(self) -> int:
        """Calculate total cost in dollars."""
        total = 0
        # Leader cost
        total += NODE_COST[self.leader_region]
        # Follower costs
        for region, count in self.followers.items():
            total += NODE_COST[region] * count
        return total


# ========================
# Latency Simulator
# ========================

def simulate_latency(from_region: str, to_region: str) -> float:
    """Simulate network latency between regions. Returns actual delay applied."""
    latency_ms = LATENCY_MS.get(from_region, {}).get(to_region, 100)
    # Add jitter (±10%)
    jitter = random.uniform(-0.1, 0.1) * latency_ms
    actual_latency = (latency_ms + jitter) / 1000  # Convert to seconds
    time.sleep(actual_latency)
    return latency_ms + jitter


# ========================
# Test Results
# ========================

@dataclass
class TestMetrics:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    latencies: List[float] = field(default_factory=list)
    stale_reads: int = 0
    downtime_ms: float = 0
    
    @property
    def p95_latency(self) -> float:
        if not self.latencies:
            return 0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]
    
    @property
    def avg_latency(self) -> float:
        return statistics.mean(self.latencies) if self.latencies else 0
    
    @property
    def availability(self) -> float:
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100


# ========================
# Cluster Manager
# ========================

class ClusterManager:
    """Manages the distributed KV store cluster."""
    
    def __init__(self, config: StudentConfig):
        self.config = config
        self.processes: List[subprocess.Popen] = []
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.node_regions: Dict[str, str] = {}  # node_id -> region
    
    def start(self) -> bool:
        """Start registry, coordinator with nodes."""
        print("🚀 Starting cluster...")
        
        follower_count = self.config.get_total_followers()
        if follower_count == 0:
            print("❌ No followers configured!")
            return False
        
        # Start registry with auto-spawn (always enabled)
        registry_cmd = [
            sys.executable,
            os.path.join(self.base_dir, "registry.py"),
            "--port", "9000",
            "--auto-spawn"
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
            "--followers", str(follower_count),
            "--write-quorum", str(self.config.write_quorum),
            "--read-quorum", str(self.config.read_quorum),
            "--registry", REGISTRY_URL
        ]
        self.processes.append(subprocess.Popen(
            coord_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        ))
        
        regions_str = f"Leader: {self.config.leader_region.upper()}, Followers: {self.config.followers}"
        print(f"   {regions_str}")
        print(f"   W={self.config.write_quorum}, R={self.config.read_quorum}")
        print(f"   Service Discovery: enabled")
        print(f"   Waiting for cluster to initialize...")
        time.sleep(5)
        
        # Map nodes to regions
        self._assign_regions_to_nodes()
        
        # Verify cluster is up
        try:
            resp = requests.get(f"{COORDINATOR_URL}/status", timeout=5)
            if resp.status_code == 200:
                print("✅ Cluster started successfully")
                return True
        except:
            pass
        
        print("❌ Cluster failed to start")
        return False
    
    def _assign_regions_to_nodes(self):
        """Assign regions to spawned nodes for latency simulation."""
        # Build region list based on followers config
        regions = []
        for region, count in self.config.followers.items():
            regions.extend([region] * count)
        
        try:
            resp = requests.get(f"{COORDINATOR_URL}/status", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                followers = data.get("followers", [])
                for i, follower in enumerate(followers):
                    node_id = follower.get("id", f"follower-{i+1}")
                    region = regions[i] if i < len(regions) else "us"
                    self.node_regions[node_id] = region
        except:
            pass
    
    def get_nearest_region(self, client_region: str) -> str:
        """Get the nearest node region for a client."""
        all_regions = self.config.get_all_regions()
        if client_region in all_regions:
            return client_region
        # Find nearest by latency
        return min(all_regions, key=lambda r: LATENCY_MS[client_region][r])
    
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
    """Runs assessment tests with latency simulation."""
    
    def __init__(self, config: StudentConfig, cluster: ClusterManager):
        self.config = config
        self.cluster = cluster
        self.metrics = TestMetrics()
        self.version_cache: Dict[str, int] = {}  # Track written versions
    
    def run_all(self) -> TestMetrics:
        """Run all tests and collect metrics."""
        print("\n" + "=" * 60)
        print("               RUNNING ASSESSMENT TESTS")
        print("=" * 60 + "\n")
        
        # Calculate request distribution
        total = self.config.total_requests
        reads = int(total * self.config.rw_ratio / 100)
        writes = total - reads
        
        # Distribute across regions equally
        users_per_region = total // 3
        
        print(f"📊 Workload: {reads} reads, {writes} writes")
        print(f"👥 Users: {users_per_region} per region (US, EU, Asia)")
        print()
        
        # Run tests
        self._run_latency_test(users_per_region)
        
        # Check stale reads
        self._check_stale_reads()
        
        return self.metrics
    
    def _run_latency_test(self, users_per_region: int):
        """Run multi-region latency test."""
        print("🌍 Running Multi-Region Latency Test...")
        
        regions = ["us", "eu", "asia"]
        reads = int(self.config.rw_ratio / 100 * users_per_region)
        writes = users_per_region - reads
        
        for region in regions:
            print(f"   📍 {region.upper()} users: {reads} reads, {writes} writes")
            
            # Writes
            for i in range(writes):
                self._do_write(f"key_{region}_{i}", f"value_{region}_{i}", region)
            
            # Reads
            for i in range(reads):
                key = f"key_{region}_{i % max(1, writes)}"  # Read existing keys
                self._do_read(key, region)
        
        print(f"\n   ✅ Completed: {self.metrics.successful_requests}/{self.metrics.total_requests}")
        print(f"   📈 P95 Latency: {self.metrics.p95_latency:.1f}ms")
        print(f"   📊 Avg Latency: {self.metrics.avg_latency:.1f}ms")
    
    def _do_write(self, key: str, value: str, client_region: str):
        """Perform a write with latency simulation."""
        self.metrics.total_requests += 1
        
        # Writes always go to leader
        leader_region = self.config.leader_region
        start_time = time.time()
        
        # Outbound latency
        simulate_latency(client_region, leader_region)
        
        try:
            resp = requests.post(
                f"{COORDINATOR_URL}/write",
                json={"key": key, "value": value},
                timeout=30
            )
            
            # Return latency
            simulate_latency(leader_region, client_region)
            
            elapsed = (time.time() - start_time) * 1000  # ms
            
            if resp.status_code == 200:
                self.metrics.successful_requests += 1
                self.metrics.latencies.append(elapsed)
                # Track version for stale read detection
                data = resp.json()
                self.version_cache[key] = data.get("version", 1)
            else:
                self.metrics.failed_requests += 1
        except Exception as e:
            self.metrics.failed_requests += 1
    
    def _do_read(self, key: str, client_region: str):
        """Perform a read with latency simulation."""
        self.metrics.total_requests += 1
        
        # Reads go to nearest replica
        nearest_region = self.cluster.get_nearest_region(client_region)
        start_time = time.time()
        
        # Outbound latency
        simulate_latency(client_region, nearest_region)
        
        try:
            resp = requests.get(f"{COORDINATOR_URL}/read/{key}", timeout=10)
            
            # Return latency
            simulate_latency(nearest_region, client_region)
            
            elapsed = (time.time() - start_time) * 1000  # ms
            
            if resp.status_code == 200:
                self.metrics.successful_requests += 1
                self.metrics.latencies.append(elapsed)
                
                # Check for stale read
                data = resp.json()
                read_version = data.get("version", 0)
                expected_version = self.version_cache.get(key, 0)
                if read_version < expected_version:
                    self.metrics.stale_reads += 1
            elif resp.status_code == 404:
                # Key doesn't exist yet, still counts as successful
                self.metrics.successful_requests += 1
                self.metrics.latencies.append(elapsed)
            else:
                self.metrics.failed_requests += 1
        except Exception as e:
            self.metrics.failed_requests += 1
    
    def _check_stale_reads(self):
        """Report stale reads status."""
        print(f"\n🔄 Stale Read Check...")
        if self.metrics.stale_reads > 0:
            if self.config.stale_reads_allowed:
                print(f"   ⚠️ {self.metrics.stale_reads} stale reads (allowed in config)")
            else:
                print(f"   ❌ {self.metrics.stale_reads} stale reads (NOT allowed - FAIL)")
        else:
            print(f"   ✅ No stale reads detected")


# ========================
# Report Generator
# ========================

def print_report(config: StudentConfig, metrics: TestMetrics):
    """Print the final results report."""
    cost = config.calculate_cost()
    
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + "MULTI-REGION ASSESSMENT RESULTS".center(68) + "║")
    print("╠" + "═" * 68 + "╣")
    
    # Configuration
    print("║  " + "CONFIGURATION".ljust(66) + "║")
    print("║  " + f"├─ Leader: {config.leader_region.upper()}".ljust(66) + "║")
    followers_str = ", ".join(f"{r.upper()}={c}" for r, c in config.followers.items() if c > 0)
    print("║  " + f"├─ Followers: {followers_str}".ljust(66) + "║")
    print("║  " + f"├─ Quorum: W={config.write_quorum}, R={config.read_quorum}".ljust(66) + "║")
    print("║  " + f"└─ Total Cost: ${cost}".ljust(66) + "║")
    
    print("╠" + "═" * 68 + "╣")
    
    # Metrics
    print("║  " + "RESULTS".ljust(66) + "║")
    print("║  " + f"├─ Requests: {metrics.successful_requests}/{metrics.total_requests} successful".ljust(66) + "║")
    print("║  " + f"├─ Availability: {metrics.availability:.1f}%".ljust(66) + "║")
    print("║  " + f"├─ P95 Latency: {metrics.p95_latency:.1f}ms".ljust(66) + "║")
    print("║  " + f"├─ Avg Latency: {metrics.avg_latency:.1f}ms".ljust(66) + "║")
    stale_status = "✅ None" if metrics.stale_reads == 0 else f"❌ {metrics.stale_reads}"
    print("║  " + f"└─ Stale Reads: {stale_status}".ljust(66) + "║")
    
    print("╚" + "═" * 68 + "╝")


# ========================
# Instructor Config
# ========================

@dataclass
class InstructorConfig:
    # Constraints - same for all students
    total_requests: int = 100
    rw_ratio: int = 80  # % reads
    stale_reads_allowed: bool = False
    
    @classmethod
    def from_file(cls, path: str) -> "InstructorConfig":
        """Load instructor config from JSON."""
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            config = cls()
            # Load constraints
            constraints = data.get("constraints", {})
            config.total_requests = constraints.get("total_requests", 100)
            config.rw_ratio = constraints.get("rw_ratio", 80)
            config.stale_reads_allowed = constraints.get("stale_reads_allowed", False)
            return config
        except FileNotFoundError:
            return cls()  # Use defaults


# ========================
# Main
# ========================

def run_assessment(config: StudentConfig, instructor: InstructorConfig, label: str = "Student") -> Tuple[TestMetrics, int]:
    """Run assessment for a config. Returns (metrics, cost)."""
    cluster = None
    try:
        cluster = ClusterManager(config)
        if not cluster.start():
            return None, 0
        
        runner = TestRunner(config, cluster)
        metrics = runner.run_all()
        cost = config.calculate_cost()
        
        return metrics, cost
    finally:
        if cluster:
            cluster.stop()


def main():
    parser = argparse.ArgumentParser(description="Multi-Region Distributed KV Store Assessment")
    parser.add_argument("--config", type=str, required=True, help="Path to student config file")
    parser.add_argument("--instructor-config", type=str, default="instructor_config.json", 
                        help="Path to instructor config (constraints)")
    
    args = parser.parse_args()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load instructor config
    instructor_path = os.path.join(base_dir, args.instructor_config)
    instructor = InstructorConfig.from_file(instructor_path)
    print(f"\n📋 Instructor Config:")
    print(f"   Constraints: {instructor.total_requests} requests, {instructor.rw_ratio}% reads, stale_reads_allowed={instructor.stale_reads_allowed}")
    
    # Load student config
    print("\n📋 Loading student configuration...")
    try:
        student_config = StudentConfig.from_file(args.config)
        # Apply instructor constraints
        student_config.total_requests = instructor.total_requests
        student_config.rw_ratio = instructor.rw_ratio
        student_config.stale_reads_allowed = instructor.stale_reads_allowed
        print(f"   Leader: {student_config.leader_region.upper()}")
        print(f"   Followers: {student_config.followers}")
        print(f"   Quorum: W={student_config.write_quorum}, R={student_config.read_quorum}")
        print(f"   Cost: ${student_config.calculate_cost()}")
    except Exception as e:
        print(f"❌ Failed to load student config: {e}")
        sys.exit(1)
    
    # Run assessment
    print("\n" + "=" * 60)
    print("               RUNNING ASSESSMENT")
    print("=" * 60)
    
    student_metrics, student_cost = run_assessment(student_config, instructor, "Student")
    if student_metrics is None:
        print("❌ Assessment failed")
        sys.exit(1)
    
    # Print final report (raw metrics)
    print_report(student_config, student_metrics)


if __name__ == "__main__":
    main()
