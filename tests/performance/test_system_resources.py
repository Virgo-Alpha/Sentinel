"""
Performance tests for system resource utilization under load.
"""

import pytest
import psutil
import time
import threading
import json
import boto3
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch
import uuid
from datetime import datetime, timezone
import gc
import sys

@pytest.mark.performance
@pytest.mark.benchmark
class TestSystemResourceUtilization:
    """Test system resource utilization under various load conditions."""
    
    def test_cpu_utilization_under_load(self, performance_monitor, benchmark_thresholds,
                                      mock_aws_performance_services, load_test_data):
        """Test CPU utilization during intensive processing."""
        test_name = "cpu_utilization_under_load"
        performance_monitor.start_monitoring(test_name)
        
        # CPU monitoring
        cpu_samples = []
        monitoring_active = threading.Event()
        monitoring_active.set()
        
        def monitor_cpu():
            """Monitor CPU usage in background thread."""
            while monitoring_active.is_set():
                cpu_percent = psutil.cpu_percent(interval=0.1)
                cpu_samples.append({
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent,
                    'cpu_count': psutil.cpu_count(),
                    'load_avg': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
                })
                time.sleep(0.1)
        
        # Start CPU monitoring
        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.start()
        
        try:
            # CPU-intensive processing simulation
            class CPUIntensiveProcessor:
                def __init__(self, table):
                    self.table = table
                    self.processed_count = 0
                
                def cpu_intensive_task(self, data_batch):
                    """Simulate CPU-intensive processing."""
                    start_time = time.perf_counter()
                    
                    try:
                        # Simulate complex calculations (relevancy scoring, text analysis)
                        for item in data_batch:
                            # Simulate text processing
                            text = item['content']
                            
                            # CPU-intensive operations
                            word_count = len(text.split())
                            char_count = len(text)
                            
                            # Simulate keyword matching
                            keywords = ['security', 'vulnerability', 'threat', 'malware', 'exploit']
                            matches = sum(text.lower().count(keyword) for keyword in keywords)
                            
                            # Simulate relevancy calculation
                            relevancy_score = min(1.0, (matches * 0.1) + (word_count / 1000))
                            
                            # Update item
                            item['relevancy_score'] = relevancy_score
                            item['word_count'] = word_count
                            item['keyword_matches'] = matches
                            
                            # Store in database
                            self.table.put_item(Item=item)
                            self.processed_count += 1
                        
                        end_time = time.perf_counter()
                        response_time = (end_time - start_time) * 1000
                        performance_monitor.record_response_time(test_name, response_time)
                        
                        return len(data_batch)
                        
                    except Exception as e:
                        performance_monitor.record_error(test_name, e)
                        raise
            
            processor = CPUIntensiveProcessor(mock_aws_performance_services['dynamodb_table'])
            
            # Generate CPU-intensive workload
            articles = load_test_data['generate_articles'](2000)  # Large dataset
            batch_size = 50
            batches = [articles[i:i + batch_size] for i in range(0, len(articles), batch_size)]
            
            # Process batches concurrently to stress CPU
            with ThreadPoolExecutor(max_workers=psutil.cpu_count()) as executor:
                futures = [
                    executor.submit(processor.cpu_intensive_task, batch)
                    for batch in batches
                ]
                
                completed_batches = 0
                for future in futures:
                    try:
                        batch_size = future.result(timeout=60)
                        completed_batches += 1
                        
                        # Record throughput
                        if completed_batches % 5 == 0:
                            elapsed = time.time() - performance_monitor.metrics[test_name]['start_time']
                            throughput = processor.processed_count / elapsed
                            performance_monitor.record_throughput(test_name, throughput)
                            
                    except Exception as e:
                        performance_monitor.record_error(test_name, e)
        
        finally:
            # Stop CPU monitoring
            monitoring_active.clear()
            monitor_thread.join(timeout=5)
        
        results = performance_monitor.stop_monitoring(test_name)
        
        # Analyze CPU usage
        if cpu_samples:
            max_cpu = max(sample['cpu_percent'] for sample in cpu_samples)
            avg_cpu = sum(sample['cpu_percent'] for sample in cpu_samples) / len(cpu_samples)
            cpu_over_threshold = sum(1 for sample in cpu_samples if sample['cpu_percent'] > benchmark_thresholds['cpu_usage_max'])
            cpu_threshold_percentage = (cpu_over_threshold / len(cpu_samples)) * 100
        else:
            max_cpu = avg_cpu = cpu_threshold_percentage = 0
        
        # Assertions
        assert results['error_rate'] < benchmark_thresholds['error_rate']
        assert avg_cpu < benchmark_thresholds['cpu_usage_max']
        assert cpu_threshold_percentage < 20  # Less than 20% of samples should exceed threshold
        
        print(f"\\nCPU Utilization Test Results for {test_name}:")
        print(f"  Articles processed: {processor.processed_count}")
        print(f"  Batches completed: {completed_batches}")
        print(f"  Max CPU usage: {max_cpu:.1f}%")
        print(f"  Average CPU usage: {avg_cpu:.1f}%")
        print(f"  CPU samples: {len(cpu_samples)}")
        print(f"  Samples over threshold: {cpu_threshold_percentage:.1f}%")
        print(f"  Average processing time: {results['response_time_avg']:.2f}ms")
        print(f"  Error rate: {results['error_rate']:.2%}")
    
    def test_memory_usage_patterns(self, performance_monitor, benchmark_thresholds,
                                 load_test_data):
        """Test memory usage patterns and potential leaks."""
        test_name = "memory_usage_patterns"
        performance_monitor.start_monitoring(test_name)
        
        import gc
        process = psutil.Process()
        
        # Memory monitoring
        memory_samples = []
        
        def track_memory(label):
            """Track memory usage with label."""
            gc.collect()  # Force garbage collection
            memory_info = process.memory_info()
            memory_samples.append({
                'timestamp': time.time(),
                'label': label,
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
                'percent': process.memory_percent(),
                'available_mb': psutil.virtual_memory().available / 1024 / 1024
            })
        
        # Baseline memory usage
        track_memory('baseline')
        
        # Memory-intensive processing
        class MemoryIntensiveProcessor:
            def __init__(self):
                self.data_cache = {}
                self.processed_items = []
            
            def process_large_dataset(self, articles):
                """Process large dataset that uses significant memory."""
                start_time = time.perf_counter()
                
                try:
                    # Simulate memory-intensive operations
                    for i, article in enumerate(articles):
                        # Create large data structures
                        processed_data = {
                            'article_id': article['article_id'],
                            'processed_content': article['content'] * 10,  # Expand content
                            'analysis_results': {
                                'keywords': article['content'].split() * 5,  # Duplicate keywords
                                'sentences': article['content'].split('.') * 3,
                                'metadata': {
                                    'processing_timestamp': datetime.now(timezone.utc).isoformat(),
                                    'processing_id': str(uuid.uuid4()),
                                    'additional_data': list(range(1000))  # Large list
                                }
                            }
                        }
                        
                        # Store in memory cache
                        self.data_cache[article['article_id']] = processed_data
                        self.processed_items.append(processed_data)
                        
                        # Track memory every 100 items
                        if (i + 1) % 100 == 0:
                            track_memory(f'processed_{i + 1}')
                    
                    end_time = time.perf_counter()
                    response_time = (end_time - start_time) * 1000
                    performance_monitor.record_response_time(test_name, response_time)
                    
                    return len(articles)
                    
                except Exception as e:
                    performance_monitor.record_error(test_name, e)
                    raise
            
            def cleanup_cache(self):
                """Clean up memory cache."""
                self.data_cache.clear()
                self.processed_items.clear()
                gc.collect()
        
        processor = MemoryIntensiveProcessor()
        
        try:
            # Process increasingly large datasets
            dataset_sizes = [500, 1000, 1500, 2000]
            
            for size in dataset_sizes:
                articles = load_test_data['generate_articles'](size)
                track_memory(f'before_processing_{size}')\n                \n                processed_count = processor.process_large_dataset(articles)\n                track_memory(f'after_processing_{size}')\n                \n                # Simulate some processing delay\n                time.sleep(0.5)\n                \n                # Partial cleanup\n                if size < max(dataset_sizes):\n                    processor.cleanup_cache()\n                    track_memory(f'after_cleanup_{size}')\n        \n        finally:\n            # Final cleanup\n            processor.cleanup_cache()\n            track_memory('final_cleanup')\n        \n        results = performance_monitor.stop_monitoring(test_name)\n        \n        # Analyze memory usage patterns\n        baseline_memory = memory_samples[0]['rss_mb']\n        max_memory = max(sample['rss_mb'] for sample in memory_samples)\n        final_memory = memory_samples[-1]['rss_mb']\n        memory_growth = max_memory - baseline_memory\n        memory_leak = final_memory - baseline_memory\n        \n        # Calculate memory efficiency\n        peak_usage_samples = [s for s in memory_samples if 'after_processing' in s['label']]\n        if peak_usage_samples:\n            avg_peak_memory = sum(s['rss_mb'] for s in peak_usage_samples) / len(peak_usage_samples)\n        else:\n            avg_peak_memory = max_memory\n        \n        # Assertions\n        assert max_memory < benchmark_thresholds['memory_usage_max']\n        assert memory_leak < benchmark_thresholds['memory_usage_max'] * 0.1  # Memory leak should be minimal\n        assert results['error_rate'] < benchmark_thresholds['error_rate']\n        \n        print(f\"\\nMemory Usage Test Results for {test_name}:\")\n        print(f\"  Baseline memory: {baseline_memory:.1f} MB\")\n        print(f\"  Peak memory: {max_memory:.1f} MB\")\n        print(f\"  Final memory: {final_memory:.1f} MB\")\n        print(f\"  Memory growth: {memory_growth:.1f} MB\")\n        print(f\"  Potential leak: {memory_leak:.1f} MB\")\n        print(f\"  Average peak usage: {avg_peak_memory:.1f} MB\")\n        print(f\"  Memory samples: {len(memory_samples)}\")\n        print(f\"  Processing time: {results['response_time_avg']:.2f}ms\")\n        print(f\"  Error rate: {results['error_rate']:.2%}\")\n    \n    def test_disk_io_performance(self, performance_monitor, benchmark_thresholds,\n                               mock_aws_performance_services, load_test_data):\n        \"\"\"Test disk I/O performance under load.\"\"\"\n        test_name = \"disk_io_performance\"\n        performance_monitor.start_monitoring(test_name)\n        \n        # Disk I/O monitoring\n        io_samples = []\n        \n        def track_disk_io(label):\n            \"\"\"Track disk I/O statistics.\"\"\"\n            disk_io = psutil.disk_io_counters()\n            if disk_io:\n                io_samples.append({\n                    'timestamp': time.time(),\n                    'label': label,\n                    'read_bytes': disk_io.read_bytes,\n                    'write_bytes': disk_io.write_bytes,\n                    'read_count': disk_io.read_count,\n                    'write_count': disk_io.write_count\n                })\n        \n        # Baseline I/O\n        track_disk_io('baseline')\n        \n        # I/O intensive operations\n        class IOIntensiveProcessor:\n            def __init__(self, s3_bucket):\n                self.s3_bucket = s3_bucket\n                self.s3_client = boto3.client('s3', region_name='us-east-1')\n                self.files_processed = 0\n            \n            def process_file_operations(self, articles):\n                \"\"\"Perform I/O intensive file operations.\"\"\"\n                start_time = time.perf_counter()\n                \n                try:\n                    for article in articles:\n                        # Simulate file operations\n                        \n                        # 1. Write article content to S3\n                        content_key = f\"articles/{article['article_id']}/content.json\"\n                        self.s3_client.put_object(\n                            Bucket=self.s3_bucket,\n                            Key=content_key,\n                            Body=json.dumps(article),\n                            ContentType='application/json'\n                        )\n                        \n                        # 2. Write processed data\n                        processed_key = f\"processed/{article['article_id']}/analysis.json\"\n                        analysis_data = {\n                            'article_id': article['article_id'],\n                            'analysis_timestamp': datetime.now(timezone.utc).isoformat(),\n                            'word_count': len(article['content'].split()),\n                            'keywords': article['content'].split()[:50],  # First 50 words\n                            'metadata': article.get('metadata', {})\n                        }\n                        \n                        self.s3_client.put_object(\n                            Bucket=self.s3_bucket,\n                            Key=processed_key,\n                            Body=json.dumps(analysis_data),\n                            ContentType='application/json'\n                        )\n                        \n                        # 3. Read back for verification (simulate processing)\n                        response = self.s3_client.get_object(\n                            Bucket=self.s3_bucket,\n                            Key=content_key\n                        )\n                        content = json.loads(response['Body'].read())\n                        \n                        self.files_processed += 1\n                    \n                    end_time = time.perf_counter()\n                    response_time = (end_time - start_time) * 1000\n                    performance_monitor.record_response_time(test_name, response_time)\n                    \n                    return len(articles)\n                    \n                except Exception as e:\n                    performance_monitor.record_error(test_name, e)\n                    raise\n        \n        processor = IOIntensiveProcessor(mock_aws_performance_services['s3_bucket'])\n        \n        # Process articles in batches to stress I/O\n        articles = load_test_data['generate_articles'](500)  # Moderate size for I/O testing\n        batch_size = 25\n        batches = [articles[i:i + batch_size] for i in range(0, len(articles), batch_size)]\n        \n        # Track I/O before processing\n        track_disk_io('before_processing')\n        \n        # Execute I/O operations\n        with ThreadPoolExecutor(max_workers=5) as executor:  # Limit to avoid overwhelming I/O\n            futures = []\n            \n            for i, batch in enumerate(batches):\n                future = executor.submit(processor.process_file_operations, batch)\n                futures.append(future)\n                \n                # Track I/O periodically\n                if (i + 1) % 5 == 0:\n                    track_disk_io(f'batch_{i + 1}')\n            \n            # Wait for completion\n            completed_batches = 0\n            for future in futures:\n                try:\n                    batch_size = future.result(timeout=120)  # Longer timeout for I/O\n                    completed_batches += 1\n                except Exception as e:\n                    performance_monitor.record_error(test_name, e)\n        \n        # Final I/O tracking\n        track_disk_io('after_processing')\n        \n        results = performance_monitor.stop_monitoring(test_name)\n        \n        # Analyze I/O performance\n        if len(io_samples) >= 2:\n            baseline_io = io_samples[0]\n            final_io = io_samples[-1]\n            \n            total_read_bytes = final_io['read_bytes'] - baseline_io['read_bytes']\n            total_write_bytes = final_io['write_bytes'] - baseline_io['write_bytes']\n            total_read_ops = final_io['read_count'] - baseline_io['read_count']\n            total_write_ops = final_io['write_count'] - baseline_io['write_count']\n            \n            duration_seconds = results['duration']\n            read_throughput_mb_s = (total_read_bytes / 1024 / 1024) / duration_seconds if duration_seconds > 0 else 0\n            write_throughput_mb_s = (total_write_bytes / 1024 / 1024) / duration_seconds if duration_seconds > 0 else 0\n        else:\n            total_read_bytes = total_write_bytes = 0\n            total_read_ops = total_write_ops = 0\n            read_throughput_mb_s = write_throughput_mb_s = 0\n        \n        # Assertions\n        assert results['error_rate'] < benchmark_thresholds['error_rate']\n        assert processor.files_processed > 0\n        \n        print(f\"\\nDisk I/O Performance Test Results for {test_name}:\")\n        print(f\"  Files processed: {processor.files_processed}\")\n        print(f\"  Batches completed: {completed_batches}\")\n        print(f\"  Total read bytes: {total_read_bytes / 1024 / 1024:.1f} MB\")\n        print(f\"  Total write bytes: {total_write_bytes / 1024 / 1024:.1f} MB\")\n        print(f\"  Read operations: {total_read_ops}\")\n        print(f\"  Write operations: {total_write_ops}\")\n        print(f\"  Read throughput: {read_throughput_mb_s:.2f} MB/s\")\n        print(f\"  Write throughput: {write_throughput_mb_s:.2f} MB/s\")\n        print(f\"  Average processing time: {results['response_time_avg']:.2f}ms\")\n        print(f\"  Error rate: {results['error_rate']:.2%}\")\n    \n    def test_network_utilization(self, performance_monitor, benchmark_thresholds):\n        \"\"\"Test network utilization under concurrent requests.\"\"\"\n        test_name = \"network_utilization\"\n        performance_monitor.start_monitoring(test_name)\n        \n        # Network monitoring\n        network_samples = []\n        \n        def track_network_io(label):\n            \"\"\"Track network I/O statistics.\"\"\"\n            net_io = psutil.net_io_counters()\n            if net_io:\n                network_samples.append({\n                    'timestamp': time.time(),\n                    'label': label,\n                    'bytes_sent': net_io.bytes_sent,\n                    'bytes_recv': net_io.bytes_recv,\n                    'packets_sent': net_io.packets_sent,\n                    'packets_recv': net_io.packets_recv\n                })\n        \n        # Baseline network usage\n        track_network_io('baseline')\n        \n        # Network-intensive operations\n        class NetworkIntensiveProcessor:\n            def __init__(self):\n                self.requests_made = 0\n                self.data_transferred = 0\n            \n            def simulate_api_requests(self, request_count):\n                \"\"\"Simulate network-intensive API requests.\"\"\"\n                start_time = time.perf_counter()\n                \n                try:\n                    for i in range(request_count):\n                        # Simulate HTTP request/response\n                        request_data = {\n                            'request_id': str(uuid.uuid4()),\n                            'query': f'security vulnerability {i}',\n                            'filters': {\n                                'date_range': '7d',\n                                'sources': ['CISA', 'NCSC', 'Microsoft'],\n                                'relevancy_threshold': 0.7\n                            },\n                            'timestamp': datetime.now(timezone.utc).isoformat()\n                        }\n                        \n                        # Simulate response data\n                        response_data = {\n                            'request_id': request_data['request_id'],\n                            'results': [\n                                {\n                                    'article_id': str(uuid.uuid4()),\n                                    'title': f'Security Article {j}',\n                                    'content': 'This is simulated article content for network testing. ' * 20,\n                                    'relevancy_score': 0.8 + (j * 0.01)\n                                }\n                                for j in range(20)  # 20 results per request\n                            ],\n                            'total_count': 20,\n                            'processing_time_ms': 150 + (i % 50)\n                        }\n                        \n                        # Calculate data transfer\n                        request_size = len(json.dumps(request_data))\n                        response_size = len(json.dumps(response_data))\n                        self.data_transferred += request_size + response_size\n                        \n                        # Simulate network delay\n                        time.sleep(0.01)  # 10ms network delay\n                        \n                        self.requests_made += 1\n                    \n                    end_time = time.perf_counter()\n                    response_time = (end_time - start_time) * 1000\n                    performance_monitor.record_response_time(test_name, response_time)\n                    \n                    return request_count\n                    \n                except Exception as e:\n                    performance_monitor.record_error(test_name, e)\n                    raise\n        \n        processor = NetworkIntensiveProcessor()\n        \n        # Execute concurrent network operations\n        with ThreadPoolExecutor(max_workers=10) as executor:\n            futures = []\n            \n            # Create multiple concurrent request batches\n            for i in range(20):  # 20 concurrent batches\n                future = executor.submit(processor.simulate_api_requests, 25)  # 25 requests per batch\n                futures.append(future)\n                \n                # Track network periodically\n                if (i + 1) % 5 == 0:\n                    track_network_io(f'batch_{i + 1}')\n            \n            # Wait for completion\n            completed_batches = 0\n            for future in futures:\n                try:\n                    requests_completed = future.result(timeout=60)\n                    completed_batches += 1\n                    \n                    # Record throughput\n                    if completed_batches % 5 == 0:\n                        elapsed = time.time() - performance_monitor.metrics[test_name]['start_time']\n                        throughput = processor.requests_made / elapsed\n                        performance_monitor.record_throughput(test_name, throughput)\n                        \n                except Exception as e:\n                    performance_monitor.record_error(test_name, e)\n        \n        # Final network tracking\n        track_network_io('final')\n        \n        results = performance_monitor.stop_monitoring(test_name)\n        \n        # Analyze network performance\n        if len(network_samples) >= 2:\n            baseline_net = network_samples[0]\n            final_net = network_samples[-1]\n            \n            total_sent = final_net['bytes_sent'] - baseline_net['bytes_sent']\n            total_recv = final_net['bytes_recv'] - baseline_net['bytes_recv']\n            total_packets_sent = final_net['packets_sent'] - baseline_net['packets_sent']\n            total_packets_recv = final_net['packets_recv'] - baseline_net['packets_recv']\n            \n            duration_seconds = results['duration']\n            send_throughput_mb_s = (total_sent / 1024 / 1024) / duration_seconds if duration_seconds > 0 else 0\n            recv_throughput_mb_s = (total_recv / 1024 / 1024) / duration_seconds if duration_seconds > 0 else 0\n        else:\n            total_sent = total_recv = 0\n            total_packets_sent = total_packets_recv = 0\n            send_throughput_mb_s = recv_throughput_mb_s = 0\n        \n        # Assertions\n        assert results['error_rate'] < benchmark_thresholds['error_rate']\n        assert processor.requests_made > 0\n        \n        print(f\"\\nNetwork Utilization Test Results for {test_name}:\")\n        print(f\"  Requests made: {processor.requests_made}\")\n        print(f\"  Batches completed: {completed_batches}\")\n        print(f\"  Data transferred (app): {processor.data_transferred / 1024 / 1024:.1f} MB\")\n        print(f\"  Bytes sent (system): {total_sent / 1024 / 1024:.1f} MB\")\n        print(f\"  Bytes received (system): {total_recv / 1024 / 1024:.1f} MB\")\n        print(f\"  Packets sent: {total_packets_sent}\")\n        print(f\"  Packets received: {total_packets_recv}\")\n        print(f\"  Send throughput: {send_throughput_mb_s:.2f} MB/s\")\n        print(f\"  Receive throughput: {recv_throughput_mb_s:.2f} MB/s\")\n        print(f\"  Average request time: {results['response_time_avg']:.2f}ms\")\n        print(f\"  Request throughput: {results['throughput_avg']:.1f} req/sec\")\n        print(f\"  Error rate: {results['error_rate']:.2%}\")"