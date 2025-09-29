"""
Performance tests for bulk operations and report generation.

Tests system performance for large-scale operations like
bulk report generation and data export.
"""

import pytest
import json
import time
import threading
from unittest.mock import patch, MagicMock
import uuid
from typing import List, Dict, Any
import tempfile
import os

# Import Lambda functions for testing
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from lambda_tools.query_kb import lambda_handler as query_handler
from lambda_tools.report_generator import lambda_handler as report_handler

@pytest.mark.slow
@pytest.mark.performance
class TestBulkOperations:
    """Performance tests for bulk operations and report generation."""
    
    def test_bulk_report_generation(
        self,
        integration_test_setup,
        performance_monitor,
        memory_profiler,
        load_test_articles,
        correlation_id,
        lambda_context
    ):
        """Test bulk report generation performance."""
        
        # Set up large dataset
        import boto3
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        # Load all test articles
        batch_size = 25
        for i in range(0, len(load_test_articles), batch_size):
            batch = load_test_articles[i:i + batch_size]
            with articles_table.batch_writer() as writer:
                for article in batch:
                    writer.put_item(Item=article)
        
        performance_monitor.start_monitoring()
        memory_profiler.start_profiling()
        
        # Test large report generation
        report_event = {
            "report_type": "keyword_analysis",
            "filters": {
                "date_range": {
                    "start": "2024-01-01",
                    "end": "2024-12-31"
                },
                "keywords": ["AWS", "Microsoft", "vulnerability"],
                "export_format": "xlsx"
            },
            "correlation_id": correlation_id
        }
        
        with patch('boto3.client') as mock_boto_client:
            # Mock S3 for report storage
            mock_s3 = MagicMock()
            mock_s3.put_object.return_value = {"ETag": "test-etag"}
            mock_s3.generate_presigned_url.return_value = "https://example.com/report.xlsx"
            
            # Mock OpenSearch for data retrieval
            mock_opensearch = MagicMock()
            mock_opensearch.search.return_value = {
                "hits": {
                    "hits": [
                        {
                            "_source": article,
                            "_score": 0.9
                        }
                        for article in load_test_articles[:500]  # Return 500 articles
                    ]
                }
            }
            
            def mock_client(service_name):
                if service_name == "s3":
                    return mock_s3
                elif service_name == "opensearch":
                    return mock_opensearch
                else:
                    return MagicMock()
            
            mock_boto_client.side_effect = mock_client
            
            start_time = time.time()
            result = report_handler(report_event, lambda_context)
            end_time = time.time()
            
            processing_time = (end_time - start_time) * 1000
            performance_monitor.record_response_time(processing_time)
            
            if result["statusCode"] == 200:
                performance_monitor.record_success()
            else:
                performance_monitor.record_error()
        
        performance_monitor.stop_monitoring()
        memory_stats = memory_profiler.get_memory_stats()
        perf_summary = performance_monitor.get_summary()
        
        # Verify report generation performance
        assert result["statusCode"] == 200
        
        body = json.loads(result["body"])
        assert "export_url" in body
        assert "total_records" in body
        assert body["total_records"] == 500
        
        # Performance requirements for bulk operations
        assert processing_time < 60000  # Under 1 minute for 500 records
        assert memory_stats["peak_memory_mb"] < 350  # Reasonable memory usage
        assert perf_summary["success_rate"] == 1.0
        
        # Efficiency metrics
        records_per_second = 500 / (processing_time / 1000)
        assert records_per_second > 10  # At least 10 records per second
    
    def test_concurrent_report_generation(
        self,
        integration_test_setup,
        performance_monitor,
        concurrent_executor,
        load_test_articles,
        correlation_id,
        lambda_context
    ):
        """Test concurrent report generation requests."""
        
        # Set up test data
        import boto3
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        with articles_table.batch_writer() as batch:
            for article in load_test_articles[:200]:
                batch.put_item(Item=article)
        
        performance_monitor.start_monitoring()
        
        def generate_report(report_id: int) -> dict:
            """Generate a report."""
            report_types = ["keyword_analysis", "feed_summary", "threat_intelligence", "vulnerability_report"]
            report_type = report_types[report_id % len(report_types)]
            
            report_event = {
                "report_type": report_type,
                "filters": {
                    "keywords": ["AWS", "Microsoft"][report_id % 2:report_id % 2 + 1],
                    "export_format": "xlsx" if report_id % 2 == 0 else "json"
                },
                "correlation_id": f"{correlation_id}-report-{report_id}"
            }
            
            with patch('boto3.client') as mock_boto_client:
                mock_s3 = MagicMock()
                mock_s3.put_object.return_value = {"ETag": f"etag-{report_id}"}
                mock_s3.generate_presigned_url.return_value = f"https://example.com/report-{report_id}.xlsx"
                
                mock_opensearch = MagicMock()
                mock_opensearch.search.return_value = {
                    "hits": {
                        "hits": [
                            {"_source": article, "_score": 0.9}
                            for article in load_test_articles[report_id*10:(report_id+1)*10]
                        ]
                    }
                }
                
                def mock_client(service_name):
                    if service_name == "s3":
                        return mock_s3
                    elif service_name == "opensearch":
                        return mock_opensearch
                    else:
                        return MagicMock()
                
                mock_boto_client.side_effect = mock_client
                
                start_time = time.time()
                result = report_handler(report_event, lambda_context)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000
                performance_monitor.record_response_time(response_time)
                
                if result["statusCode"] == 200:
                    performance_monitor.record_success()
                else:
                    performance_monitor.record_error()
                
                return result
        
        # Generate concurrent reports
        concurrent_reports = 8
        report_args = [(i,) for i in range(concurrent_reports)]
        
        execution_result = concurrent_executor.execute_concurrent(
            generate_report,
            report_args,
            max_workers=concurrent_reports
        )
        
        performance_monitor.stop_monitoring()
        perf_summary = performance_monitor.get_summary()
        
        # Verify concurrent report generation
        assert execution_result["error_count"] == 0
        assert execution_result["success_count"] == concurrent_reports
        
        # Performance requirements
        assert perf_summary["success_rate"] == 1.0
        assert perf_summary["avg_response_time_ms"] < 30000  # Under 30 seconds
        assert perf_summary["max_response_time_ms"] < 60000  # Max 1 minute
        
        # Concurrent efficiency
        total_time = perf_summary["duration_seconds"]
        reports_per_second = concurrent_reports / total_time
        assert reports_per_second > 0.2  # At least 0.2 reports per second
    
    def test_large_dataset_export(
        self,
        integration_test_setup,
        performance_monitor,
        memory_profiler,
        load_test_articles,
        correlation_id,
        lambda_context
    ):
        """Test export performance with large datasets."""
        
        # Set up very large dataset
        import boto3
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        # Load all test articles (1000 articles)
        batch_size = 25
        for i in range(0, len(load_test_articles), batch_size):
            batch = load_test_articles[i:i + batch_size]
            with articles_table.batch_writer() as writer:
                for article in batch:
                    writer.put_item(Item=article)
        
        performance_monitor.start_monitoring()
        memory_profiler.start_profiling()
        
        # Test large export
        export_event = {
            "report_type": "full_export",
            "filters": {
                "state": ["PUBLISHED", "REVIEW"],
                "export_format": "xlsx"
            },
            "include_all_fields": True,
            "correlation_id": correlation_id
        }
        
        with patch('boto3.client') as mock_boto_client:
            mock_s3 = MagicMock()
            mock_s3.put_object.return_value = {"ETag": "large-export-etag"}
            mock_s3.generate_presigned_url.return_value = "https://example.com/large-export.xlsx"
            
            mock_opensearch = MagicMock()
            
            # Simulate paginated search results
            def mock_search(*args, **kwargs):
                # Simulate processing time for large dataset
                time.sleep(0.1)
                return {
                    "hits": {
                        "hits": [
                            {"_source": article, "_score": 0.9}
                            for article in load_test_articles  # All 1000 articles
                        ]
                    }
                }
            
            mock_opensearch.search.side_effect = mock_search
            
            def mock_client(service_name):
                if service_name == "s3":
                    return mock_s3
                elif service_name == "opensearch":
                    return mock_opensearch
                else:
                    return MagicMock()
            
            mock_boto_client.side_effect = mock_client
            
            start_time = time.time()
            result = report_handler(export_event, lambda_context)
            end_time = time.time()
            
            processing_time = (end_time - start_time) * 1000
            performance_monitor.record_response_time(processing_time)
            
            if result["statusCode"] == 200:
                performance_monitor.record_success()
            else:
                performance_monitor.record_error()
        
        performance_monitor.stop_monitoring()
        memory_stats = memory_profiler.get_memory_stats()
        perf_summary = performance_monitor.get_summary()
        
        # Verify large export performance
        assert result["statusCode"] == 200
        
        body = json.loads(result["body"])
        assert "export_url" in body
        assert body["total_records"] == 1000
        
        # Performance requirements for large exports
        assert processing_time < 120000  # Under 2 minutes for 1000 records
        assert memory_stats["peak_memory_mb"] < 400  # Within Lambda limits
        assert perf_summary["success_rate"] == 1.0
        
        # Export efficiency
        records_per_second = 1000 / (processing_time / 1000)
        assert records_per_second > 15  # At least 15 records per second
    
    def test_batch_processing_performance(
        self,
        integration_test_setup,
        performance_monitor,
        memory_profiler,
        load_test_articles,
        correlation_id,
        lambda_context
    ):
        """Test batch processing performance for bulk operations."""
        
        from lambda_tools.storage_tool import lambda_handler as storage_handler
        
        performance_monitor.start_monitoring()
        memory_profiler.start_profiling()
        
        # Test batch storage of articles
        batch_sizes = [10, 25, 50, 100]
        
        for batch_size in batch_sizes:
            batch_articles = load_test_articles[:batch_size]
            
            batch_event = {
                "operation": "batch_store",
                "articles": batch_articles,
                "correlation_id": f"{correlation_id}-batch-{batch_size}"
            }
            
            start_time = time.time()
            result = storage_handler(batch_event, lambda_context)
            end_time = time.time()
            
            processing_time = (end_time - start_time) * 1000
            performance_monitor.record_response_time(processing_time)
            memory_profiler.sample_memory()
            
            if result["statusCode"] == 200:
                performance_monitor.record_success()
            else:
                performance_monitor.record_error()
            
            # Verify batch was processed
            body = json.loads(result["body"])
            assert body.get("batch_size") == batch_size
            assert body.get("processed_count") == batch_size
            
            # Performance should scale sub-linearly with batch size
            articles_per_ms = batch_size / processing_time
            assert articles_per_ms > 0.1  # At least 0.1 articles per millisecond
        
        performance_monitor.stop_monitoring()
        memory_stats = memory_profiler.get_memory_stats()
        perf_summary = performance_monitor.get_summary()
        
        # Verify batch processing efficiency
        assert perf_summary["success_rate"] == 1.0
        assert memory_stats["peak_memory_mb"] < 350
        
        # Batch processing should be more efficient than individual operations
        response_times = performance_monitor.metrics["response_times"]
        if len(response_times) >= 4:
            # Larger batches should have better per-item efficiency
            small_batch_time = response_times[0] / 10  # 10 items
            large_batch_time = response_times[-1] / 100  # 100 items
            
            efficiency_improvement = small_batch_time / large_batch_time
            assert efficiency_improvement > 2  # At least 2x more efficient
    
    def test_concurrent_bulk_operations(
        self,
        integration_test_setup,
        performance_monitor,
        concurrent_executor,
        load_test_articles,
        correlation_id,
        lambda_context
    ):
        """Test concurrent bulk operations."""
        
        from lambda_tools.storage_tool import lambda_handler as storage_handler
        
        performance_monitor.start_monitoring()
        
        def perform_bulk_operation(operation_id: int) -> dict:
            """Perform a bulk operation."""
            batch_start = operation_id * 50
            batch_end = batch_start + 50
            batch_articles = load_test_articles[batch_start:batch_end]
            
            batch_event = {
                "operation": "batch_store",
                "articles": batch_articles,
                "correlation_id": f"{correlation_id}-bulk-{operation_id}"
            }
            
            start_time = time.time()
            result = storage_handler(batch_event, lambda_context)
            end_time = time.time()
            
            processing_time = (end_time - start_time) * 1000
            performance_monitor.record_response_time(processing_time)
            
            if result["statusCode"] == 200:
                performance_monitor.record_success()
            else:
                performance_monitor.record_error()
            
            return result
        
        # Run concurrent bulk operations
        concurrent_operations = 10  # 10 concurrent batches of 50 articles each
        operation_args = [(i,) for i in range(concurrent_operations)]
        
        execution_result = concurrent_executor.execute_concurrent(
            perform_bulk_operation,
            operation_args,
            max_workers=concurrent_operations
        )
        
        performance_monitor.stop_monitoring()
        perf_summary = performance_monitor.get_summary()
        
        # Verify concurrent bulk operations
        assert execution_result["error_count"] == 0
        assert execution_result["success_count"] == concurrent_operations
        
        # Performance requirements
        assert perf_summary["success_rate"] == 1.0
        assert perf_summary["avg_response_time_ms"] < 20000  # Under 20 seconds per batch
        
        # Concurrent efficiency
        total_articles = concurrent_operations * 50  # 500 articles total
        total_time = perf_summary["duration_seconds"]
        articles_per_second = total_articles / total_time
        assert articles_per_second > 25  # At least 25 articles per second with concurrency
    
    def test_streaming_export_performance(
        self,
        integration_test_setup,
        performance_monitor,
        memory_profiler,
        load_test_articles,
        correlation_id,
        lambda_context
    ):
        """Test streaming export for very large datasets."""
        
        # Set up large dataset
        import boto3
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        # Load all test articles
        batch_size = 25
        for i in range(0, len(load_test_articles), batch_size):
            batch = load_test_articles[i:i + batch_size]
            with articles_table.batch_writer() as writer:
                for article in batch:
                    writer.put_item(Item=article)
        
        performance_monitor.start_monitoring()
        memory_profiler.start_profiling()
        
        # Test streaming export
        streaming_event = {
            "report_type": "streaming_export",
            "filters": {},  # Export all articles
            "export_format": "json",
            "streaming": True,
            "correlation_id": correlation_id
        }
        
        with patch('boto3.client') as mock_boto_client:
            mock_s3 = MagicMock()
            
            # Track S3 uploads to simulate streaming
            upload_count = 0
            def mock_put_object(*args, **kwargs):
                nonlocal upload_count
                upload_count += 1
                return {"ETag": f"stream-etag-{upload_count}"}
            
            mock_s3.put_object.side_effect = mock_put_object
            mock_s3.generate_presigned_url.return_value = "https://example.com/streaming-export.json"
            
            mock_opensearch = MagicMock()
            
            # Simulate paginated results for streaming
            def mock_search(*args, **kwargs):
                # Simulate memory-efficient streaming
                memory_profiler.sample_memory()
                time.sleep(0.05)  # Small processing delay
                
                # Return batch of results
                batch_size = 50
                return {
                    "hits": {
                        "hits": [
                            {"_source": article, "_score": 0.9}
                            for article in load_test_articles[:batch_size]
                        ]
                    }
                }
            
            mock_opensearch.search.side_effect = mock_search
            
            def mock_client(service_name):
                if service_name == "s3":
                    return mock_s3
                elif service_name == "opensearch":
                    return mock_opensearch
                else:
                    return MagicMock()
            
            mock_boto_client.side_effect = mock_client
            
            start_time = time.time()
            result = report_handler(streaming_event, lambda_context)
            end_time = time.time()
            
            processing_time = (end_time - start_time) * 1000
            performance_monitor.record_response_time(processing_time)
            
            if result["statusCode"] == 200:
                performance_monitor.record_success()
            else:
                performance_monitor.record_error()
        
        performance_monitor.stop_monitoring()
        memory_stats = memory_profiler.get_memory_stats()
        perf_summary = performance_monitor.get_summary()
        
        # Verify streaming export performance
        assert result["statusCode"] == 200
        
        body = json.loads(result["body"])
        assert "export_url" in body
        
        # Streaming should be memory-efficient
        assert memory_stats["peak_memory_mb"] < 200  # Much lower memory usage
        assert memory_stats["memory_growth_mb"] < 50  # Minimal memory growth
        
        # Should handle large datasets efficiently
        assert processing_time < 90000  # Under 1.5 minutes
        assert upload_count > 0  # Should have made streaming uploads