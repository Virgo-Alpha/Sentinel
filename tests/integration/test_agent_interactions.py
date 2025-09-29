"""
Integration tests for agent interactions and tool coordination.

Tests the interaction between different agents and their tools,
including the Ingestor Agent and Analyst Assistant Agent.
"""

import pytest
import json
import boto3
from unittest.mock import patch, MagicMock
import uuid
from typing import Dict, Any

# Import agent and tool modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from lambda_tools.agent_shim import lambda_handler as agent_shim_handler
from lambda_tools.query_kb import lambda_handler as query_kb_handler
from lambda_tools.human_escalation import lambda_handler as human_escalation_handler
from lambda_tools.publish_decision import lambda_handler as publish_decision_handler
from lambda_tools.commentary_api import lambda_handler as commentary_handler

@pytest.mark.integration
class TestAgentInteractions:
    """Integration tests for agent interactions and coordination."""
    
    def test_ingestor_agent_tool_coordination(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test Ingestor Agent coordinating multiple tools."""
        
        # Simulate Ingestor Agent workflow
        agent_event = {
            "agent_type": "ingestor",
            "workflow": "process_article",
            "article_data": sample_article_data,
            "correlation_id": correlation_id
        }
        
        with patch('boto3.client') as mock_boto_client:
            # Mock Lambda client for tool invocations
            mock_lambda = MagicMock()
            
            # Mock tool responses
            tool_responses = {
                "relevancy_evaluator": {
                    "statusCode": 200,
                    "body": json.dumps({
                        "is_relevant": True,
                        "relevancy_score": 0.85,
                        "entities": {"cves": ["CVE-2024-0001"], "vendors": ["AWS"]}
                    })
                },
                "dedup_tool": {
                    "statusCode": 200,
                    "body": json.dumps({
                        "is_duplicate": False,
                        "cluster_id": None
                    })
                },
                "guardrail_tool": {
                    "statusCode": 200,
                    "body": json.dumps({
                        "guardrail_flags": [],
                        "passed": True
                    })
                },
                "storage_tool": {
                    "statusCode": 200,
                    "body": json.dumps({
                        "stored": True,
                        "article_id": sample_article_data["article_id"]
                    })
                }
            }
            
            def mock_invoke(FunctionName, Payload, **kwargs):
                # Determine which tool is being called based on function name
                for tool_name, response in tool_responses.items():
                    if tool_name in FunctionName:
                        return {"Payload": MagicMock(read=lambda: json.dumps(response).encode())}
                
                # Default response
                return {"Payload": MagicMock(read=lambda: json.dumps({"statusCode": 200}).encode())}
            
            mock_lambda.invoke.side_effect = mock_invoke
            mock_boto_client.return_value = mock_lambda
            
            result = agent_shim_handler(agent_event, lambda_context)
        
        assert result["statusCode"] == 200
        agent_data = json.loads(result["body"])
        
        # Should have coordinated all tools successfully
        assert "tool_executions" in agent_data
        assert len(agent_data["tool_executions"]) >= 4  # All main tools
        
        # Should have final decision
        assert "final_decision" in agent_data
        assert agent_data["final_decision"]["action"] in ["AUTO_PUBLISH", "REVIEW", "DROP"]
    
    def test_analyst_assistant_query_workflow(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test Analyst Assistant Agent query and response workflow."""
        
        # First, store some test articles
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        test_articles = []
        for i in range(5):
            article = {
                **sample_article_data,
                "article_id": str(uuid.uuid4()),
                "title": f"Test Article {i} about AWS security",
                "state": "PUBLISHED"
            }
            table.put_item(Item=article)
            test_articles.append(article)
        
        # Test natural language query
        query_event = {
            "query": "Find articles about AWS security from the last week",
            "filters": {
                "state": ["PUBLISHED"],
                "keywords": ["AWS"]
            },
            "correlation_id": correlation_id
        }
        
        with patch('boto3.client') as mock_boto_client:
            # Mock OpenSearch for semantic search
            mock_opensearch = MagicMock()
            mock_opensearch.search.return_value = {
                "hits": {
                    "hits": [
                        {
                            "_source": {
                                "article_id": article["article_id"],
                                "title": article["title"],
                                "summary_short": article.get("summary_short", "")
                            },
                            "_score": 0.9
                        }
                        for article in test_articles[:3]  # Return top 3
                    ]
                }
            }
            
            query_result = query_kb_handler(query_event, lambda_context)
        
        assert query_result["statusCode"] == 200
        query_data = json.loads(query_result["body"])
        
        assert "articles" in query_data
        assert len(query_data["articles"]) == 3
        assert "total" in query_data
        
        # Should include source citations
        for article in query_data["articles"]:
            assert "title" in article
            assert "url" in article or "article_id" in article
    
    def test_human_escalation_workflow(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test human escalation and review workflow."""
        
        # Step 1: Escalate article for human review
        escalation_event = {
            "article_id": sample_article_data["article_id"],
            "escalation_reason": "Guardrail violation detected",
            "priority": "high",
            "reviewer_group": "senior_analysts",
            "correlation_id": correlation_id
        }
        
        with patch('boto3.client') as mock_boto_client:
            # Mock SES for email notifications
            mock_ses = MagicMock()
            mock_ses.send_email.return_value = {"MessageId": "test-message-id"}
            mock_boto_client.return_value = mock_ses
            
            escalation_result = human_escalation_handler(escalation_event, lambda_context)
        
        assert escalation_result["statusCode"] == 200
        escalation_data = json.loads(escalation_result["body"])
        
        assert escalation_data["escalated"] is True
        assert "notification_sent" in escalation_data
        
        # Step 2: Human makes decision
        decision_event = {
            "article_id": sample_article_data["article_id"],
            "decision": "approve",
            "reviewer": "test_analyst",
            "reason": "Article meets publication criteria",
            "correlation_id": correlation_id
        }
        
        decision_result = publish_decision_handler(decision_event, lambda_context)
        
        assert decision_result["statusCode"] == 200
        decision_data = json.loads(decision_result["body"])
        
        assert decision_data["decision_recorded"] is True
        assert decision_data["next_action"] == "publish"
        
        # Verify decision was stored
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        response = table.get_item(Key={"article_id": sample_article_data["article_id"]})
        if "Item" in response:
            article = response["Item"]
            assert article.get("review_decision") == "approve"
            assert article.get("reviewer") == "test_analyst"
    
    def test_commentary_system_workflow(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test commentary and discussion workflow."""
        
        # Add initial comment
        comment_event = {
            "action": "create",
            "article_id": sample_article_data["article_id"],
            "content": "This article needs additional verification of the CVE details.",
            "author": "analyst_1",
            "correlation_id": correlation_id
        }
        
        comment_result = commentary_handler(comment_event, lambda_context)
        
        assert comment_result["statusCode"] == 200
        comment_data = json.loads(comment_result["body"])
        
        assert comment_data["comment_created"] is True
        comment_id = comment_data["comment_id"]
        
        # Add reply to comment
        reply_event = {
            "action": "create",
            "article_id": sample_article_data["article_id"],
            "content": "I've verified the CVE details with the NVD database.",
            "author": "analyst_2",
            "parent_id": comment_id,
            "correlation_id": correlation_id
        }
        
        reply_result = commentary_handler(reply_event, lambda_context)
        
        assert reply_result["statusCode"] == 200
        reply_data = json.loads(reply_result["body"])
        
        assert reply_data["comment_created"] is True
        
        # Retrieve all comments for article
        get_comments_event = {
            "action": "get",
            "article_id": sample_article_data["article_id"],
            "correlation_id": correlation_id
        }
        
        get_result = commentary_handler(get_comments_event, lambda_context)
        
        assert get_result["statusCode"] == 200
        get_data = json.loads(get_result["body"])
        
        assert "comments" in get_data
        assert len(get_data["comments"]) >= 2  # Original comment and reply
        
        # Verify threading structure
        root_comments = [c for c in get_data["comments"] if not c.get("parent_id")]
        assert len(root_comments) >= 1
        
        replies = [c for c in get_data["comments"] if c.get("parent_id")]
        assert len(replies) >= 1
    
    def test_agent_error_recovery(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test agent error handling and recovery mechanisms."""
        
        # Test agent shim with tool failure
        agent_event = {
            "agent_type": "ingestor",
            "workflow": "process_article",
            "article_data": sample_article_data,
            "correlation_id": correlation_id
        }
        
        with patch('boto3.client') as mock_boto_client:
            mock_lambda = MagicMock()
            
            # Simulate tool failure
            def mock_invoke_with_failure(FunctionName, Payload, **kwargs):
                if "relevancy_evaluator" in FunctionName:
                    # First tool fails
                    return {
                        "Payload": MagicMock(read=lambda: json.dumps({
                            "statusCode": 500,
                            "body": json.dumps({"error": "Bedrock service unavailable"})
                        }).encode())
                    }
                else:
                    # Other tools succeed
                    return {
                        "Payload": MagicMock(read=lambda: json.dumps({
                            "statusCode": 200,
                            "body": json.dumps({"success": True})
                        }).encode())
                    }
            
            mock_lambda.invoke.side_effect = mock_invoke_with_failure
            mock_boto_client.return_value = mock_lambda
            
            result = agent_shim_handler(agent_event, lambda_context)
        
        # Agent should handle tool failure gracefully
        assert result["statusCode"] in [200, 206]  # Partial success acceptable
        agent_data = json.loads(result["body"])
        
        assert "errors" in agent_data
        assert len(agent_data["errors"]) > 0
        
        # Should have fallback decision
        assert "fallback_decision" in agent_data
    
    def test_agent_memory_and_context(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test agent memory and context management."""
        
        # Store some context in memory table
        dynamodb = boto3.resource('dynamodb')
        memory_table = dynamodb.Table(os.environ["MEMORY_TABLE_NAME"])
        
        memory_items = [
            {
                "memory_id": f"context-{correlation_id}-1",
                "memory_type": "agent_context",
                "content": {
                    "agent_type": "ingestor",
                    "previous_decisions": ["AUTO_PUBLISH", "REVIEW"],
                    "processing_stats": {"articles_processed": 10, "avg_relevancy": 0.75}
                },
                "created_at": "2024-01-01T12:00:00Z",
                "correlation_id": correlation_id
            },
            {
                "memory_id": f"duplicate-{correlation_id}-1",
                "memory_type": "duplicate_rationale",
                "content": {
                    "article_id": sample_article_data["article_id"],
                    "duplicate_reasoning": "Similar title and content detected",
                    "confidence": 0.95
                },
                "created_at": "2024-01-01T12:00:00Z",
                "correlation_id": correlation_id
            }
        ]
        
        for item in memory_items:
            memory_table.put_item(Item=item)
        
        # Test agent using memory context
        agent_event = {
            "agent_type": "ingestor",
            "workflow": "process_article_with_context",
            "article_data": sample_article_data,
            "use_memory": True,
            "correlation_id": correlation_id
        }
        
        with patch('boto3.client') as mock_boto_client:
            mock_lambda = MagicMock()
            mock_lambda.invoke.return_value = {
                "Payload": MagicMock(read=lambda: json.dumps({
                    "statusCode": 200,
                    "body": json.dumps({"success": True, "used_context": True})
                }).encode())
            }
            mock_boto_client.return_value = mock_lambda
            
            result = agent_shim_handler(agent_event, lambda_context)
        
        assert result["statusCode"] == 200
        agent_data = json.loads(result["body"])
        
        # Should indicate context was used
        assert agent_data.get("context_used") is True
    
    def test_cross_agent_communication(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test communication between Ingestor and Analyst Assistant agents."""
        
        # Ingestor Agent processes article and creates memory
        ingestor_event = {
            "agent_type": "ingestor",
            "workflow": "process_and_share",
            "article_data": sample_article_data,
            "correlation_id": correlation_id
        }
        
        with patch('boto3.client') as mock_boto_client:
            mock_lambda = MagicMock()
            mock_lambda.invoke.return_value = {
                "Payload": MagicMock(read=lambda: json.dumps({
                    "statusCode": 200,
                    "body": json.dumps({
                        "processed": True,
                        "shared_context": {
                            "article_id": sample_article_data["article_id"],
                            "processing_insights": "High relevancy, no duplicates found"
                        }
                    })
                }).encode())
            }
            mock_boto_client.return_value = mock_lambda
            
            ingestor_result = agent_shim_handler(ingestor_event, lambda_context)
        
        assert ingestor_result["statusCode"] == 200
        
        # Analyst Assistant queries for insights about the article
        query_event = {
            "query": f"What insights do we have about article {sample_article_data['article_id']}?",
            "include_agent_memory": True,
            "correlation_id": correlation_id
        }
        
        query_result = query_kb_handler(query_event, lambda_context)
        
        assert query_result["statusCode"] == 200
        query_data = json.loads(query_result["body"])
        
        # Should include insights from Ingestor Agent
        assert "agent_insights" in query_data or "context" in query_data
    
    @pytest.mark.slow
    def test_agent_performance_under_load(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test agent performance under high load conditions."""
        
        import threading
        import time
        
        results = []
        errors = []
        
        def process_with_agent(article_id):
            try:
                agent_event = {
                    "agent_type": "ingestor",
                    "workflow": "process_article",
                    "article_data": {
                        **sample_article_data,
                        "article_id": article_id
                    },
                    "correlation_id": f"{correlation_id}-{article_id}"
                }
                
                with patch('boto3.client') as mock_boto_client:
                    mock_lambda = MagicMock()
                    mock_lambda.invoke.return_value = {
                        "Payload": MagicMock(read=lambda: json.dumps({
                            "statusCode": 200,
                            "body": json.dumps({"processed": True})
                        }).encode())
                    }
                    mock_boto_client.return_value = mock_lambda
                    
                    result = agent_shim_handler(agent_event, lambda_context)
                    results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        # Create 20 concurrent agent executions
        threads = []
        for i in range(20):
            article_id = f"load-test-article-{i}"
            thread = threading.Thread(target=process_with_agent, args=(article_id,))
            threads.append(thread)
        
        start_time = time.time()
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        processing_time = time.time() - start_time
        
        # All should succeed
        assert len(errors) == 0
        assert len(results) == 20
        
        # Should handle load efficiently
        assert processing_time < 30  # Complete within 30 seconds
        
        # All results should be successful
        for result in results:
            assert result["statusCode"] == 200