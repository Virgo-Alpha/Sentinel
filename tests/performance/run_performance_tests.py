#!/usr/bin/env python3
"""
Performance test runner for Sentinel cybersecurity triage system.
"""

import argparse
import subprocess
import sys
import os
import json
import time
from datetime import datetime
import psutil

def run_pytest_performance_tests(test_type="all", verbose=False):
    """Run pytest-based performance tests."""
    print(f"Running pytest performance tests: {test_type}")
    
    # Build pytest command
    cmd = ["python", "-m", "pytest", "tests/performance/"]
    
    # Add markers based on test type
    if test_type == "load":
        cmd.extend(["-m", "load"])
    elif test_type == "stress":
        cmd.extend(["-m", "stress"])
    elif test_type == "volume":
        cmd.extend(["-m", "volume"])
    elif test_type == "benchmark":
        cmd.extend(["-m", "benchmark"])
    elif test_type != "all":
        cmd.extend(["-k", test_type])
    
    # Add verbose output if requested
    if verbose:
        cmd.extend(["-v", "-s"])
    
    # Add performance-specific options
    cmd.extend([
        "--tb=short",
        "--maxfail=3",
        "--durations=10",
        f"--junitxml=tests/performance/results/pytest_results_{test_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
    ])
    
    # Ensure results directory exists
    os.makedirs("tests/performance/results", exist_ok=True)
    
    # Run tests
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    return result.returncode == 0

def run_locust_load_test(host="http://localhost:3000", users=50, spawn_rate=5, duration="5m", verbose=False):
    """Run Locust-based load tests."""
    print(f"Running Locust load test against {host}")
    print(f"Users: {users}, Spawn rate: {spawn_rate}, Duration: {duration}")
    
    # Build locust command
    cmd = [
        "locust",
        "-f", "tests/performance/locustfile.py",
        "--host", host,
        "--users", str(users),
        "--spawn-rate", str(spawn_rate),
        "--run-time", duration,
        "--headless",
        "--html", f"tests/performance/results/locust_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
        "--csv", f"tests/performance/results/locust_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    ]
    
    if verbose:
        cmd.append("--loglevel=DEBUG")
    
    # Ensure results directory exists
    os.makedirs("tests/performance/results", exist_ok=True)
    
    # Run Locust
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    return result.returncode == 0

def monitor_system_resources(duration_seconds=300, interval=5):
    """Monitor system resources during performance tests."""
    print(f"Monitoring system resources for {duration_seconds} seconds...")
    
    metrics = []
    start_time = time.time()
    
    while time.time() - start_time < duration_seconds:
        # Collect system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        metric = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_mb': memory.available / 1024 / 1024,
            'disk_percent': disk.percent,
            'network_bytes_sent': network.bytes_sent,
            'network_bytes_recv': network.bytes_recv
        }
        
        metrics.append(metric)
        print(f"CPU: {cpu_percent:5.1f}% | Memory: {memory.percent:5.1f}% | Disk: {disk.percent:5.1f}%")
        
        time.sleep(interval)
    
    # Save metrics to file
    os.makedirs("tests/performance/results", exist_ok=True)
    metrics_file = f"tests/performance/results/system_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"System metrics saved to: {metrics_file}")
    return metrics

def generate_performance_report(results_dir="tests/performance/results"):
    """Generate a comprehensive performance test report."""
    print("Generating performance test report...")
    
    if not os.path.exists(results_dir):
        print(f"Results directory not found: {results_dir}")
        return False
    
    # Find all result files
    result_files = []
    for file in os.listdir(results_dir):
        if file.endswith(('.xml', '.html', '.json', '.csv')):
            result_files.append(os.path.join(results_dir, file))
    
    if not result_files:
        print("No result files found")
        return False
    
    # Create summary report
    report = {
        'generated_at': datetime.now().isoformat(),
        'test_environment': {
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
            'python_version': sys.version,
            'platform': sys.platform
        },
        'result_files': result_files,
        'summary': {
            'total_files': len(result_files),
            'pytest_results': len([f for f in result_files if 'pytest' in f]),
            'locust_results': len([f for f in result_files if 'locust' in f]),
            'system_metrics': len([f for f in result_files if 'system_metrics' in f])
        }
    }
    
    # Save report
    report_file = os.path.join(results_dir, f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Performance report saved to: {report_file}")
    print(f"Found {len(result_files)} result files:")
    for file in result_files:
        print(f"  - {file}")
    
    return True

def main():
    """Main performance test runner."""
    parser = argparse.ArgumentParser(description="Run Sentinel performance tests")
    
    parser.add_argument("--test-type", 
                       choices=["all", "load", "stress", "volume", "benchmark", "locust"],
                       default="all",
                       help="Type of performance tests to run")
    
    parser.add_argument("--host",
                       default="http://localhost:3000",
                       help="Host URL for load testing (default: http://localhost:3000)")
    
    parser.add_argument("--users",
                       type=int,
                       default=50,
                       help="Number of concurrent users for load testing (default: 50)")
    
    parser.add_argument("--spawn-rate",
                       type=int,
                       default=5,
                       help="User spawn rate for load testing (default: 5)")
    
    parser.add_argument("--duration",
                       default="5m",
                       help="Test duration (default: 5m)")
    
    parser.add_argument("--monitor-resources",
                       action="store_true",
                       help="Monitor system resources during tests")
    
    parser.add_argument("--monitor-duration",
                       type=int,
                       default=300,
                       help="Resource monitoring duration in seconds (default: 300)")
    
    parser.add_argument("--generate-report",
                       action="store_true",
                       help="Generate performance test report")
    
    parser.add_argument("--verbose", "-v",
                       action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Sentinel Performance Test Runner")
    print("=" * 60)
    print(f"Test type: {args.test_type}")
    print(f"Target host: {args.host}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    success = True
    
    # Start resource monitoring if requested
    if args.monitor_resources:
        import threading
        monitor_thread = threading.Thread(
            target=monitor_system_resources,
            args=(args.monitor_duration, 5)
        )
        monitor_thread.daemon = True
        monitor_thread.start()
    
    try:
        # Run pytest-based tests
        if args.test_type in ["all", "load", "stress", "volume", "benchmark"]:
            print("\\nRunning pytest-based performance tests...")
            if not run_pytest_performance_tests(args.test_type, args.verbose):
                print("❌ Pytest performance tests failed")
                success = False
            else:
                print("✅ Pytest performance tests completed")
        
        # Run Locust load tests
        if args.test_type in ["all", "locust"]:
            print("\\nRunning Locust load tests...")
            if not run_locust_load_test(
                host=args.host,
                users=args.users,
                spawn_rate=args.spawn_rate,
                duration=args.duration,
                verbose=args.verbose
            ):
                print("❌ Locust load tests failed")
                success = False
            else:
                print("✅ Locust load tests completed")
        
        # Wait for resource monitoring to complete
        if args.monitor_resources:
            print("\\nWaiting for resource monitoring to complete...")
            monitor_thread.join()
            print("✅ Resource monitoring completed")
        
        # Generate report
        if args.generate_report:
            print("\\nGenerating performance test report...")
            if generate_performance_report():
                print("✅ Performance report generated")
            else:
                print("❌ Failed to generate performance report")
        
    except KeyboardInterrupt:
        print("\\n❌ Performance tests interrupted by user")
        success = False
    except Exception as e:
        print(f"\\n❌ Performance tests failed with error: {e}")
        success = False
    
    print("\\n" + "=" * 60)
    if success:
        print("✅ Performance testing completed successfully")
        sys.exit(0)
    else:
        print("❌ Performance testing completed with errors")
        sys.exit(1)

if __name__ == "__main__":
    main()