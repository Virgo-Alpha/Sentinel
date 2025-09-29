"""
Performance testing configuration and fixtures.
"""

import pytest
import boto3
import json
import time
import psutil
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from moto import mock_dynamodb, mock_s3, mock_sqs, mock_lambda
import uuid

# Performance test configuration
PERFORMANCE_CONFIG = {
    'load_test': {
        'users': 50,
        'spawn_rate': 5,
        'duration': '5m',
        'host': 'http://localhost:3000'
    },
    'stress_test': {
        'users': 200,
        'spawn_rate': 20,
        'duration': '10m'
    },
    'volume_test': {
        'articles_per_batch': 1000,
        'concurrent_batches': 10,
        'total_articles': 10000
    },
    'thresholds': {
        'response_time_p95': 2000,  # ms
        'response_time_p99': 5000,  # ms
        'error_rate': 0.01,  # 1%
        'throughput_min': 100,  # requests/second
        'memory_usage_max': 512,  # MB per Lambda
        'cpu_usage_max': 80  # %
    }
}

@pytest.fixture(scope="session")
def performance_config():
    """Performance test configuration."""
    return PERFORMANCE_CONFIG

@pytest.fixture
def performance_monitor():
    """Performance monitoring utilities."""
    class PerformanceMonitor:
        def __init__(self):
            self.metrics = {}
            self.start_time = None
            self.process = psutil.Process()
        
        def start_monitoring(self, test_name):
            """Start performance monitoring for a test."""
            self.start_time = time.time()
            self.metrics[test_name] = {
                'start_time': self.start_time,
                'start_memory': self.process.memory_info().rss / 1024 / 1024,  # MB
                'start_cpu': self.process.cpu_percent(),
                'response_times': [],
                'errors': [],
                'throughput': []
            }
        
        def record_response_time(self, test_name, response_time_ms):
            """Record response time for a test."""
            if test_name in self.metrics:
                self.metrics[test_name]['response_times'].append(response_time_ms)
        
        def record_error(self, test_name, error):
            """Record error for a test."""
            if test_name in self.metrics:
                self.metrics[test_name]['errors'].append({
                    'timestamp': time.time(),
                    'error': str(error)
                })
        
        def record_throughput(self, test_name, requests_per_second):
            """Record throughput for a test."""
            if test_name in self.metrics:
                self.metrics[test_name]['throughput'].append(requests_per_second)
        
        def stop_monitoring(self, test_name):
            """Stop monitoring and calculate final metrics."""
            if test_name not in self.metrics:
                return None
            
            end_time = time.time()
            end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            end_cpu = self.process.cpu_percent()
            
            metrics = self.metrics[test_name]
            duration = end_time - metrics['start_time']
            
            # Calculate statistics
            response_times = metrics['response_times']
            if response_times:
                response_times.sort()
                p50 = response_times[len(response_times) // 2]
                p95 = response_times[int(len(response_times) * 0.95)]
                p99 = response_times[int(len(response_times) * 0.99)]
                avg_response_time = sum(response_times) / len(response_times)
            else:
                p50 = p95 = p99 = avg_response_time = 0
            
            error_rate = len(metrics['errors']) / max(len(response_times), 1)
            avg_throughput = sum(metrics['throughput']) / max(len(metrics['throughput']), 1) if metrics['throughput'] else 0
            
            return {
                'test_name': test_name,
                'duration': duration,
                'total_requests': len(response_times),
                'total_errors': len(metrics['errors']),
                'error_rate': error_rate,
                'response_time_avg': avg_response_time,
                'response_time_p50': p50,
                'response_time_p95': p95,
                'response_time_p99': p99,
                'throughput_avg': avg_throughput,
                'memory_start': metrics['start_memory'],
                'memory_end': end_memory,
                'memory_delta': end_memory - metrics['start_memory'],
                'cpu_start': metrics['start_cpu'],
                'cpu_end': end_cpu
            }
        
        def get_system_metrics(self):
            """Get current system metrics."""
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'memory_available': psutil.virtual_memory().available / 1024 / 1024,  # MB
                'disk_usage': psutil.disk_usage('/').percent,
                'network_io': psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
            }
    
    return PerformanceMonitor()

@pytest.fixture
def load_test_data():
    """Generate test data for load testing."""
    def generate_articles(count=100):
        """Generate test articles for load testing."""
        articles = []
        for i in range(count):
            articles.append({
                'article_id': str(uuid.uuid4()),
                'title': f'Performance Test Article {i}',
                'content': f'This is test content for performance testing article number {i}. ' * 10,
                'url': f'https://example.com/article-{i}',
                'feed_source': 'PERFORMANCE_TEST',
                'published_at': datetime.now(timezone.utc).isoformat(),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'status': 'pending_review',
                'relevancy_score': 0.75 + (i % 25) / 100,  # Vary scores
                'metadata': {
                    'author': f'Test Author {i % 10}',
                    'tags': ['performance', 'test', f'batch-{i // 100}'],
                    'language': 'en'
                }
            })
        return articles
    
    def generate_feed_events(count=50):
        """Generate SQS feed events for testing."""
        events = []
        for i in range(count):
            events.append({
                'Records': [{
                    'eventSource': 'aws:sqs',
                    'eventName': 'Insert',
                    'body': json.dumps({
                        'feed_url': f'https://example.com/feed-{i}.xml',
                        'feed_source': f'TEST_FEED_{i}',
                        'last_updated': datetime.now(timezone.utc).isoformat()
                    }),
                    'messageAttributes': {
                        'correlationId': {
                            'stringValue': str(uuid.uuid4()),
                            'dataType': 'String'
                        }
                    }
                }]
            })
        return events
    
    def generate_api_requests(count=100):
        """Generate API requests for testing."""
        requests = []
        query_templates = [
            'AWS security vulnerability',
            'Microsoft 365 update',
            'Fortinet security advisory',
            'CVE-2024 critical',
            'ransomware attack',
            'phishing campaign',
            'zero-day exploit',
            'security patch'
        ]
        
        for i in range(count):
            requests.append({
                'method': 'POST',
                'path': '/api/articles/search',
                'headers': {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer test-token-{i}',
                    'X-Correlation-ID': str(uuid.uuid4())
                },
                'body': {
                    'query': query_templates[i % len(query_templates)],
                    'filters': {
                        'date_range': '7d',
                        'sources': ['CISA', 'NCSC', 'Microsoft'],
                        'relevancy_threshold': 0.6
                    },
                    'pagination': {
                        'page': (i % 10) + 1,
                        'limit': 20
                    }
                }
            })
        return requests
    
    return {
        'generate_articles': generate_articles,
        'generate_feed_events': generate_feed_events,
        'generate_api_requests': generate_api_requests
    }

@pytest.fixture
def mock_aws_performance_services():
    """Mock AWS services optimized for performance testing."""
    with mock_dynamodb(), mock_s3(), mock_sqs(), mock_lambda():
        # Create performance-optimized mock resources
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create table with higher throughput for performance testing
        table = dynamodb.create_table(
            TableName='sentinel-articles-perf-test',
            KeySchema=[
                {'AttributeName': 'article_id', 'KeyType': 'HASH'},
                {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'article_id', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'},
                {'AttributeName': 'feed_source', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'feed-source-index',
                    'KeySchema': [
                        {'AttributeName': 'feed_source', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 100, 'WriteCapacityUnits': 100}
                },
                {
                    'IndexName': 'status-index',
                    'KeySchema': [
                        {'AttributeName': 'status', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 100, 'WriteCapacityUnits': 100}
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 100, 'WriteCapacityUnits': 100}
        )
        
        # Wait for table creation
        table.meta.client.get_waiter('table_exists').wait(TableName='sentinel-articles-perf-test')
        
        # Create S3 bucket
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='sentinel-perf-test-bucket')
        
        # Create SQS queues
        sqs = boto3.client('sqs', region_name='us-east-1')
        queue_url = sqs.create_queue(
            QueueName='sentinel-perf-test-queue',
            Attributes={
                'DelaySeconds': '0',
                'MessageRetentionPeriod': '1209600',
                'VisibilityTimeoutSeconds': '300',
                'ReceiveMessageWaitTimeSeconds': '20'  # Long polling
            }
        )['QueueUrl']
        
        yield {
            'dynamodb_table': table,
            's3_bucket': 'sentinel-perf-test-bucket',
            'sqs_queue_url': queue_url
        }

@pytest.fixture
def benchmark_thresholds(performance_config):
    """Performance benchmark thresholds."""
    return performance_config['thresholds']

# Performance test markers
def pytest_configure(config):
    """Configure pytest with performance test markers."""
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "load: mark test as a load test"
    )
    config.addinivalue_line(
        "markers", "stress: mark test as a stress test"
    )
    config.addinivalue_line(
        "markers", "volume: mark test as a volume test"
    )
    config.addinivalue_line(
        "markers", "benchmark: mark test as a benchmark test"
    )

def pytest_collection_modifyitems(config, items):
    """Add performance markers based on test names."""
    for item in items:
        if "performance" in str(item.fspath) or "performance" in item.name:
            item.add_marker(pytest.mark.performance)
        
        if "load" in item.name:
            item.add_marker(pytest.mark.load)
        elif "stress" in item.name:
            item.add_marker(pytest.mark.stress)
        elif "volume" in item.name:
            item.add_marker(pytest.mark.volume)
        elif "benchmark" in item.name:
            item.add_marker(pytest.mark.benchmark)

# Utility functions for performance testing
class PerformanceTestUtils:
    """Utility functions for performance testing."""
    
    @staticmethod
    def measure_execution_time(func, *args, **kwargs):
        """Measure function execution time."""
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = e
        end_time = time.perf_counter()
        
        return {
            'result': result,
            'success': success,
            'error': error,
            'execution_time_ms': (end_time - start_time) * 1000,
            'start_time': start_time,
            'end_time': end_time
        }
    
    @staticmethod
    def calculate_percentiles(values, percentiles=[50, 95, 99]):
        """Calculate percentiles for a list of values."""
        if not values:
            return {p: 0 for p in percentiles}
        
        sorted_values = sorted(values)
        result = {}
        
        for p in percentiles:
            index = int(len(sorted_values) * p / 100)
            if index >= len(sorted_values):
                index = len(sorted_values) - 1
            result[p] = sorted_values[index]
        
        return result
    
    @staticmethod
    def generate_performance_report(metrics, thresholds):
        """Generate performance test report."""
        report = {
            'summary': {
                'total_tests': len(metrics),
                'passed_tests': 0,
                'failed_tests': 0,
                'performance_issues': []
            },
            'details': metrics,
            'thresholds': thresholds
        }
        
        for test_name, test_metrics in metrics.items():
            # Check against thresholds
            issues = []
            
            if test_metrics.get('response_time_p95', 0) > thresholds['response_time_p95']:
                issues.append(f"P95 response time ({test_metrics['response_time_p95']}ms) exceeds threshold ({thresholds['response_time_p95']}ms)")
            
            if test_metrics.get('response_time_p99', 0) > thresholds['response_time_p99']:
                issues.append(f"P99 response time ({test_metrics['response_time_p99']}ms) exceeds threshold ({thresholds['response_time_p99']}ms)")
            
            if test_metrics.get('error_rate', 0) > thresholds['error_rate']:
                issues.append(f"Error rate ({test_metrics['error_rate']:.2%}) exceeds threshold ({thresholds['error_rate']:.2%})")
            
            if test_metrics.get('throughput_avg', 0) < thresholds['throughput_min']:
                issues.append(f"Throughput ({test_metrics['throughput_avg']:.1f} req/s) below threshold ({thresholds['throughput_min']} req/s)")
            
            if issues:
                report['summary']['failed_tests'] += 1
                report['summary']['performance_issues'].extend([f"{test_name}: {issue}" for issue in issues])
            else:
                report['summary']['passed_tests'] += 1
        
        return report

@pytest.fixture
def perf_utils():
    """Performance testing utilities."""
    return PerformanceTestUtils()