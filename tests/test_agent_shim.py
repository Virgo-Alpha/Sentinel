"""
Unit tests for the Agent Shim Lambda function.

Tests both direct Lambda orchestration and Bedrock AgentCore integration modes.
"""

import json
import os
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Import the module under test
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'lambda_tools'))

from agent_shim import (
    lambda_handler,
    DirectLambdaOrchestrator,
    BedrockAgentCoreOrchestrator,
    AgentShimError
)


class TestDirectLambdaOrchestrator:
    """Test cases for direct Lambda orchestration."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create a DirectLambdaOrchestrator instance for testing."""
        return DirectLambdaOrchestrator()
    
    @pytest.fixture
    def sample_event(self):
        """Sample event for testing."""
        return {
            'feed_config': {
                'feed_id': 'test-feed',
                'feed_url': 'https://example.com/feed.xml',
                'target_keywords': ['AWS', 'Azure', 'security'],
                'notification_recipients': ['test@example.com']
            },
            'since': '2024-01-01T00:00:00Z',
            'workflow_id': 'test-workflow-123'
        }
    
    @pytest.fixture
    def mock_lambda_responses(self):
        """Mock responses for Lambda tool invocations."""
        return {
            'feed_parser': {
                'statusCode': 200,
                'success': True,
                'articles': [
                    {
                        'article_id': 'article-1',
                        'title': 'Test Security Article',
                        'url': 'https://example.com/article1',
                        'normalized_content': 'This is a test article about AWS security.',
                        'published_at': '2024-01-01T12:00:00Z',
                        'source': 'test-source'
                    }
                ]
            },
            'relevancy_evaluator': {
                'statusCode': 200,
                'success': True,
                'body': {
                    'is_relevant': True,
                    'relevancy_score': 0.85,
                    'keyword_matches': [
                        {
                            'keyword': 'AWS',
                            'hit_count': 2,
                            'contexts': ['AWS security', 'AWS services']
                        }
                    ],
                    'entities': {
                        'cves': ['CVE-2024-1234'],
                        'vendors': ['Amazon'],
                        'products': ['AWS']
                    },
                    'confidence': 0.9
                }
            },
            'dedup_tool': {
                'statusCode': 200,
                'success': True,
                'body': {
                    'is_duplicate': False,
                    'cluster_id': 'cluster-123',
                    'similarity_score': 0.1
                }
            },
            'guardrail_tool': {
                'statusCode': 200,
                'success': True,
                'body': {
                    'passed': True,
                    'flags': [],
                    'violations': [],
                    'confidence': 0.95
                }
            },
            'storage_tool': {
                'statusCode': 200,
                'success': True,
                'body': {
                    'article_id': 'article-1',
                    'state': 'PROCESSED'
                }
            },
            'notifier': {
                'statusCode': 200,
                'success': True,
                'body': {
                    'sent': True,
                    'message_id': 'msg-123'
                }
            }
        }
    
    @patch('agent_shim.lambda_client')
    def test_execute_ingestor_workflow_success(self, mock_lambda_client, orchestrator, sample_event, mock_lambda_responses):
        """Test successful ingestor workflow execution."""
        # Mock Lambda invocations
        def mock_invoke(FunctionName, InvocationType, Payload):
            payload_data = json.loads(Payload)
            
            # Determine which tool is being called based on function name
            for tool_name, function_name in orchestrator.tool_mappings.items():
                if function_name in FunctionName:
                    response_data = mock_lambda_responses.get(tool_name, {})
                    break
            else:
                response_data = {'success': False, 'error': 'Unknown function'}
            
            mock_response = Mock()
            mock_response['Payload'].read.return_value = json.dumps(response_data).encode()
            return mock_response
        
        mock_lambda_client.invoke.side_effect = mock_invoke
        
        # Execute workflow
        result = orchestrator.execute_ingestor_workflow(sample_event)
        
        # Verify results
        assert result['statusCode'] == 200
        assert result['body']['success'] is True
        assert result['body']['orchestrator'] == 'direct'
        
        workflow_results = result['body']['workflow_results']
        assert workflow_results['feed_id'] == 'test-feed'
        assert workflow_results['articles_processed'] == 1
        assert workflow_results['articles_published'] == 1  # High relevancy + keywords = AUTO_PUBLISH
        assert len(workflow_results['processed_articles']) == 1
        
        processed_article = workflow_results['processed_articles'][0]
        assert processed_article['status'] == 'completed'
        assert processed_article['action'] == 'AUTO_PUBLISH'
    
    @patch('agent_shim.lambda_client')
    def test_execute_ingestor_workflow_with_review(self, mock_lambda_client, orchestrator, sample_event, mock_lambda_responses):
        """Test ingestor workflow with article requiring review."""
        # Modify relevancy score to trigger review
        mock_lambda_responses['relevancy_evaluator']['body']['relevancy_score'] = 0.7
        
        def mock_invoke(FunctionName, InvocationType, Payload):
            for tool_name, function_name in orchestrator.tool_mappings.items():
                if function_name in FunctionName:
                    response_data = mock_lambda_responses.get(tool_name, {})
                    break
            else:
                response_data = {'success': False, 'error': 'Unknown function'}
            
            mock_response = Mock()
            mock_response['Payload'].read.return_value = json.dumps(response_data).encode()
            return mock_response
        
        mock_lambda_client.invoke.side_effect = mock_invoke
        
        # Execute workflow
        result = orchestrator.execute_ingestor_workflow(sample_event)
        
        # Verify results
        assert result['statusCode'] == 200
        workflow_results = result['body']['workflow_results']
        assert workflow_results['articles_escalated'] == 1
        
        processed_article = workflow_results['processed_articles'][0]
        assert processed_article['action'] == 'REVIEW'
    
    @patch('agent_shim.lambda_client')
    def test_execute_ingestor_workflow_with_duplicate(self, mock_lambda_client, orchestrator, sample_event, mock_lambda_responses):
        """Test ingestor workflow with duplicate article."""
        # Mark article as duplicate
        mock_lambda_responses['dedup_tool']['body']['is_duplicate'] = True
        mock_lambda_responses['dedup_tool']['body']['duplicate_of'] = 'original-article-id'
        
        def mock_invoke(FunctionName, InvocationType, Payload):
            for tool_name, function_name in orchestrator.tool_mappings.items():
                if function_name in FunctionName:
                    response_data = mock_lambda_responses.get(tool_name, {})
                    break
            else:
                response_data = {'success': False, 'error': 'Unknown function'}
            
            mock_response = Mock()
            mock_response['Payload'].read.return_value = json.dumps(response_data).encode()
            return mock_response
        
        mock_lambda_client.invoke.side_effect = mock_invoke
        
        # Execute workflow
        result = orchestrator.execute_ingestor_workflow(sample_event)
        
        # Verify results
        assert result['statusCode'] == 200
        workflow_results = result['body']['workflow_results']
        assert workflow_results['articles_dropped'] == 1
        
        processed_article = workflow_results['processed_articles'][0]
        assert processed_article['action'] == 'DROP'
        assert processed_article['reason'] == 'duplicate'
    
    def test_make_triage_decision_auto_publish(self, orchestrator):
        """Test triage decision for auto-publish scenario."""
        relevance_data = {
            'relevancy_score': 0.9,
            'keyword_matches': [{'keyword': 'AWS', 'hit_count': 2}]
        }
        guardrail_data = {'passed': True}
        
        decision = orchestrator._make_triage_decision(relevance_data, guardrail_data)
        assert decision == 'AUTO_PUBLISH'
    
    def test_make_triage_decision_review(self, orchestrator):
        """Test triage decision for review scenario."""
        relevance_data = {
            'relevancy_score': 0.7,
            'keyword_matches': [{'keyword': 'security', 'hit_count': 1}]
        }
        guardrail_data = {'passed': True}
        
        decision = orchestrator._make_triage_decision(relevance_data, guardrail_data)
        assert decision == 'REVIEW'
    
    def test_make_triage_decision_drop(self, orchestrator):
        """Test triage decision for drop scenario."""
        relevance_data = {
            'relevancy_score': 0.4,
            'keyword_matches': []
        }
        guardrail_data = {'passed': True}
        
        decision = orchestrator._make_triage_decision(relevance_data, guardrail_data)
        assert decision == 'DROP'
    
    def test_make_triage_decision_guardrail_fail(self, orchestrator):
        """Test triage decision when guardrails fail."""
        relevance_data = {
            'relevancy_score': 0.9,
            'keyword_matches': [{'keyword': 'AWS', 'hit_count': 2}]
        }
        guardrail_data = {'passed': False, 'violations': ['PII detected']}
        
        decision = orchestrator._make_triage_decision(relevance_data, guardrail_data)
        assert decision == 'REVIEW'
    
    def test_get_escalation_priority(self, orchestrator):
        """Test escalation priority determination."""
        # High priority with CVEs
        relevance_data = {
            'relevancy_score': 0.8,
            'entities': {'cves': ['CVE-2024-1234']}
        }
        priority = orchestrator._get_escalation_priority(relevance_data)
        assert priority == 'high'
        
        # Medium priority with high relevancy
        relevance_data = {
            'relevancy_score': 0.9,
            'entities': {}
        }
        priority = orchestrator._get_escalation_priority(relevance_data)
        assert priority == 'medium'
        
        # Low priority
        relevance_data = {
            'relevancy_score': 0.6,
            'entities': {}
        }
        priority = orchestrator._get_escalation_priority(relevance_data)
        assert priority == 'low'


class TestBedrockAgentCoreOrchestrator:
    """Test cases for Bedrock AgentCore orchestration."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create a BedrockAgentCoreOrchestrator instance for testing."""
        with patch.dict(os.environ, {
            'INGESTOR_AGENT_ID': 'test-ingestor-agent-id',
            'ANALYST_ASSISTANT_AGENT_ID': 'test-analyst-agent-id'
        }):
            return BedrockAgentCoreOrchestrator()
    
    @pytest.fixture
    def sample_ingestor_event(self):
        """Sample event for ingestor testing."""
        return {
            'feed_config': {
                'feed_id': 'test-feed',
                'feed_url': 'https://example.com/feed.xml'
            },
            'session_id': 'test-session-123'
        }
    
    @pytest.fixture
    def sample_analyst_event(self):
        """Sample event for analyst assistant testing."""
        return {
            'query': 'Show me recent AWS security vulnerabilities',
            'session_id': 'test-session-456'
        }
    
    @patch('agent_shim.bedrock_agent_runtime')
    def test_execute_ingestor_workflow_success(self, mock_bedrock_client, orchestrator, sample_ingestor_event):
        """Test successful ingestor workflow execution via AgentCore."""
        # Mock Bedrock agent response
        mock_response = {
            'completion': [
                {
                    'chunk': {
                        'bytes': b'{"success": true, "articles_processed": 5}'
                    }
                }
            ],
            'sessionId': 'test-session-123',
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        mock_bedrock_client.invoke_agent.return_value = mock_response
        
        # Execute workflow
        result = orchestrator.execute_ingestor_workflow(sample_ingestor_event)
        
        # Verify results
        assert result['statusCode'] == 200
        assert result['body']['success'] is True
        assert result['body']['orchestrator'] == 'agentcore'
        
        # Verify Bedrock agent was called correctly
        mock_bedrock_client.invoke_agent.assert_called_once()
        call_args = mock_bedrock_client.invoke_agent.call_args
        assert call_args[1]['agentId'] == 'test-ingestor-agent-id'
        assert call_args[1]['sessionId'] == 'test-session-123'
    
    @patch('agent_shim.bedrock_agent_runtime')
    def test_execute_analyst_query_success(self, mock_bedrock_client, orchestrator, sample_analyst_event):
        """Test successful analyst query execution via AgentCore."""
        # Mock Bedrock agent response
        mock_response = {
            'completion': [
                {
                    'chunk': {
                        'bytes': b'Here are the recent AWS security vulnerabilities...'
                    }
                }
            ],
            'sessionId': 'test-session-456',
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        mock_bedrock_client.invoke_agent.return_value = mock_response
        
        # Execute query
        result = orchestrator.execute_analyst_query(sample_analyst_event)
        
        # Verify results
        assert result['statusCode'] == 200
        assert result['body']['success'] is True
        assert result['body']['orchestrator'] == 'agentcore'
        
        # Verify Bedrock agent was called correctly
        mock_bedrock_client.invoke_agent.assert_called_once()
        call_args = mock_bedrock_client.invoke_agent.call_args
        assert call_args[1]['agentId'] == 'test-analyst-agent-id'
        assert call_args[1]['inputText'] == 'Show me recent AWS security vulnerabilities'
    
    def test_missing_agent_id_error(self):
        """Test error when agent ID is missing."""
        orchestrator = BedrockAgentCoreOrchestrator()  # No env vars set
        
        event = {'feed_config': {'feed_id': 'test'}}
        result = orchestrator.execute_ingestor_workflow(event)
        
        assert result['statusCode'] == 500
        assert 'INGESTOR_AGENT_ID' in result['body']['error']


class TestLambdaHandler:
    """Test cases for the main Lambda handler."""
    
    @pytest.fixture
    def ingestor_event(self):
        """Sample ingestor event."""
        return {
            'agent_type': 'ingestor',
            'operation': 'workflow',
            'feed_config': {
                'feed_id': 'test-feed',
                'feed_url': 'https://example.com/feed.xml'
            }
        }
    
    @pytest.fixture
    def analyst_event(self):
        """Sample analyst event."""
        return {
            'agent_type': 'analyst_assistant',
            'operation': 'query',
            'query': 'Show me recent security alerts'
        }
    
    @patch.dict(os.environ, {'ORCHESTRATOR': 'direct', 'ENABLE_AGENTS': 'false'})
    @patch('agent_shim.DirectLambdaOrchestrator')
    def test_lambda_handler_direct_mode(self, mock_orchestrator_class, ingestor_event):
        """Test Lambda handler in direct orchestration mode."""
        mock_orchestrator = Mock()
        mock_orchestrator.execute_ingestor_workflow.return_value = {
            'statusCode': 200,
            'body': {'success': True, 'orchestrator': 'direct'}
        }
        mock_orchestrator_class.return_value = mock_orchestrator
        
        result = lambda_handler(ingestor_event, None)
        
        assert result['statusCode'] == 200
        assert result['body']['orchestrator'] == 'direct'
        mock_orchestrator.execute_ingestor_workflow.assert_called_once_with(ingestor_event)
    
    @patch.dict(os.environ, {'ORCHESTRATOR': 'agentcore', 'ENABLE_AGENTS': 'true'})
    @patch('agent_shim.BedrockAgentCoreOrchestrator')
    def test_lambda_handler_agentcore_mode(self, mock_orchestrator_class, ingestor_event):
        """Test Lambda handler in AgentCore orchestration mode."""
        mock_orchestrator = Mock()
        mock_orchestrator.execute_ingestor_workflow.return_value = {
            'statusCode': 200,
            'body': {'success': True, 'orchestrator': 'agentcore'}
        }
        mock_orchestrator_class.return_value = mock_orchestrator
        
        result = lambda_handler(ingestor_event, None)
        
        assert result['statusCode'] == 200
        assert result['body']['orchestrator'] == 'agentcore'
        mock_orchestrator.execute_ingestor_workflow.assert_called_once_with(ingestor_event)
    
    @patch.dict(os.environ, {'ORCHESTRATOR': 'agentcore', 'ENABLE_AGENTS': 'false'})
    @patch('agent_shim.DirectLambdaOrchestrator')
    def test_lambda_handler_agents_disabled_override(self, mock_orchestrator_class, ingestor_event):
        """Test that ENABLE_AGENTS=false overrides ORCHESTRATOR=agentcore."""
        mock_orchestrator = Mock()
        mock_orchestrator.execute_ingestor_workflow.return_value = {
            'statusCode': 200,
            'body': {'success': True, 'orchestrator': 'direct'}
        }
        mock_orchestrator_class.return_value = mock_orchestrator
        
        result = lambda_handler(ingestor_event, None)
        
        # Should use direct mode despite ORCHESTRATOR=agentcore
        assert result['body']['orchestrator'] == 'direct'
        mock_orchestrator.execute_ingestor_workflow.assert_called_once_with(ingestor_event)
    
    def test_lambda_handler_unsupported_operation(self):
        """Test Lambda handler with unsupported operation."""
        event = {
            'agent_type': 'unknown',
            'operation': 'invalid'
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 500
        assert 'Unsupported operation' in result['body']['error']
    
    def test_lambda_handler_exception_handling(self):
        """Test Lambda handler exception handling."""
        # Invalid event that will cause an exception
        event = None
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 500
        assert result['body']['success'] is False
        assert 'error' in result['body']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])