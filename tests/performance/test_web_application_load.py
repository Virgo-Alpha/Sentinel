"""
Load tests for web application concurrent user scenarios.
"""

import pytest
import requests
import json
import time
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch
import uuid
from datetime import datetime, timezone

@pytest.mark.performance
@pytest.mark.load
class TestWebApplicationLoad:
    """Load tests for web application user interactions."""
    
    def test_concurrent_user_queries(self, performance_monitor, benchmark_thresholds,
                                   load_test_data):
        """Test concurrent user search queries."""
        test_name = "concurrent_user_queries"
        performance_monitor.start_monitoring(test_name)
        
        # Mock API endpoint
        class MockAPIServer:
            def __init__(self):
                self.request_count = 0
                self.active_connections = 0
            
            def search_articles(self, query_data):
                """Mock article search endpoint."""
                start_time = time.perf_counter()
                self.active_connections += 1
                
                try:
                    # Simulate database query processing time
                    processing_time = 0.1 + (self.active_connections * 0.01)  # Simulate load impact
                    time.sleep(processing_time)
                    
                    # Generate mock results
                    results = []
                    for i in range(min(20, query_data.get('limit', 20))):
                        results.append({
                            'article_id': str(uuid.uuid4()),
                            'title': f'Search Result {i} for: {query_data["query"]}',
                            'relevancy_score': 0.9 - (i * 0.02),
                            'feed_source': 'CISA',
                            'published_at': datetime.now(timezone.utc).isoformat()
                        })
                    
                    response = {
                        'results': results,
                        'total_count': len(results),
                        'query_time_ms': processing_time * 1000,
                        'pagination': {
                            'page': query_data.get('page', 1),
                            'limit': query_data.get('limit', 20),
                            'has_more': len(results) == query_data.get('limit', 20)
                        }
                    }
                    
                    self.request_count += 1
                    
                    end_time = time.perf_counter()
                    response_time = (end_time - start_time) * 1000
                    performance_monitor.record_response_time(test_name, response_time)
                    
                    return response
                    
                except Exception as e:
                    performance_monitor.record_error(test_name, e)
                    raise
                finally:
                    self.active_connections -= 1
        
        api_server = MockAPIServer()
        
        # Generate concurrent user requests
        api_requests = load_test_data['generate_api_requests'](200)  # 200 concurrent users
        
        def execute_user_session(user_requests):
            """Execute a user session with multiple requests."""
            session_results = []
            
            # Simulate user making multiple queries in a session
            for request in user_requests[:5]:  # 5 queries per user session
                try:
                    result = api_server.search_articles(request['body'])
                    session_results.append(result)
                    
                    # Simulate user think time
                    time.sleep(0.1)
                    
                except Exception as e:
                    performance_monitor.record_error(test_name, e)
            
            return len(session_results)
        
        # Group requests into user sessions
        users_per_session = 5
        user_sessions = [
            api_requests[i:i + users_per_session] 
            for i in range(0, len(api_requests), users_per_session)
        ]
        
        # Execute concurrent user sessions
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(execute_user_session, session)
                for session in user_sessions
            ]
            
            completed_sessions = 0
            total_queries = 0
            
            for future in as_completed(futures):
                try:
                    queries_completed = future.result(timeout=60)
                    total_queries += queries_completed
                    completed_sessions += 1
                    
                    # Record throughput periodically
                    if completed_sessions % 5 == 0:
                        elapsed = time.time() - performance_monitor.metrics[test_name]['start_time']
                        throughput = total_queries / elapsed
                        performance_monitor.record_throughput(test_name, throughput)
                        
                except Exception as e:
                    performance_monitor.record_error(test_name, e)
        
        results = performance_monitor.stop_monitoring(test_name)
        
        # Assertions
        assert results['total_requests'] > 0
        assert results['error_rate'] < benchmark_thresholds['error_rate']
        assert results['response_time_p95'] < benchmark_thresholds['response_time_p95']
        assert results['throughput_avg'] >= benchmark_thresholds['throughput_min']
        
        print(f"\\nConcurrent User Test Results for {test_name}:")
        print(f"  User sessions: {completed_sessions}")
        print(f"  Total queries: {total_queries}")
        print(f"  API requests processed: {api_server.request_count}")
        print(f"  Average response time: {results['response_time_avg']:.2f}ms")
        print(f"  P95 response time: {results['response_time_p95']:.2f}ms")
        print(f"  P99 response time: {results['response_time_p99']:.2f}ms")
        print(f"  Error rate: {results['error_rate']:.2%}")
        print(f"  Average throughput: {results['throughput_avg']:.1f} queries/sec")
    
    @pytest.mark.asyncio
    async def test_websocket_concurrent_connections(self, performance_monitor,
                                                  benchmark_thresholds):
        """Test concurrent WebSocket connections for real-time updates."""
        test_name = "websocket_concurrent_connections"
        performance_monitor.start_monitoring(test_name)
        
        # Mock WebSocket server
        class MockWebSocketServer:
            def __init__(self):
                self.connections = {}
                self.message_count = 0
            
            async def handle_connection(self, connection_id):
                """Handle a WebSocket connection."""
                start_time = time.perf_counter()
                
                try:
                    self.connections[connection_id] = {
                        'connected_at': time.time(),
                        'messages_received': 0
                    }
                    
                    # Simulate connection lifecycle
                    await asyncio.sleep(0.1)  # Connection setup
                    
                    # Simulate receiving messages
                    for i in range(10):  # 10 messages per connection
                        await asyncio.sleep(0.05)  # Message processing
                        self.connections[connection_id]['messages_received'] += 1
                        self.message_count += 1
                    
                    # Simulate sending updates
                    for i in range(5):  # 5 updates sent to client
                        await asyncio.sleep(0.02)  # Update generation
                    
                    end_time = time.perf_counter()
                    response_time = (end_time - start_time) * 1000
                    performance_monitor.record_response_time(test_name, response_time)
                    
                    return self.connections[connection_id]['messages_received']
                    
                except Exception as e:
                    performance_monitor.record_error(test_name, e)
                    raise
                finally:
                    if connection_id in self.connections:
                        del self.connections[connection_id]
        
        ws_server = MockWebSocketServer()
        
        # Create concurrent WebSocket connections
        connection_count = 100
        connection_ids = [f"conn_{i}" for i in range(connection_count)]
        
        # Execute concurrent connections
        semaphore = asyncio.Semaphore(25)  # Limit concurrent connections
        
        async def handle_connection_with_semaphore(conn_id):
            async with semaphore:
                return await ws_server.handle_connection(conn_id)
        
        tasks = [handle_connection_with_semaphore(conn_id) for conn_id in connection_ids]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_connections = [r for r in results_list if isinstance(r, int)]
        exceptions = [r for r in results_list if isinstance(r, Exception)]
        
        for exc in exceptions:
            performance_monitor.record_error(test_name, exc)
        
        results = performance_monitor.stop_monitoring(test_name)
        
        # Assertions
        assert len(successful_connections) > 0
        assert len(exceptions) / len(results_list) < benchmark_thresholds['error_rate']
        assert results['response_time_p95'] < benchmark_thresholds['response_time_p95']
        
        print(f"\\nWebSocket Load Test Results for {test_name}:")
        print(f"  Successful connections: {len(successful_connections)}")
        print(f"  Failed connections: {len(exceptions)}")
        print(f"  Total messages processed: {ws_server.message_count}")
        print(f"  Average connection time: {results['response_time_avg']:.2f}ms")
        print(f"  P95 connection time: {results['response_time_p95']:.2f}ms")
        print(f"  Error rate: {results['error_rate']:.2%}")
    
    def test_bulk_report_generation_load(self, performance_monitor, benchmark_thresholds,
                                       load_test_data):
        """Test bulk report generation under load."""
        test_name = "bulk_report_generation"
        performance_monitor.start_monitoring(test_name)
        
        # Mock report generator
        class MockReportGenerator:
            def __init__(self):
                self.reports_generated = 0
            
            def generate_report(self, report_config):
                """Generate a report based on configuration."""
                start_time = time.perf_counter()
                
                try:
                    # Simulate report generation processing
                    article_count = report_config.get('article_count', 100)
                    processing_time = 0.5 + (article_count / 1000)  # Scale with article count
                    
                    time.sleep(processing_time)
                    
                    # Generate mock report data
                    report_data = {
                        'report_id': str(uuid.uuid4()),
                        'title': report_config['title'],
                        'generated_at': datetime.now(timezone.utc).isoformat(),
                        'article_count': article_count,
                        'summary': {
                            'high_priority': article_count // 10,
                            'medium_priority': article_count // 2,
                            'low_priority': article_count - (article_count // 10) - (article_count // 2)
                        },
                        'size_mb': article_count * 0.01  # Estimate report size
                    }
                    
                    self.reports_generated += 1
                    
                    end_time = time.perf_counter()
                    response_time = (end_time - start_time) * 1000
                    performance_monitor.record_response_time(test_name, response_time)
                    
                    return report_data
                    
                except Exception as e:
                    performance_monitor.record_error(test_name, e)
                    raise
        
        report_generator = MockReportGenerator()
        
        # Generate report configurations
        report_configs = []
        for i in range(50):  # 50 concurrent report requests
            report_configs.append({
                'title': f'Security Report {i}',
                'date_range': '30d',
                'article_count': 100 + (i * 10),  # Varying report sizes
                'format': 'xlsx',
                'filters': {
                    'sources': ['CISA', 'NCSC', 'Microsoft'],
                    'relevancy_threshold': 0.7
                }
            })
        
        # Execute concurrent report generation
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(report_generator.generate_report, config)
                for config in report_configs
            ]
            
            completed_reports = 0
            total_size_mb = 0
            
            for future in as_completed(futures):
                try:
                    report_data = future.result(timeout=120)  # Longer timeout for reports
                    completed_reports += 1
                    total_size_mb += report_data['size_mb']
                    
                    # Record throughput
                    if completed_reports % 5 == 0:
                        elapsed = time.time() - performance_monitor.metrics[test_name]['start_time']
                        throughput = completed_reports / elapsed
                        performance_monitor.record_throughput(test_name, throughput)
                        
                except Exception as e:
                    performance_monitor.record_error(test_name, e)
        
        results = performance_monitor.stop_monitoring(test_name)
        
        # Assertions
        assert completed_reports > 0
        assert results['error_rate'] < benchmark_thresholds['error_rate']
        # Reports can take longer, so use a higher threshold
        assert results['response_time_p95'] < benchmark_thresholds['response_time_p95'] * 5
        
        print(f"\\nBulk Report Generation Test Results for {test_name}:")
        print(f"  Reports generated: {completed_reports}")
        print(f"  Total report size: {total_size_mb:.1f} MB")
        print(f"  Average generation time: {results['response_time_avg']:.2f}ms")
        print(f"  P95 generation time: {results['response_time_p95']:.2f}ms")
        print(f"  Error rate: {results['error_rate']:.2%}")
        print(f"  Average throughput: {results['throughput_avg']:.2f} reports/sec")
    
    def test_dashboard_refresh_load(self, performance_monitor, benchmark_thresholds):
        """Test dashboard refresh under concurrent user load."""
        test_name = "dashboard_refresh_load"
        performance_monitor.start_monitoring(test_name)
        
        # Mock dashboard data service
        class MockDashboardService:
            def __init__(self):
                self.refresh_count = 0
            
            def get_dashboard_data(self, user_id):
                """Get dashboard data for a user."""
                start_time = time.perf_counter()
                
                try:
                    # Simulate dashboard data aggregation
                    time.sleep(0.2)  # Simulate database queries and aggregation
                    
                    dashboard_data = {
                        'user_id': user_id,
                        'summary': {
                            'total_articles': 1500 + (hash(user_id) % 500),
                            'pending_review': 25 + (hash(user_id) % 10),
                            'high_priority': 5 + (hash(user_id) % 3),
                            'last_updated': datetime.now(timezone.utc).isoformat()
                        },
                        'recent_articles': [
                            {
                                'id': str(uuid.uuid4()),
                                'title': f'Recent Article {i}',
                                'relevancy_score': 0.8 + (i * 0.02)
                            }
                            for i in range(10)
                        ],
                        'alerts': [
                            {
                                'id': str(uuid.uuid4()),
                                'message': f'Alert {i} for user {user_id}',
                                'severity': 'high' if i < 2 else 'medium'
                            }
                            for i in range(3)
                        ]
                    }
                    
                    self.refresh_count += 1
                    
                    end_time = time.perf_counter()
                    response_time = (end_time - start_time) * 1000
                    performance_monitor.record_response_time(test_name, response_time)
                    
                    return dashboard_data
                    
                except Exception as e:
                    performance_monitor.record_error(test_name, e)
                    raise
        
        dashboard_service = MockDashboardService()
        
        # Simulate concurrent dashboard refreshes
        user_ids = [f"user_{i}" for i in range(100)]  # 100 concurrent users
        
        def simulate_user_dashboard_activity(user_id):
            """Simulate user dashboard activity with multiple refreshes."""
            refreshes_completed = 0
            
            # Each user refreshes dashboard multiple times
            for _ in range(5):  # 5 refreshes per user
                try:
                    dashboard_data = dashboard_service.get_dashboard_data(user_id)
                    refreshes_completed += 1
                    
                    # Simulate user interaction time
                    time.sleep(0.1)
                    
                except Exception as e:
                    performance_monitor.record_error(test_name, e)
            
            return refreshes_completed
        
        # Execute concurrent dashboard activity
        with ThreadPoolExecutor(max_workers=25) as executor:
            futures = [
                executor.submit(simulate_user_dashboard_activity, user_id)
                for user_id in user_ids
            ]
            
            total_refreshes = 0
            completed_users = 0
            
            for future in as_completed(futures):
                try:
                    user_refreshes = future.result(timeout=60)
                    total_refreshes += user_refreshes
                    completed_users += 1
                    
                    # Record throughput
                    if completed_users % 10 == 0:
                        elapsed = time.time() - performance_monitor.metrics[test_name]['start_time']
                        throughput = total_refreshes / elapsed
                        performance_monitor.record_throughput(test_name, throughput)
                        
                except Exception as e:
                    performance_monitor.record_error(test_name, e)
        
        results = performance_monitor.stop_monitoring(test_name)
        
        # Assertions
        assert total_refreshes > 0
        assert results['error_rate'] < benchmark_thresholds['error_rate']
        assert results['response_time_p95'] < benchmark_thresholds['response_time_p95']
        
        print(f"\\nDashboard Load Test Results for {test_name}:")
        print(f"  Users simulated: {completed_users}")
        print(f"  Total refreshes: {total_refreshes}")
        print(f"  Service refresh count: {dashboard_service.refresh_count}")
        print(f"  Average response time: {results['response_time_avg']:.2f}ms")
        print(f"  P95 response time: {results['response_time_p95']:.2f}ms")
        print(f"  Error rate: {results['error_rate']:.2%}")
        print(f"  Average throughput: {results['throughput_avg']:.1f} refreshes/sec")