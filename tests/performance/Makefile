# Makefile for Sentinel Performance Tests

# Configuration
PYTHON := python3
PIP := pip3
VENV := venv
HOST := http://localhost:3000
RESULTS_DIR := results
TIMESTAMP := $(shell date +%Y%m%d_%H%M%S)

# Default target
.PHONY: help
help:
	@echo "Sentinel Performance Testing Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  setup           - Set up performance testing environment"
	@echo "  install         - Install performance testing dependencies"
	@echo "  test-all        - Run all performance tests"
	@echo "  test-load       - Run load tests only"
	@echo "  test-stress     - Run stress tests only"
	@echo "  test-volume     - Run volume tests only"
	@echo "  test-benchmark  - Run benchmark tests only"
	@echo "  test-locust     - Run Locust load tests"
	@echo "  test-quick      - Run quick performance validation"
	@echo "  monitor         - Monitor system resources"
	@echo "  report          - Generate performance report"
	@echo "  clean           - Clean up test results and artifacts"
	@echo "  clean-all       - Clean everything including virtual environment"
	@echo ""
	@echo "Configuration:"
	@echo "  HOST=$(HOST)"
	@echo "  RESULTS_DIR=$(RESULTS_DIR)"

# Environment setup
.PHONY: setup
setup: $(VENV)/bin/activate

$(VENV)/bin/activate:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip setuptools wheel

.PHONY: install
install: setup
	$(VENV)/bin/pip install -r requirements.txt
	$(VENV)/bin/pip install -r ../requirements.txt  # Main test requirements
	@echo "Performance testing environment ready!"

# Performance test targets
.PHONY: test-all
test-all: setup
	@echo "Running all performance tests..."
	@mkdir -p $(RESULTS_DIR)
	$(VENV)/bin/python run_performance_tests.py \
		--test-type all \
		--host $(HOST) \
		--monitor-resources \
		--generate-report \
		--verbose

.PHONY: test-load
test-load: setup
	@echo "Running load tests..."
	@mkdir -p $(RESULTS_DIR)
	$(VENV)/bin/python run_performance_tests.py \
		--test-type load \
		--host $(HOST) \
		--users 50 \
		--spawn-rate 5 \
		--duration 5m \
		--verbose

.PHONY: test-stress
test-stress: setup
	@echo "Running stress tests..."
	@mkdir -p $(RESULTS_DIR)
	$(VENV)/bin/python run_performance_tests.py \
		--test-type stress \
		--host $(HOST) \
		--users 200 \
		--spawn-rate 20 \
		--duration 10m \
		--monitor-resources \
		--verbose

.PHONY: test-volume
test-volume: setup
	@echo "Running volume tests..."
	@mkdir -p $(RESULTS_DIR)
	$(VENV)/bin/python run_performance_tests.py \
		--test-type volume \
		--host $(HOST) \
		--users 100 \
		--spawn-rate 10 \
		--duration 30m \
		--monitor-resources \
		--verbose

.PHONY: test-benchmark
test-benchmark: setup
	@echo "Running benchmark tests..."
	@mkdir -p $(RESULTS_DIR)
	$(VENV)/bin/python -m pytest \
		-m benchmark \
		--benchmark-only \
		--benchmark-sort=mean \
		--benchmark-json=$(RESULTS_DIR)/benchmark_$(TIMESTAMP).json \
		-v

.PHONY: test-locust
test-locust: setup
	@echo "Running Locust load tests..."
	@mkdir -p $(RESULTS_DIR)
	$(VENV)/bin/locust \
		-f locustfile.py \
		--host $(HOST) \
		--users 50 \
		--spawn-rate 5 \
		--run-time 5m \
		--headless \
		--html $(RESULTS_DIR)/locust_report_$(TIMESTAMP).html \
		--csv $(RESULTS_DIR)/locust_stats_$(TIMESTAMP)

.PHONY: test-quick
test-quick: setup
	@echo "Running quick performance validation..."
	@mkdir -p $(RESULTS_DIR)
	$(VENV)/bin/python run_performance_tests.py \
		--test-type load \
		--host $(HOST) \
		--users 10 \
		--spawn-rate 2 \
		--duration 2m \
		--verbose

# Interactive Locust (with web UI)
.PHONY: locust-ui
locust-ui: setup
	@echo "Starting Locust with web UI..."
	@echo "Open http://localhost:8089 in your browser"
	$(VENV)/bin/locust -f locustfile.py --host $(HOST)

# System monitoring
.PHONY: monitor
monitor: setup
	@echo "Monitoring system resources for 5 minutes..."
	@mkdir -p $(RESULTS_DIR)
	$(VENV)/bin/python -c "
import sys
sys.path.append('.')
from run_performance_tests import monitor_system_resources
monitor_system_resources(300, 5)
"

# Reporting
.PHONY: report
report: setup
	@echo "Generating performance test report..."
	$(VENV)/bin/python -c "
import sys
sys.path.append('.')
from run_performance_tests import generate_performance_report
generate_performance_report('$(RESULTS_DIR)')
"

# Validation targets
.PHONY: validate-environment
validate-environment:
	@echo "Validating performance test environment..."
	@echo "Checking if target host is accessible..."
	@curl -f -s $(HOST)/api/health > /dev/null || (echo "❌ Host $(HOST) is not accessible" && exit 1)
	@echo "✅ Host $(HOST) is accessible"
	@echo "Checking system resources..."
	@$(PYTHON) -c "
import psutil
print(f'CPU cores: {psutil.cpu_count()}')
print(f'Memory: {psutil.virtual_memory().total / 1024**3:.1f} GB')
print(f'Disk space: {psutil.disk_usage(\"/\").free / 1024**3:.1f} GB free')
"

.PHONY: validate-thresholds
validate-thresholds: setup
	@echo "Validating performance against thresholds..."
	$(VENV)/bin/python -c "
import yaml
import json
import os
with open('performance_config.yaml', 'r') as f:
    config = yaml.safe_load(f)
thresholds = config['thresholds']
print('Performance Thresholds:')
print(f'  Response Time P95: {thresholds[\"response_time\"][\"p95\"]}ms')
print(f'  Error Rate: {thresholds[\"error_rate\"][\"critical\"]}%')
print(f'  Min Throughput: {thresholds[\"throughput\"][\"min_rps\"]} RPS')
print(f'  Max CPU: {thresholds[\"system_resources\"][\"cpu_percent\"]}%')
print(f'  Max Memory: {thresholds[\"system_resources\"][\"memory_percent\"]}%')
"

# CI/CD integration targets
.PHONY: ci-performance-gate
ci-performance-gate: setup validate-environment
	@echo "Running performance gate for CI/CD..."
	@mkdir -p $(RESULTS_DIR)
	$(VENV)/bin/python run_performance_tests.py \
		--test-type load \
		--host $(HOST) \
		--users 25 \
		--spawn-rate 5 \
		--duration 3m \
		--generate-report
	@echo "Performance gate completed"

.PHONY: nightly-performance
nightly-performance: setup validate-environment
	@echo "Running nightly performance tests..."
	@mkdir -p $(RESULTS_DIR)
	$(VENV)/bin/python run_performance_tests.py \
		--test-type all \
		--host $(HOST) \
		--users 100 \
		--spawn-rate 10 \
		--duration 15m \
		--monitor-resources \
		--generate-report \
		--verbose

# Cleanup targets
.PHONY: clean
clean:
	@echo "Cleaning up test results and artifacts..."
	rm -rf $(RESULTS_DIR)
	rm -rf __pycache__
	rm -rf .pytest_cache
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	@echo "Cleanup completed"

.PHONY: clean-all
clean-all: clean
	@echo "Removing virtual environment..."
	rm -rf $(VENV)
	@echo "Full cleanup completed"

# Development targets
.PHONY: dev-setup
dev-setup: setup
	$(VENV)/bin/pip install -e .
	$(VENV)/bin/pip install pytest-benchmark pytest-xdist pytest-html
	@echo "Development environment ready"

.PHONY: lint
lint: setup
	$(VENV)/bin/flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	$(VENV)/bin/flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

.PHONY: format
format: setup
	$(VENV)/bin/black .
	$(VENV)/bin/isort .

# Docker targets (if using containerized testing)
.PHONY: docker-build
docker-build:
	docker build -t sentinel-performance-tests .

.PHONY: docker-test
docker-test: docker-build
	docker run --rm \
		-v $(PWD)/$(RESULTS_DIR):/app/$(RESULTS_DIR) \
		-e HOST=$(HOST) \
		sentinel-performance-tests \
		make test-quick

# Utility targets
.PHONY: show-config
show-config:
	@echo "Performance Test Configuration:"
	@echo "  Python: $(shell $(PYTHON) --version)"
	@echo "  Host: $(HOST)"
	@echo "  Results Directory: $(RESULTS_DIR)"
	@echo "  Timestamp: $(TIMESTAMP)"
	@echo "  Virtual Environment: $(VENV)"

.PHONY: list-results
list-results:
	@echo "Available test results:"
	@if [ -d "$(RESULTS_DIR)" ]; then \
		ls -la $(RESULTS_DIR)/; \
	else \
		echo "No results directory found"; \
	fi

# Make sure results directory exists for all test targets
$(RESULTS_DIR):
	mkdir -p $(RESULTS_DIR)

# Phony targets to avoid conflicts with files
.PHONY: all install clean clean-all test-all test-load test-stress test-volume test-benchmark test-locust test-quick monitor report