"""
Integration tests for error handling and recovery scenarios.

Tests system behavior under various failure conditions and
validates recovery mechanisms.
"""

import pytest
import json
import boto3
from unittest.mock import patch, MagicMock
import uuid
from datetime import datetime, timezone
import time
from typing import Dict, Any
from botocore.exceptions import ClientError

@pytest.mark.integration
class TestErrorHandling:
    """Integration tests for error handling and recovery scenarios."""
    
    def test_dynamodb_throttling_recovery(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test recovery from DynamoDB throttling errors."""
        
        from lambda_tools.storage_tool import lambda_handler as storage_handler
        
        # Mock DynamoDB throttling error
        with patch('boto3.resource') as mock_boto_resource:
            mock_table = MagicMock()
            
            # First call fails with throttling
            # Second call succeeds
            mock_table.put_item.side_effect = [
                ClientError(
                    error_response={
                        'Error': {
                            'Code': 'ProvisionedThroughputExceededException',
                            'Message': 'The level of configured provisioned throughput for the table was exceeded'
                        }
                    },
                    operation_name='PutItem'
                ),
                None  # Success on retry
            ]
            
            mock_dynamodb = MagicMock()
            mock_dynamodb.Table.return_value = mock_table
            mock_boto_resource.return_value = mock_dynamodb
            
            storage_event = {
                "article_id": sample_article_data["article_id"],
                "article_data": sample_article_data,
                "correlation_id": correlation_id
            }
            
            result = storage_handler(storage_event, lambda_context)
        
        # Should succeed after retry
        assert result["statusCode"] == 200
        
        body = json.loads(result["body"])
        assert "retry_count" in body
        assert body["retry_count"] > 0
    
    def test_s3_service_unavailable_recovery(
        self,
        integration_test_setup,
        sample_rss_feed_data,
        correlation_id,
        lambda_context
    ):
        """Test recovery from S3 service unavailable errors."""
        
        from lambda_tools.feed_parser import lambda_handler as feed_parser_handler
        
        with patch('boto3.client') as mock_boto_client:
            mock_s3 = MagicMock()
            
            # First call fails with service unavailable
            # Second call succeeds
            mock_s3.put_object.side_effect = [
                ClientError(
                    error_response={
                        'Error': {
                            'Code': 'ServiceUnavailable',
                            'Message': 'Service is temporarily unavailable'
                        }
                    },
                    operation_name='PutObject'
                ),
                {'ETag': '"test-etag"'}  # Success on retry
            ]
            
            mock_boto_client.return_value = mock_s3
            
            # Mock successful HTTP request
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.text = sample_rss_feed_data["feed_content"]
                mock_response.status_code = 200
                mock_get.return_value = mock_response
                
                feed_event = {
                    "feed_id": "test-feed",
                    "feed_url": sample_rss_feed_data["feed_url"],
                    "correlation_id": correlation_id
                }
                
                result = feed_parser_handler(feed_event, lambda_context)
        
        # Should succeed after retry
        assert result["statusCode"] == 200
        
        body = json.loads(result["body"])
        assert "s3_retry_count" in body
        assert body["s3_retry_count"] > 0
    
    def test_bedrock_rate_limiting_recovery(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test recovery from Bedrock rate limiting."""
        
        from lambda_tools.relevancy_evaluator import lambda_handler as relevancy_handler
        
        with patch('boto3.client') as mock_boto_client:
            mock_bedrock = MagicMock()
            
            # First call fails with throttling
            # Second call succeeds
            mock_bedrock.invoke_model.side_effect = [
                ClientError(
                    error_response={
                        'Error': {
                            'Code': 'ThrottlingException',
                            'Message': 'Rate exceeded'
                        }
                    },
                    operation_name='InvokeModel'
                ),
                {
                    "body": MagicMock(read=lambda: json.dumps({
                        "completion": json.dumps({
                            "is_relevant": True,
                            "relevancy_score": 0.85,
                            "entities": {"cves": [], "vendors": ["AWS"]},
                            "rationale": "Article discusses AWS security"
                        })
                    }).encode())
                }
            ]
            
            mock_boto_client.return_value = mock_bedrock
            
            relevancy_event = {
                "article_id": sample_article_data["article_id"],
                "content": "Test content about AWS security",
                "target_keywords": ["AWS"],
                "correlation_id": correlation_id
            }
            
            result = relevancy_handler(relevancy_event, lambda_context)
        
        # Should succeed after retry with backoff
        assert result["statusCode"] == 200
        
        body = json.loads(result["body"])
        assert body["is_relevant"] is True
        assert "bedrock_retry_count" in body
    
    def test_opensearch_connection_failure_recovery(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test recovery from OpenSearch connection failures."""
        
        from lambda_tools.dedup_tool import lambda_handler as dedup_handler
        
        with patch('boto3.client') as mock_boto_client:
            mock_opensearch = MagicMock()
            
            # First call fails with connection error
            # Second call succeeds
            mock_opensearch.search.side_effect = [
                Exception("Connection timeout"),
                {
                    "hits": {
                        "hits": []  # No duplicates found
                    }
                }
            ]
            
            mock_boto_client.return_value = mock_opensearch
            
            dedup_event = {
                "article_id": sample_article_data["article_id"],
                "title": sample_article_data["title"],
                "content": "Test content for deduplication",
                "correlation_id": correlation_id
            }
            
            result = dedup_handler(dedup_event, lambda_context)
        
        # Should succeed after retry or fallback to heuristic deduplication
        assert result["statusCode"] == 200
        
        body = json.loads(result["body"])
        assert "is_duplicate" in body
        assert "fallback_method" in body or "opensearch_retry_count" in body
    
    def test_lambda_timeout_handling(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test handling of Lambda function timeouts."""
        
        from lambda_tools.storage_tool import lambda_handler as storage_handler
        
        # Mock context with very short remaining time
        short_context = MagicMock()
        short_context.get_remaining_time_in_millis.return_value = 100  # 100ms left
        short_context.aws_request_id = lambda_context.aws_request_id
        
        storage_event = {
            "article_id": sample_article_data["article_id"],
            "article_data": sample_article_data,
            "correlation_id": correlation_id
        }
        
        result = storage_handler(storage_event, short_context)
        
        # Should handle timeout gracefully
        assert result["statusCode"] in [200, 202, 408]  # Success, Accepted, or Timeout
        
        body = json.loads(result["body"])
        if result["statusCode"] == 408:
            assert "timeout" in body.get("error", "").lower()
        elif result["statusCode"] == 202:
            assert "partial" in body or "queued" in body
    
    def test_memory_limit_handling(
        self,
        integration_test_setup,
        correlation_id,
        lambda_context
    ):
        """Test handling of Lambda memory limit issues."""
        
        from lambda_tools.feed_parser import lambda_handler as feed_parser_handler
        
        # Create very large RSS feed content
        large_feed_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Large Feed</title>
                <description>Very large feed for memory testing</description>
        """
        
        # Add 1000 articles with large content
        for i in range(1000):
            large_content = "A" * 10000  # 10KB per article
            large_feed_content += f"""
                <item>
                    <title>Large Article {i}</title>
                    <description>{large_content}</description>
                    <link>https://example.com/article-{i}</link>
                    <pubDate>Mon, 01 Jan 2024 {i:02d}:00:00 GMT</pubDate>
                    <guid>large-article-{i}</guid>
                </item>
            """
        
        large_feed_content += """
            </channel>
        </rss>"""
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = large_feed_content
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            feed_event = {
                "feed_id": "large-feed",
                "feed_url": "https://example.com/large-feed.xml",
                "correlation_id": correlation_id
            }
            
            result = feed_parser_handler(feed_event, lambda_context)
        
        # Should handle large content gracefully
        assert result["statusCode"] in [200, 413, 507]  # Success, Too Large, or Insufficient Storage
        
        body = json.loads(result["body"])
        if result["statusCode"] == 413:
            assert "too large" in body.get("error", "").lower()
        elif result["statusCode"] == 507:
            assert "memory" in body.get("error", "").lower()
    
    def test_network_failure_recovery(
        self,
        integration_test_setup,
        correlation_id,
        lambda_context
    ):
        """Test recovery from network failures during RSS feed fetching."""
        
        from lambda_tools.feed_parser import lambda_handler as feed_parser_handler
        
        with patch('requests.get') as mock_get:
            # First call fails with network error
            # Second call succeeds
            mock_get.side_effect = [
                Exception("Network unreachable"),
                MagicMock(
                    text='<?xml version="1.0"?><rss><channel><item><title>Test</title></item></channel></rss>',
                    status_code=200
                )
            ]
            
            feed_event = {
                "feed_id": "test-feed",
                "feed_url": "https://example.com/feed.xml",
                "correlation_id": correlation_id
            }
            
            result = feed_parser_handler(feed_event, lambda_context)
        
        # Should succeed after retry
        assert result["statusCode"] == 200
        
        body = json.loads(result["body"])
        assert "network_retry_count" in body
        assert body["network_retry_count"] > 0
    
    def test_malformed_data_handling(
        self,
        integration_test_setup,
        correlation_id,
        lambda_context
    ):
        """Test handling of malformed or corrupted data."""
        
        from lambda_tools.feed_parser import lambda_handler as feed_parser_handler
        
        # Test with malformed RSS
        malformed_rss = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Malformed Feed</title>
                <item>
                    <title>Article 1</title>
                    <!-- Missing closing tag for item -->
                <item>
                    <title>Article 2</title>
                </item>
            </channel>
        <!-- Missing closing rss tag -->"""
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = malformed_rss
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            feed_event = {
                "feed_id": "malformed-feed",
                "feed_url": "https://example.com/malformed.xml",
                "correlation_id": correlation_id
            }
            
            result = feed_parser_handler(feed_event, lambda_context)
        
        # Should handle malformed data gracefully
        assert result["statusCode"] in [200, 400, 422]
        
        body = json.loads(result["body"])
        if result["statusCode"] != 200:
            assert "malformed" in body.get("error", "").lower() or "invalid" in body.get("error", "").lower()
        else:
            # If successful, should have parsed what it could
            assert "articles" in body
            assert "parsing_warnings" in body
    
    def test_concurrent_access_conflicts(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test handling of concurrent access conflicts."""
        
        import threading
        import time
        
        from lambda_tools.storage_tool import lambda_handler as storage_handler
        
        article_id = str(uuid.uuid4())
        results = []
        errors = []
        
        def update_article(version):
            try:
                storage_event = {
                    "article_id": article_id,
                    "article_data": {
                        **sample_article_data,
                        "article_id": article_id,
                        "version": version,
                        "updated_by": f"thread-{version}"
                    },
                    "correlation_id": f"{correlation_id}-{version}"
                }
                
                result = storage_handler(storage_event, lambda_context)
                results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        # Create 5 concurrent updates
        threads = []
        for i in range(5):
            thread = threading.Thread(target=update_article, args=(i,))
            threads.append(thread)
        
        # Start all threads simultaneously
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Should handle concurrent access gracefully
        assert len(errors) == 0
        assert len(results) == 5
        
        # At least some should succeed
        success_count = sum(1 for r in results if r["statusCode"] == 200)
        assert success_count >= 1
        
        # Check for conflict handling
        conflict_count = sum(1 for r in results if r["statusCode"] == 409)
        if conflict_count > 0:
            # Conflicts were detected and handled
            assert success_count + conflict_count == 5
    
    def test_dead_letter_queue_processing(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test dead letter queue processing for failed messages."""
        
        from lambda_tools.storage_tool import lambda_handler as storage_handler
        
        # Simulate message that consistently fails
        failing_event = {
            "article_id": "invalid-id-format",  # Invalid format
            "article_data": {
                "invalid": "data structure"  # Missing required fields
            },
            "correlation_id": correlation_id,
            "retry_count": 3  # Already retried
        }
        
        result = storage_handler(failing_event, lambda_context)
        
        # Should handle gracefully and route to DLQ
        assert result["statusCode"] in [200, 400, 500]
        
        body = json.loads(result["body"])
        if result["statusCode"] != 200:
            assert "dlq" in body or "dead_letter" in body or "failed" in body
    
    def test_circuit_breaker_pattern(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test circuit breaker pattern for external service failures."""
        
        from lambda_tools.relevancy_evaluator import lambda_handler as relevancy_handler
        
        # Simulate multiple consecutive failures to trigger circuit breaker
        with patch('boto3.client') as mock_boto_client:
            mock_bedrock = MagicMock()
            
            # All calls fail to trigger circuit breaker
            mock_bedrock.invoke_model.side_effect = Exception("Service unavailable")
            mock_boto_client.return_value = mock_bedrock
            
            results = []
            
            # Make multiple requests that should trigger circuit breaker
            for i in range(5):
                relevancy_event = {
                    "article_id": f"{sample_article_data['article_id']}-{i}",
                    "content": f"Test content {i}",
                    "target_keywords": ["AWS"],
                    "correlation_id": f"{correlation_id}-{i}"
                }
                
                result = relevancy_handler(relevancy_event, lambda_context)
                results.append(result)
        
        # Later requests should fail fast due to circuit breaker
        assert len(results) == 5
        
        # Check if circuit breaker pattern is implemented
        response_times = []
        for result in results:
            body = json.loads(result["body"])
            if "response_time_ms" in body:
                response_times.append(body["response_time_ms"])
        
        # Later requests should be faster (circuit breaker open)
        if len(response_times) >= 3:
            assert response_times[-1] < response_times[0]  # Faster response when circuit is open
    
    def test_graceful_degradation(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test graceful degradation when optional services fail."""
        
        from lambda_tools.dedup_tool import lambda_handler as dedup_handler
        
        # Simulate OpenSearch failure, should fall back to heuristic deduplication
        with patch('boto3.client') as mock_boto_client:
            mock_opensearch = MagicMock()
            mock_opensearch.search.side_effect = Exception("OpenSearch unavailable")
            mock_boto_client.return_value = mock_opensearch
            
            dedup_event = {
                "article_id": sample_article_data["article_id"],
                "title": sample_article_data["title"],
                "content": "Test content for deduplication",
                "correlation_id": correlation_id
            }
            
            result = dedup_handler(dedup_event, lambda_context)
        
        # Should succeed with fallback method
        assert result["statusCode"] == 200
        
        body = json.loads(result["body"])
        assert "is_duplicate" in body
        assert body.get("method") == "heuristic" or "fallback" in body
        assert body.get("degraded_mode") is True
    
    @pytest.mark.slow
    def test_system_recovery_after_outage(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test system recovery after simulated outage."""
        
        from lambda_tools.storage_tool import lambda_handler as storage_handler
        
        # Phase 1: Simulate outage (all requests fail)
        outage_results = []
        
        with patch('boto3.resource') as mock_boto_resource:
            mock_boto_resource.side_effect = Exception("Service outage")
            
            for i in range(3):
                storage_event = {
                    "article_id": f"outage-test-{i}",
                    "article_data": {
                        **sample_article_data,
                        "article_id": f"outage-test-{i}"
                    },
                    "correlation_id": f"{correlation_id}-outage-{i}"
                }
                
                result = storage_handler(storage_event, lambda_context)
                outage_results.append(result)
        
        # All should fail during outage
        for result in outage_results:
            assert result["statusCode"] == 500
        
        # Phase 2: Service recovery (requests succeed)
        recovery_results = []
        
        # Normal operation (no mocking = use real mocked AWS services)
        for i in range(3):
            storage_event = {
                "article_id": f"recovery-test-{i}",
                "article_data": {
                    **sample_article_data,
                    "article_id": f"recovery-test-{i}"
                },
                "correlation_id": f"{correlation_id}-recovery-{i}"
            }
            
            result = storage_handler(storage_event, lambda_context)
            recovery_results.append(result)
        
        # All should succeed after recovery
        for result in recovery_results:
            assert result["statusCode"] == 200
        
        # Verify data consistency after recovery
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        for i in range(3):
            response = articles_table.get_item(Key={"article_id": f"recovery-test-{i}"})
            assert "Item" in response