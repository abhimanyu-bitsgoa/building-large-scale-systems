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

# Node pricing (credits per test run)
NODE_COST = {
    "asia": 10,
    "us": 12,
    "eu": 15,
}

# Service discovery cost (substantial to force deliberation)
SERVICE_DISCOVERY_COST = {
    "asia": 15,
    "us": 18,
    "eu": 22,
}

# Default scoring weights (tunable by instructor)
DEFAULT_WEIGHTS = {
    "cost": 33,
    "latency": 33,
    "availability": 34,
}


# ========================
# Student Config Schema
# ========================

@dataclass
class StudentConfig:
    # Regions
    regions: Dict[str, bool] = field(default_factory=lambda: {"us": True, "eu": True, "asia": True})
    
    # Quorum
    write_quorum: int = 2
    read_quorum: int = 1
    
    # Features
    service_discovery: bool = True
    stale_reads_allowed: bool = False
    
    # Workload
    rw_ratio: int = 80  # percentage reads
    total_requests: int = 99  # divisible by 3 for equal distribution
    
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
        
        if "regions" in data:
            config.regions = data["regions"]
        if "quorum" in data:
            config.write_quorum = data["quorum"].get("write_quorum", 2)
            config.read_quorum = data["quorum"].get("read_quorum", 1)
        if "service_discovery" in data:
            config.service_discovery = data["service_discovery"]
        if "stale_reads_allowed" in data:
            config.stale_reads_allowed = data["stale_reads_allowed"]
        if "rw_ratio" in data:
            config.rw_ratio = data["rw_ratio"]
        if "total_requests" in data:
            config.total_requests = data["total_requests"]
        if "justification" in data:
            config.justification = data["justification"]
        
        return config
    
    def get_enabled_regions(self) -> List[str]:
        return [r for r, enabled in self.regions.items() if enabled]
    
    def calculate_cost(self) -> int:
        """Calculate total cost in credits."""
        total = 0
        for region, enabled in self.regions.items():
            if enabled:
                total += NODE_COST[region]
                if self.service_discovery:
                    total += SERVICE_DISCOVERY_COST[region]
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
        
        enabled_regions = self.config.get_enabled_regions()
        if not enabled_regions:
            print("❌ No regions enabled!")
            return False
        
        follower_count = len(enabled_regions)
        
        # Start registry with auto-spawn based on config
        registry_cmd = [
            sys.executable,
            os.path.join(self.base_dir, "registry.py"),
            "--port", "9000"
        ]
        if self.config.service_discovery:
            registry_cmd.append("--auto-spawn")
        
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
        
        print(f"   Regions: {', '.join(enabled_regions)}")
        print(f"   W={self.config.write_quorum}, R={self.config.read_quorum}")
        print(f"   Service Discovery: {'enabled' if self.config.service_discovery else 'disabled'}")
        print(f"   Waiting for cluster to initialize...")
        time.sleep(5)
        
        # Map nodes to regions
        self._assign_regions_to_nodes(enabled_regions)
        
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
    
    def _assign_regions_to_nodes(self, regions: List[str]):
        """Assign regions to spawned nodes for latency simulation."""
        try:
            resp = requests.get(f"{COORDINATOR_URL}/status", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                followers = data.get("followers", [])
                for i, follower in enumerate(followers):
                    node_id = follower.get("id", f"follower-{i+1}")
                    region = regions[i % len(regions)]
                    self.node_regions[node_id] = region
        except:
            pass
    
    def get_nearest_region(self, client_region: str) -> str:
        """Get the nearest node region for a client."""
        enabled_regions = self.config.get_enabled_regions()
        if client_region in enabled_regions:
            return client_region
        # Find nearest by latency
        return min(enabled_regions, key=lambda r: LATENCY_MS[client_region][r])
    
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
        
        # Simulate latency to leader (writes always go to leader)
        # For simplicity, assume leader is in the first enabled region
        leader_region = self.config.get_enabled_regions()[0]
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
# Scorer
# ========================

class Scorer:
    """Calculate scores based on metrics."""
    
    def __init__(
        self, 
        config: StudentConfig, 
        metrics: TestMetrics,
        ideal_cost: int = None,
        ideal_p95: float = None,
        ideal_availability: float = None,
        weights: Dict[str, int] = None
    ):
        self.config = config
        self.metrics = metrics
        self.ideal_cost = ideal_cost or 100
        self.ideal_p95 = ideal_p95 or 200
        self.ideal_availability = ideal_availability or 100
        self.weights = weights or DEFAULT_WEIGHTS
    
    def calculate_score(self) -> Dict[str, float]:
        """Calculate component and total scores."""
        student_cost = self.config.calculate_cost()
        
        # Cost score (lower is better)
        cost_ratio = self.ideal_cost / max(student_cost, 1)
        cost_score = min(100, cost_ratio * 100)
        
        # Latency score (lower is better)
        latency_ratio = self.ideal_p95 / max(self.metrics.p95_latency, 1)
        latency_score = min(100, latency_ratio * 100)
        
        # Availability score
        avail_ratio = self.metrics.availability / self.ideal_availability
        availability_score = min(100, avail_ratio * 100)
        
        # Stale read penalty
        stale_penalty = 0
        if not self.config.stale_reads_allowed and self.metrics.stale_reads > 0:
            stale_penalty = self.metrics.stale_reads * 20
        
        # Weighted total
        total = (
            (self.weights["cost"] / 100) * cost_score +
            (self.weights["latency"] / 100) * latency_score +
            (self.weights["availability"] / 100) * availability_score
            - stale_penalty
        )
        
        return {
            "cost_score": cost_score,
            "latency_score": latency_score,
            "availability_score": availability_score,
            "stale_penalty": stale_penalty,
            "total": max(0, total),
        }


# ========================
# Report Generator
# ========================

def print_report(config: StudentConfig, metrics: TestMetrics, scores: Dict[str, float]):
    """Print the final grading report."""
    cost = config.calculate_cost()
    
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + "MULTI-REGION ASSESSMENT RESULTS".center(68) + "║")
    print("╠" + "═" * 68 + "╣")
    
    # Configuration
    regions = ", ".join(r.upper() for r in config.get_enabled_regions())
    print("║  " + f"Regions: {regions}".ljust(66) + "║")
    print("║  " + f"Quorum: W={config.write_quorum}, R={config.read_quorum}".ljust(66) + "║")
    print("║  " + f"Service Discovery: {'Yes' if config.service_discovery else 'No'}".ljust(66) + "║")
    print("║  " + f"Total Cost: {cost} credits".ljust(66) + "║")
    
    print("╠" + "═" * 68 + "╣")
    
    # Metrics
    print("║  " + "METRICS".ljust(66) + "║")
    print("║  " + f"├─ Requests: {metrics.successful_requests}/{metrics.total_requests} successful".ljust(66) + "║")
    print("║  " + f"├─ P95 Latency: {metrics.p95_latency:.1f}ms".ljust(66) + "║")
    print("║  " + f"├─ Avg Latency: {metrics.avg_latency:.1f}ms".ljust(66) + "║")
    print("║  " + f"├─ Availability: {metrics.availability:.1f}%".ljust(66) + "║")
    print("║  " + f"└─ Stale Reads: {metrics.stale_reads}".ljust(66) + "║")
    
    print("╠" + "═" * 68 + "╣")
    
    # Scores
    print("║  " + "SCORES".ljust(66) + "║")
    print("║  " + f"├─ Cost Score: {scores['cost_score']:.1f}/100".ljust(66) + "║")
    print("║  " + f"├─ Latency Score: {scores['latency_score']:.1f}/100".ljust(66) + "║")
    print("║  " + f"├─ Availability Score: {scores['availability_score']:.1f}/100".ljust(66) + "║")
    if scores["stale_penalty"] > 0:
        print("║  " + f"├─ Stale Read Penalty: -{scores['stale_penalty']:.0f}".ljust(66) + "║")
    print("║  " + f"└─ TOTAL SCORE: {scores['total']:.1f}/100".ljust(66) + "║")
    
    print("╚" + "═" * 68 + "╝")


# ========================
# Main
# ========================

def main():
    parser = argparse.ArgumentParser(description="Multi-Region Distributed KV Store Assessment")
    parser.add_argument("--config", type=str, required=True, help="Path to student config file")
    parser.add_argument("--ideal", action="store_true", help="Run ideal baseline config")
    parser.add_argument("--cost-weight", type=int, default=33, help="Cost weight (0-100)")
    parser.add_argument("--latency-weight", type=int, default=33, help="Latency weight (0-100)")
    parser.add_argument("--availability-weight", type=int, default=34, help="Availability weight (0-100)")
    
    args = parser.parse_args()
    
    # Load config
    print("\n📋 Loading configuration...")
    try:
        config = StudentConfig.from_file(args.config)
        print(f"   Regions: {config.get_enabled_regions()}")
        print(f"   Quorum: W={config.write_quorum}, R={config.read_quorum}")
        print(f"   R/W Ratio: {config.rw_ratio}% reads")
        print(f"   Cost: {config.calculate_cost()} credits")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        sys.exit(1)
    
    cluster = None
    
    try:
        # Start cluster
        cluster = ClusterManager(config)
        if not cluster.start():
            sys.exit(1)
        
        # Run tests
        runner = TestRunner(config, cluster)
        metrics = runner.run_all()
        
        # Calculate scores
        weights = {
            "cost": args.cost_weight,
            "latency": args.latency_weight,
            "availability": args.availability_weight,
        }
        scorer = Scorer(config, metrics, weights=weights)
        scores = scorer.calculate_score()
        
        # Print report
        print_report(config, metrics, scores)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Assessment interrupted")
    finally:
        if cluster:
            cluster.stop()


if __name__ == "__main__":
    main()
