"""
Integration tests for the feed ingestion pipeline.

Tests the complete end-to-end flow from RSS feed parsing through
to article storage and processing.
"""

import pytest
import json
import boto3
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import uuid
from typing import Dict, Any

# Import the Lambda functions to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from lambda_tools.feed_parser import lambda_handler as feed_parser_handler
from lambda_tools.relevancy_evaluator import lambda_handler as relevancy_handler
from lambda_tools.dedup_tool import lambda_handler as dedup_handler
from lambda_tools.guardrail_tool import lambda_handler as guardrail_handler
from lambda_tools.storage_tool import lambda_handler as storage_handler

@pytest.mark.integration
class TestFeedIngestionPipeline:
    """Integration tests for the complete feed ingestion pipeline."""
    
    def test_complete_ingestion_pipeline(
        self,
        integration_test_setup,
        sample_rss_feed_data,
        sample_keyword_config,
        correlation_id,
        lambda_context
    ):
        """Test the complete feed ingestion pipeline from RSS to storage."""
        
        # Step 1: Feed Parser
        feed_event = {
            "feed_id": "test-feed",
            "feed_url": sample_rss_feed_data["feed_url"],
            "correlation_id": correlation_id
        }
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = sample_rss_feed_data["feed_content"]
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            feed_result = feed_parser_handler(feed_event, lambda_context)
        
        assert feed_result["statusCode"] == 200
        parsed_data = json.loads(feed_result["body"])
        assert "articles" in parsed_data
        assert len(parsed_data["articles"]) == 2
        
        # Extract first article for pipeline testing
        article = parsed_data["articles"][0]
        
        # Step 2: Relevancy Evaluator
        relevancy_event = {
            "article_id": article["article_id"],
            "content": article["content"],
            "target_keywords": sample_keyword_config["cloud_platforms"],
            "correlation_id": correlation_id
        }
        
        with patch('boto3.client') as mock_boto_client:
            # Mock Bedrock client for LLM calls
            mock_bedrock = MagicMock()
            mock_bedrock.invoke_model.return_value = {
                "body": MagicMock(read=lambda: json.dumps({
                    "completion": json.dumps({
                        "is_relevant": True,
                        "relevancy_score": 0.85,
                        "entities": {
                            "cves": ["CVE-2024-0001"],
                            "vendors": ["AWS"],
                            "products": ["Lambda"]
                        },
                        "rationale": "Article discusses AWS Lambda vulnerability"
                    })
                }).encode())
            }
            mock_boto_client.return_value = mock_bedrock
            
            relevancy_result = relevancy_handler(relevancy_event, lambda_context)
        
        assert relevancy_result["statusCode"] == 200
        relevancy_data = json.loads(relevancy_result["body"])
        assert relevancy_data["is_relevant"] is True
        assert relevancy_data["relevancy_score"] == 0.85
        
        # Step 3: Deduplication Tool
        dedup_event = {
            "article_id": article["article_id"],
            "title": article["title"],
            "content": article["content"],
            "correlation_id": correlation_id
        }
        
        with patch('boto3.resource') as mock_boto_resource:
            # Mock OpenSearch for similarity search
            mock_opensearch = MagicMock()
            mock_opensearch.search.return_value = {
                "hits": {
                    "hits": []  # No duplicates found
                }
            }
            
            dedup_result = dedup_handler(dedup_event, lambda_context)
        
        assert dedup_result["statusCode"] == 200
        dedup_data = json.loads(dedup_result["body"])
        assert dedup_data["is_duplicate"] is False
        
        # Step 4: Guardrail Tool
        guardrail_event = {
            "article_id": article["article_id"],
            "content": article["content"],
            "entities": relevancy_data["entities"],
            "correlation_id": correlation_id
        }
        
        guardrail_result = guardrail_handler(guardrail_event, lambda_context)
        
        assert guardrail_result["statusCode"] == 200
        guardrail_data = json.loads(guardrail_result["body"])
        assert len(guardrail_data["guardrail_flags"]) == 0  # No violations
        
        # Step 5: Storage Tool
        storage_event = {
            "article_id": article["article_id"],
            "article_data": {
                **article,
                "relevancy_score": relevancy_data["relevancy_score"],
                "entities": relevancy_data["entities"],
                "is_duplicate": dedup_data["is_duplicate"],
                "guardrail_flags": guardrail_data["guardrail_flags"],
                "state": "PROCESSED"
            },
            "correlation_id": correlation_id
        }
        
        storage_result = storage_handler(storage_event, lambda_context)
        
        assert storage_result["statusCode"] == 200
        storage_data = json.loads(storage_result["body"])
        assert storage_data["stored"] is True
        
        # Verify article was stored in DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        response = table.get_item(Key={"article_id": article["article_id"]})
        assert "Item" in response
        stored_article = response["Item"]
        assert stored_article["state"] == "PROCESSED"
        assert stored_article["relevancy_score"] == 0.85
    
    def test_pipeline_with_duplicate_detection(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test pipeline behavior when duplicates are detected."""
        
        # First, store an existing article
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        existing_article = {
            **sample_article_data,
            "article_id": str(uuid.uuid4()),
            "state": "PUBLISHED"
        }
        table.put_item(Item=existing_article)
        
        # Now test deduplication with similar article
        dedup_event = {
            "article_id": str(uuid.uuid4()),
            "title": sample_article_data["title"],  # Same title
            "content": "Similar content about AWS Lambda vulnerability",
            "correlation_id": correlation_id
        }
        
        with patch('boto3.resource') as mock_boto_resource:
            # Mock OpenSearch to return the existing article as similar
            mock_opensearch = MagicMock()
            mock_opensearch.search.return_value = {
                "hits": {
                    "hits": [
                        {
                            "_source": {
                                "article_id": existing_article["article_id"],
                                "title": existing_article["title"]
                            },
                            "_score": 0.95  # High similarity
                        }
                    ]
                }
            }
            
            dedup_result = dedup_handler(dedup_event, lambda_context)
        
        assert dedup_result["statusCode"] == 200
        dedup_data = json.loads(dedup_result["body"])
        assert dedup_data["is_duplicate"] is True
        assert dedup_data["duplicate_of"] == existing_article["article_id"]
    
    def test_pipeline_with_guardrail_violations(
        self,
        integration_test_setup,
        correlation_id,
        lambda_context
    ):
        """Test pipeline behavior when guardrail violations are detected."""
        
        # Create article with potential PII and sensitive content
        guardrail_event = {
            "article_id": str(uuid.uuid4()),
            "content": "Contact John Doe at john.doe@example.com or call 555-123-4567 for more information about this classified security breach.",
            "entities": {
                "cves": ["CVE-INVALID-FORMAT"],  # Invalid CVE format
                "vendors": ["AWS"],
                "products": ["Lambda"]
            },
            "correlation_id": correlation_id
        }
        
        guardrail_result = guardrail_handler(guardrail_event, lambda_context)
        
        assert guardrail_result["statusCode"] == 200
        guardrail_data = json.loads(guardrail_result["body"])
        
        # Should detect PII and invalid CVE format
        assert len(guardrail_data["guardrail_flags"]) > 0
        flag_types = [flag["type"] for flag in guardrail_data["guardrail_flags"]]
        assert "PII_DETECTED" in flag_types
        assert "INVALID_CVE_FORMAT" in flag_types
    
    def test_pipeline_error_handling(
        self,
        integration_test_setup,
        correlation_id,
        lambda_context
    ):
        """Test pipeline error handling and recovery."""
        
        # Test feed parser with invalid URL
        feed_event = {
            "feed_id": "test-feed",
            "feed_url": "invalid-url",
            "correlation_id": correlation_id
        }
        
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            feed_result = feed_parser_handler(feed_event, lambda_context)
        
        assert feed_result["statusCode"] == 500
        error_data = json.loads(feed_result["body"])
        assert "error" in error_data
        
        # Test relevancy evaluator with Bedrock failure
        relevancy_event = {
            "article_id": str(uuid.uuid4()),
            "content": "Test content",
            "target_keywords": ["AWS"],
            "correlation_id": correlation_id
        }
        
        with patch('boto3.client') as mock_boto_client:
            mock_bedrock = MagicMock()
            mock_bedrock.invoke_model.side_effect = Exception("Bedrock error")
            mock_boto_client.return_value = mock_bedrock
            
            relevancy_result = relevancy_handler(relevancy_event, lambda_context)
        
        assert relevancy_result["statusCode"] == 500
        error_data = json.loads(relevancy_result["body"])
        assert "error" in error_data
    
    def test_pipeline_correlation_id_propagation(
        self,
        integration_test_setup,
        sample_rss_feed_data,
        correlation_id,
        lambda_context
    ):
        """Test that correlation IDs are properly propagated through the pipeline."""
        
        # Test feed parser correlation ID handling
        feed_event = {
            "feed_id": "test-feed",
            "feed_url": sample_rss_feed_data["feed_url"],
            "correlation_id": correlation_id
        }
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = sample_rss_feed_data["feed_content"]
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            feed_result = feed_parser_handler(feed_event, lambda_context)
        
        # Check that correlation ID is in response headers
        assert "headers" in feed_result
        assert "X-Correlation-ID" in feed_result["headers"]
        assert feed_result["headers"]["X-Correlation-ID"] == correlation_id
        
        # Test that correlation ID is included in downstream events
        parsed_data = json.loads(feed_result["body"])
        for article in parsed_data["articles"]:
            assert "correlation_id" in article
            assert article["correlation_id"] == correlation_id
    
    def test_pipeline_performance_metrics(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test that performance metrics are properly tracked."""
        
        import time
        
        start_time = time.time()
        
        # Test storage tool with timing
        storage_event = {
            "article_id": sample_article_data["article_id"],
            "article_data": sample_article_data,
            "correlation_id": correlation_id,
            "start_time": start_time
        }
        
        storage_result = storage_handler(storage_event, lambda_context)
        
        assert storage_result["statusCode"] == 200
        storage_data = json.loads(storage_result["body"])
        
        # Should include performance metrics
        assert "processing_time_ms" in storage_data
        assert storage_data["processing_time_ms"] > 0
    
    @pytest.mark.slow
    def test_pipeline_with_large_feed(
        self,
        integration_test_setup,
        correlation_id,
        lambda_context
    ):
        """Test pipeline performance with large RSS feed."""
        
        # Generate large RSS feed with 100 articles
        large_feed_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Large Security Feed</title>
                <description>Large cybersecurity news feed for testing</description>
        """
        
        for i in range(100):
            large_feed_content += f"""
                <item>
                    <title>Security Article {i}</title>
                    <description>Description for security article {i} about AWS and cybersecurity.</description>
                    <link>https://example.com/article-{i}</link>
                    <pubDate>Mon, 01 Jan 2024 {i:02d}:00:00 GMT</pubDate>
                    <guid>article-{i}</guid>
                </item>
            """
        
        large_feed_content += """
            </channel>
        </rss>"""
        
        feed_event = {
            "feed_id": "large-test-feed",
            "feed_url": "https://example.com/large-feed.xml",
            "correlation_id": correlation_id
        }
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = large_feed_content
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            start_time = time.time()
            feed_result = feed_parser_handler(feed_event, lambda_context)
            processing_time = time.time() - start_time
        
        assert feed_result["statusCode"] == 200
        parsed_data = json.loads(feed_result["body"])
        
        # Should handle large feed efficiently
        assert len(parsed_data["articles"]) == 100
        assert processing_time < 30  # Should complete within 30 seconds
        
        # Check memory usage doesn't exceed limits
        assert "memory_usage" in parsed_data
        assert parsed_data["memory_usage"]["peak_mb"] < 400  # Within Lambda limits
    
    def test_pipeline_concurrent_processing(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test pipeline behavior under concurrent processing."""
        
        import threading
        import time
        
        results = []
        errors = []
        
        def process_article(article_id):
            try:
                storage_event = {
                    "article_id": article_id,
                    "article_data": {
                        **sample_article_data,
                        "article_id": article_id
                    },
                    "correlation_id": f"{correlation_id}-{article_id}"
                }
                
                result = storage_handler(storage_event, lambda_context)
                results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        # Create 10 concurrent threads
        threads = []
        for i in range(10):
            article_id = f"concurrent-article-{i}"
            thread = threading.Thread(target=process_article, args=(article_id,))
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        processing_time = time.time() - start_time
        
        # All should succeed
        assert len(errors) == 0
        assert len(results) == 10
        
        # Should complete within reasonable time
        assert processing_time < 10
        
        # Verify all articles were stored
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        for i in range(10):
            article_id = f"concurrent-article-{i}"
            response = table.get_item(Key={"article_id": article_id})
            assert "Item" in response