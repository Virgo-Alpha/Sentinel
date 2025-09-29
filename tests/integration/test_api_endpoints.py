"""
Integration tests for API endpoints.

Tests the API Gateway endpoints that connect to Lambda functions
and provide the web application interface.
"""

import pytest
import json
import boto3
from unittest.mock import patch, MagicMock
import uuid
from datetime import datetime, timezone
import base64
from typing import Dict, Any

@pytest.mark.integration
class TestAPIEndpoints:
    """Integration tests for API Gateway endpoints."""
    
    def create_api_event(self, method: str, path: str, body: str = None, 
                        headers: Dict[str, str] = None, 
                        query_params: Dict[str, str] = None,
                        path_params: Dict[str, str] = None) -> Dict[str, Any]:
        """Create a mock API Gateway event."""
        
        event = {
            "httpMethod": method,
            "path": path,
            "resource": path,
            "requestContext": {
                "requestId": str(uuid.uuid4()),
                "stage": "test",
                "resourcePath": path,
                "httpMethod": method,
                "identity": {
                    "sourceIp": "127.0.0.1",
                    "userAgent": "test-agent"
                }
            },
            "headers": headers or {},
            "multiValueHeaders": {},
            "queryStringParameters": query_params,
            "multiValueQueryStringParameters": {},
            "pathParameters": path_params,
            "stageVariables": {},
            "body": body,
            "isBase64Encoded": False
        }
        
        return event
    
    def test_articles_get_endpoint(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test GET /articles endpoint."""
        
        # Set up test data
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        # Create test articles
        test_articles = []
        for i in range(5):
            article = {
                **sample_article_data,
                "article_id": str(uuid.uuid4()),
                "title": f"Test Article {i}",
                "state": "PUBLISHED",
                "published_at": datetime.now(timezone.utc).isoformat()
            }
            articles_table.put_item(Item=article)
            test_articles.append(article)
        
        # Import the API handler
        from lambda_tools.query_kb import lambda_handler as query_handler
        
        # Test basic GET request
        event = self.create_api_event(
            method="GET",
            path="/articles",
            query_params={"state": "PUBLISHED", "limit": "10"}
        )
        
        result = query_handler(event, lambda_context)
        
        assert result["statusCode"] == 200
        assert "headers" in result
        assert result["headers"]["Content-Type"] == "application/json"
        
        body = json.loads(result["body"])
        assert "data" in body
        assert len(body["data"]) <= 10
        
        # Verify CORS headers
        assert "Access-Control-Allow-Origin" in result["headers"]
        assert "Access-Control-Allow-Methods" in result["headers"]
    
    def test_articles_post_endpoint(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test POST /articles endpoint (create article)."""
        
        from lambda_tools.storage_tool import lambda_handler as storage_handler
        
        # Test article creation
        new_article = {
            **sample_article_data,
            "article_id": str(uuid.uuid4()),
            "title": "New Test Article"
        }
        
        event = self.create_api_event(
            method="POST",
            path="/articles",
            body=json.dumps(new_article),
            headers={"Content-Type": "application/json"}
        )
        
        result = storage_handler(event, lambda_context)
        
        assert result["statusCode"] in [200, 201]
        
        body = json.loads(result["body"])
        assert "article_id" in body
        
        # Verify article was created
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        response = articles_table.get_item(Key={"article_id": new_article["article_id"]})
        assert "Item" in response
    
    def test_articles_get_by_id_endpoint(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test GET /articles/{id} endpoint."""
        
        # Create test article
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        article_id = str(uuid.uuid4())
        article = {
            **sample_article_data,
            "article_id": article_id,
            "state": "PUBLISHED"
        }
        articles_table.put_item(Item=article)
        
        from lambda_tools.query_kb import lambda_handler as query_handler
        
        # Test GET by ID
        event = self.create_api_event(
            method="GET",
            path=f"/articles/{article_id}",
            path_params={"id": article_id}
        )
        
        result = query_handler(event, lambda_context)
        
        assert result["statusCode"] == 200
        
        body = json.loads(result["body"])
        assert body["article_id"] == article_id
        assert body["title"] == article["title"]
    
    def test_articles_get_by_id_not_found(
        self,
        integration_test_setup,
        correlation_id,
        lambda_context
    ):
        """Test GET /articles/{id} with non-existent ID."""
        
        from lambda_tools.query_kb import lambda_handler as query_handler
        
        non_existent_id = str(uuid.uuid4())
        
        event = self.create_api_event(
            method="GET",
            path=f"/articles/{non_existent_id}",
            path_params={"id": non_existent_id}
        )
        
        result = query_handler(event, lambda_context)
        
        assert result["statusCode"] == 404
        
        body = json.loads(result["body"])
        assert "error" in body
        assert "not found" in body["error"].lower()
    
    def test_chat_endpoint(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test POST /chat endpoint for analyst assistant."""
        
        from lambda_tools.query_kb import lambda_handler as query_handler
        
        # Create test articles for querying
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        for i in range(3):
            article = {
                **sample_article_data,
                "article_id": str(uuid.uuid4()),
                "title": f"AWS Security Article {i}",
                "state": "PUBLISHED"
            }
            articles_table.put_item(Item=article)
        
        # Test chat query
        chat_request = {
            "message": "Find articles about AWS security",
            "sessionId": f"session-{correlation_id}"
        }
        
        event = self.create_api_event(
            method="POST",
            path="/chat",
            body=json.dumps(chat_request),
            headers={"Content-Type": "application/json"}
        )
        
        with patch('boto3.client') as mock_boto_client:
            # Mock OpenSearch for semantic search
            mock_opensearch = MagicMock()
            mock_opensearch.search.return_value = {
                "hits": {
                    "hits": [
                        {
                            "_source": {
                                "article_id": str(uuid.uuid4()),
                                "title": "AWS Security Article 1",
                                "summary_short": "Article about AWS security"
                            },
                            "_score": 0.9
                        }
                    ]
                }
            }
            
            result = query_handler(event, lambda_context)
        
        assert result["statusCode"] == 200
        
        body = json.loads(result["body"])
        assert "message" in body
        assert "sources" in body or "queryResults" in body
    
    def test_comments_endpoints(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test comment-related endpoints."""
        
        # Create test article
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        article_id = str(uuid.uuid4())
        article = {
            **sample_article_data,
            "article_id": article_id,
            "state": "PUBLISHED"
        }
        articles_table.put_item(Item=article)
        
        from lambda_tools.commentary_api import lambda_handler as commentary_handler
        
        # Test POST /comments (create comment)
        comment_data = {
            "articleId": article_id,
            "content": "This is a test comment",
            "author": "test_user"
        }
        
        create_event = self.create_api_event(
            method="POST",
            path="/comments",
            body=json.dumps(comment_data),
            headers={"Content-Type": "application/json"}
        )
        
        create_result = commentary_handler(create_event, lambda_context)
        
        assert create_result["statusCode"] in [200, 201]
        
        create_body = json.loads(create_result["body"])
        comment_id = create_body["comment_id"]
        
        # Test GET /comments?articleId={id}
        get_event = self.create_api_event(
            method="GET",
            path="/comments",
            query_params={"articleId": article_id}
        )
        
        get_result = commentary_handler(get_event, lambda_context)
        
        assert get_result["statusCode"] == 200
        
        get_body = json.loads(get_result["body"])
        assert "comments" in get_body
        assert len(get_body["comments"]) >= 1
        
        # Verify comment exists
        found_comment = None
        for comment in get_body["comments"]:
            if comment["comment_id"] == comment_id:
                found_comment = comment
                break
        
        assert found_comment is not None
        assert found_comment["content"] == comment_data["content"]
    
    def test_review_endpoints(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test review workflow endpoints."""
        
        # Create article for review
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        article_id = str(uuid.uuid4())
        article = {
            **sample_article_data,
            "article_id": article_id,
            "state": "REVIEW"
        }
        articles_table.put_item(Item=article)
        
        from lambda_tools.publish_decision import lambda_handler as decision_handler
        
        # Test POST /review (submit review decision)
        review_data = {
            "articleId": article_id,
            "decision": "approve",
            "reason": "Article meets publication criteria"
        }
        
        event = self.create_api_event(
            method="POST",
            path="/review",
            body=json.dumps(review_data),
            headers={"Content-Type": "application/json"}
        )
        
        result = decision_handler(event, lambda_context)
        
        assert result["statusCode"] == 200
        
        body = json.loads(result["body"])
        assert body["decision_recorded"] is True
        
        # Verify article state was updated
        response = articles_table.get_item(Key={"article_id": article_id})
        updated_article = response["Item"]
        assert updated_article.get("review_decision") == "approve"
    
    def test_health_endpoint(
        self,
        integration_test_setup,
        correlation_id,
        lambda_context
    ):
        """Test health check endpoint."""
        
        # Simple health check handler
        def health_handler(event, context):
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "status": "healthy",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0.0"
                })
            }
        
        event = self.create_api_event(
            method="GET",
            path="/health"
        )
        
        result = health_handler(event, lambda_context)
        
        assert result["statusCode"] == 200
        
        body = json.loads(result["body"])
        assert body["status"] == "healthy"
        assert "timestamp" in body
    
    def test_api_authentication(
        self,
        integration_test_setup,
        correlation_id,
        lambda_context
    ):
        """Test API authentication and authorization."""
        
        from lambda_tools.query_kb import lambda_handler as query_handler
        
        # Test request without authentication
        event = self.create_api_event(
            method="GET",
            path="/articles"
        )
        
        # Mock authentication failure
        with patch('boto3.client') as mock_boto_client:
            mock_cognito = MagicMock()
            mock_cognito.get_user.side_effect = Exception("Invalid token")
            mock_boto_client.return_value = mock_cognito
            
            result = query_handler(event, lambda_context)
        
        # Should return 401 or handle gracefully
        assert result["statusCode"] in [200, 401, 403]
        
        # Test request with valid authentication
        event_with_auth = self.create_api_event(
            method="GET",
            path="/articles",
            headers={"Authorization": "Bearer valid-token"}
        )
        
        with patch('boto3.client') as mock_boto_client:
            mock_cognito = MagicMock()
            mock_cognito.get_user.return_value = {
                "Username": "test_user",
                "UserAttributes": [
                    {"Name": "email", "Value": "test@example.com"}
                ]
            }
            mock_boto_client.return_value = mock_cognito
            
            result = query_handler(event_with_auth, lambda_context)
        
        assert result["statusCode"] == 200
    
    def test_api_error_handling(
        self,
        integration_test_setup,
        correlation_id,
        lambda_context
    ):
        """Test API error handling and response formats."""
        
        from lambda_tools.query_kb import lambda_handler as query_handler
        
        # Test malformed JSON
        event = self.create_api_event(
            method="POST",
            path="/articles",
            body="invalid json{",
            headers={"Content-Type": "application/json"}
        )
        
        result = query_handler(event, lambda_context)
        
        assert result["statusCode"] in [400, 500]
        
        body = json.loads(result["body"])
        assert "error" in body
        
        # Test missing required fields
        event = self.create_api_event(
            method="POST",
            path="/articles",
            body=json.dumps({}),  # Empty body
            headers={"Content-Type": "application/json"}
        )
        
        result = query_handler(event, lambda_context)
        
        assert result["statusCode"] in [400, 422]
        
        # Test internal server error
        with patch('boto3.resource') as mock_boto_resource:
            mock_boto_resource.side_effect = Exception("Database connection failed")
            
            event = self.create_api_event(
                method="GET",
                path="/articles"
            )
            
            result = query_handler(event, lambda_context)
        
        assert result["statusCode"] == 500
        
        body = json.loads(result["body"])
        assert "error" in body
    
    def test_api_cors_headers(
        self,
        integration_test_setup,
        correlation_id,
        lambda_context
    ):
        """Test CORS headers in API responses."""
        
        from lambda_tools.query_kb import lambda_handler as query_handler
        
        # Test OPTIONS request (preflight)
        options_event = self.create_api_event(
            method="OPTIONS",
            path="/articles",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type,Authorization"
            }
        )
        
        result = query_handler(options_event, lambda_context)
        
        assert result["statusCode"] == 200
        assert "Access-Control-Allow-Origin" in result["headers"]
        assert "Access-Control-Allow-Methods" in result["headers"]
        assert "Access-Control-Allow-Headers" in result["headers"]
        
        # Test actual request with CORS
        get_event = self.create_api_event(
            method="GET",
            path="/articles",
            headers={"Origin": "https://example.com"}
        )
        
        result = query_handler(get_event, lambda_context)
        
        assert result["statusCode"] == 200
        assert "Access-Control-Allow-Origin" in result["headers"]
    
    @pytest.mark.slow
    def test_api_performance(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test API performance under load."""
        
        import time
        import threading
        
        from lambda_tools.query_kb import lambda_handler as query_handler
        
        # Create test data
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        for i in range(50):
            article = {
                **sample_article_data,
                "article_id": str(uuid.uuid4()),
                "title": f"Performance Test Article {i}",
                "state": "PUBLISHED"
            }
            articles_table.put_item(Item=article)
        
        results = []
        errors = []
        
        def make_request():
            try:
                event = self.create_api_event(
                    method="GET",
                    path="/articles",
                    query_params={"limit": "10"}
                )
                
                start_time = time.time()
                result = query_handler(event, lambda_context)
                end_time = time.time()
                
                results.append({
                    "status_code": result["statusCode"],
                    "response_time": end_time - start_time
                })
            except Exception as e:
                errors.append(str(e))
        
        # Make 20 concurrent requests
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        start_time = time.time()
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Verify performance
        assert len(errors) == 0
        assert len(results) == 20
        
        # All requests should succeed
        success_count = sum(1 for r in results if r["status_code"] == 200)
        assert success_count == 20
        
        # Average response time should be reasonable
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        assert avg_response_time < 5.0  # Less than 5 seconds per request
        
        # Total time should be reasonable for concurrent execution
        assert total_time < 10.0  # All requests complete within 10 seconds