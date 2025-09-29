"""
Unit tests for PublishDecision Lambda tool.

Tests decision processing, state transitions, audit trail creation,
downstream action triggering, and batch processing capabilities.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

# Import the module under test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_tools.publish_decision import (
    DecisionProcessor,
    StateTransitionManager,
    AuditTrailManager,
    DownstreamActionManager,
    DecisionResult,
    BatchDecisionResult,
    lambda_handler
)


class TestStateTransitionManager:
    """Test state transition validation logic."""
    
    def test_validate_transition_approve_from_review(self):
        """Test valid transition from REVIEW to PUBLISHED."""
        assert StateTransitionManager.validate_transition('REVIEW', 'approve') is True
    
    def test_validate_transition_reject_from_review(self):
        """Test valid transition from REVIEW to ARCHIVED."""
        assert StateTransitionManager.validate_transition('REVIEW', 'reject') is True
    
    def test_validate_transition_edit_from_review(self):
        """Test valid transition staying in REVIEW for edits."""
        assert StateTransitionManager.validate_transition('REVIEW', 'edit') is True
    
    def test_validate_transition_invalid_from_published(self):
        """Test invalid transition from PUBLISHED to REVIEW."""
        assert StateTransitionManager.validate_transition('PUBLISHED', 'approve') is False
    
    def test_validate_transition_invalid_from_archived(self):
        """Test invalid transition from ARCHIVED (terminal state)."""
        assert StateTransitionManager.validate_transition('ARCHIVED', 'approve') is False
    
    def test_validate_transition_unknown_decision(self):
        """Test validation with unknown decision."""
        assert StateTransitionManager.validate_transition('REVIEW', 'unknown_decision') is False
    
    def test_get_new_state(self):
        """Test getting new state from decision."""
        assert StateTransitionManager.get_new_state('approve') == 'PUBLISHED'
        assert StateTransitionManager.get_new_state('reject') == 'ARCHIVED'
        assert StateTransitionManager.get_new_state('edit') == 'REVIEW'
        assert StateTransitionManager.get_new_state('unknown') is None


class TestAuditTrailManager:
    """Test audit trail management."""
    
    @patch('lambda_tools.publish_decision.dynamodb')
    def test_create_audit_entry_success(self, mock_dynamodb):
        """Test successful audit entry creation."""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        manager = AuditTrailManager('test-articles')
        
        decision_data = {
            'decision': 'approve',
            'reviewer': 'analyst@example.com',
            'previous_state': 'REVIEW',
            'new_state': 'PUBLISHED',
            'rationale': 'Good security content',
            'confidence': 0.9
        }
        
        result = manager.create_audit_entry('test-article', decision_data)
        
        assert result is True
        mock_table.update_item.assert_called_once()
        
        # Verify audit entry structure
        call_args = mock_table.update_item.call_args[1]
        audit_entry = call_args['ExpressionAttributeValues'][':audit_entry'][0]
        assert audit_entry['article_id'] == 'test-article'
        assert audit_entry['decision'] == 'approve'
        assert audit_entry['reviewer'] == 'analyst@example.com'
        assert 'audit_id' in audit_entry
        assert 'timestamp' in audit_entry
    
    @patch('lambda_tools.publish_decision.dynamodb')
    def test_create_audit_entry_failure(self, mock_dynamodb):
        """Test audit entry creation failure."""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.update_item.side_effect = Exception("DynamoDB error")
        
        manager = AuditTrailManager('test-articles')
        
        result = manager.create_audit_entry('test-article', {})
        
        assert result is False


class TestDownstreamActionManager:
    """Test downstream action management."""
    
    @patch('lambda_tools.publish_decision.eventbridge_client')
    def test_trigger_approval_actions(self, mock_eventbridge):
        """Test downstream actions for approval."""
        manager = DownstreamActionManager('test-bus')
        
        article_data = {
            'title': 'Test Article',
            'source': 'test-source',
            'keyword_matches': [{'keyword': 'Azure'}],
            'priority_score': 0.8
        }
        
        actions = manager.trigger_downstream_actions('test-article', 'approve', article_data)
        
        assert 'publication_event_sent' in actions
        assert 'publication_notification_sent' in actions
        mock_eventbridge.put_events.assert_called_once()
        
        # Verify event structure
        call_args = mock_eventbridge.put_events.call_args[1]
        event = call_args['Entries'][0]
        assert event['Source'] == 'sentinel.publish-decision'
        assert event['DetailType'] == 'Article Approved'
        assert 'article_id' in json.loads(event['Detail'])
    
    @patch('lambda_tools.publish_decision.eventbridge_client')
    def test_trigger_rejection_actions(self, mock_eventbridge):
        """Test downstream actions for rejection."""
        manager = DownstreamActionManager('test-bus')
        
        article_data = {'rejection_reason': 'not_relevant'}
        
        actions = manager.trigger_downstream_actions('test-article', 'reject', article_data)
        
        assert 'archival_event_sent' in actions
        mock_eventbridge.put_events.assert_called_once()
        
        # Verify event structure
        call_args = mock_eventbridge.put_events.call_args[1]
        event = call_args['Entries'][0]
        assert event['DetailType'] == 'Article Rejected'
    
    @patch('lambda_tools.publish_decision.eventbridge_client')
    def test_trigger_edit_actions(self, mock_eventbridge):
        """Test downstream actions for edit requests."""
        manager = DownstreamActionManager('test-bus')
        
        article_data = {'edit_instructions': 'Update summary'}
        
        actions = manager.trigger_downstream_actions('test-article', 'edit', article_data)
        
        assert 'edit_event_sent' in actions
        mock_eventbridge.put_events.assert_called_once()
    
    @patch('lambda_tools.publish_decision.eventbridge_client')
    def test_trigger_escalation_actions(self, mock_eventbridge):
        """Test downstream actions for escalation."""
        manager = DownstreamActionManager('test-bus')
        
        article_data = {'escalation_reason': 'complex_case'}
        
        actions = manager.trigger_downstream_actions('test-article', 'escalate', article_data)
        
        assert 'escalation_event_sent' in actions
        mock_eventbridge.put_events.assert_called_once()


class TestDecisionProcessor:
    """Test main decision processing logic."""
    
    @patch('lambda_tools.publish_decision.dynamodb')
    @patch('lambda_tools.publish_decision.eventbridge_client')
    def test_process_decision_success(self, mock_eventbridge, mock_dynamodb):
        """Test successful decision processing."""
        # Mock DynamoDB
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            'Item': {
                'article_id': 'test-article',
                'state': 'REVIEW',
                'title': 'Test Article',
                'relevancy_score': Decimal('0.8')
            }
        }
        mock_table.update_item.return_value = {}
        
        processor = DecisionProcessor('test-articles', 'test-bus')
        
        result = processor.process_decision(
            'test-article', 'approve', 'analyst@example.com', 'Good content'
        )
        
        assert result.success is True
        assert result.article_id == 'test-article'
        assert result.decision == 'approve'
        assert result.previous_state == 'REVIEW'
        assert result.new_state == 'PUBLISHED'
        assert result.audit_trail_created is True
        assert len(result.downstream_actions) > 0
        
        # Verify DynamoDB update was called
        mock_table.update_item.assert_called()
    
    @patch('lambda_tools.publish_decision.dynamodb')
    def test_process_decision_article_not_found(self, mock_dynamodb):
        """Test decision processing when article is not found."""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {}  # No Item key
        
        processor = DecisionProcessor('test-articles')
        
        result = processor.process_decision(
            'nonexistent-article', 'approve', 'analyst@example.com'
        )
        
        assert result.success is False
        assert 'not found' in result.errors[0]
    
    @patch('lambda_tools.publish_decision.dynamodb')
    def test_process_decision_invalid_transition(self, mock_dynamodb):
        """Test decision processing with invalid state transition."""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            'Item': {
                'article_id': 'test-article',
                'state': 'ARCHIVED',  # Terminal state
                'title': 'Test Article'
            }
        }
        
        processor = DecisionProcessor('test-articles')
        
        result = processor.process_decision(
            'test-article', 'approve', 'analyst@example.com'
        )
        
        assert result.success is False
        assert 'Invalid transition' in result.errors[0]
    
    @patch('lambda_tools.publish_decision.dynamodb')
    @patch('lambda_tools.publish_decision.eventbridge_client')
    def test_process_decision_with_modifications(self, mock_eventbridge, mock_dynamodb):
        """Test decision processing with article modifications."""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            'Item': {
                'article_id': 'test-article',
                'state': 'REVIEW',
                'title': 'Test Article'
            }
        }
        mock_table.update_item.return_value = {}
        
        processor = DecisionProcessor('test-articles', 'test-bus')
        
        modifications = {
            'tags': ['azure', 'critical'],
            'summary_short': 'Updated summary',
            'confidence': 0.95
        }
        
        result = processor.process_decision(
            'test-article', 'approve', 'analyst@example.com', 
            'Good content', modifications
        )
        
        assert result.success is True
        assert result.metadata['modifications_applied'] is True
    
    @patch('lambda_tools.publish_decision.dynamodb')
    @patch('lambda_tools.publish_decision.eventbridge_client')
    def test_process_batch_decisions(self, mock_eventbridge, mock_dynamodb):
        """Test batch decision processing."""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            'Item': {
                'article_id': 'test-article',
                'state': 'REVIEW',
                'title': 'Test Article'
            }
        }
        mock_table.update_item.return_value = {}
        
        processor = DecisionProcessor('test-articles', 'test-bus')
        
        decisions = [
            {
                'article_id': 'article-1',
                'decision': 'approve',
                'reviewer': 'analyst1@example.com',
                'rationale': 'Good content'
            },
            {
                'article_id': 'article-2',
                'decision': 'reject',
                'reviewer': 'analyst2@example.com',
                'rationale': 'Not relevant'
            },
            {
                # Missing required fields
                'article_id': 'article-3'
            }
        ]
        
        result = processor.process_batch_decisions(decisions)
        
        assert result.total_items == 3
        assert result.successful_decisions == 2
        assert result.failed_decisions == 1
        assert len(result.decisions) == 3
        assert result.processing_time_seconds > 0


class TestLambdaHandler:
    """Test Lambda handler function."""
    
    @patch.dict(os.environ, {
        'ARTICLES_TABLE': 'test-articles',
        'EVENT_BUS_NAME': 'test-bus'
    })
    @patch('lambda_tools.publish_decision.DecisionProcessor')
    def test_lambda_handler_process_decision(self, mock_processor_class):
        """Test Lambda handler for process_decision operation."""
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor
        mock_processor.process_decision.return_value = DecisionResult(
            success=True,
            operation='process_decision',
            article_id='test-article',
            decision_id='test-decision',
            decision='approve',
            previous_state='REVIEW',
            new_state='PUBLISHED',
            downstream_actions=['publication_event_sent'],
            audit_trail_created=True
        )
        
        event = {
            'operation': 'process_decision',
            'article_id': 'test-article',
            'decision': 'approve',
            'reviewer': 'analyst@example.com',
            'rationale': 'Good content'
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        assert response['body']['success'] is True
        assert response['body']['article_id'] == 'test-article'
        assert response['body']['decision'] == 'approve'
        mock_processor.process_decision.assert_called_once()
    
    @patch.dict(os.environ, {
        'ARTICLES_TABLE': 'test-articles',
        'EVENT_BUS_NAME': 'test-bus'
    })
    @patch('lambda_tools.publish_decision.DecisionProcessor')
    def test_lambda_handler_batch_decisions(self, mock_processor_class):
        """Test Lambda handler for batch decision processing."""
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor
        mock_processor.process_batch_decisions.return_value = BatchDecisionResult(
            total_items=2,
            successful_decisions=2,
            failed_decisions=0,
            decisions=[
                DecisionResult(success=True, article_id='article-1', decision='approve'),
                DecisionResult(success=True, article_id='article-2', decision='reject')
            ],
            processing_time_seconds=1.5
        )
        
        event = {
            'operation': 'process_batch_decisions',
            'decisions': [
                {
                    'article_id': 'article-1',
                    'decision': 'approve',
                    'reviewer': 'analyst@example.com'
                },
                {
                    'article_id': 'article-2',
                    'decision': 'reject',
                    'reviewer': 'analyst@example.com'
                }
            ]
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        assert response['body']['success'] is True
        assert response['body']['total_items'] == 2
        assert response['body']['successful_decisions'] == 2
        mock_processor.process_batch_decisions.assert_called_once()
    
    def test_lambda_handler_missing_required_fields(self):
        """Test Lambda handler with missing required fields."""
        event = {
            'operation': 'process_decision',
            'article_id': 'test-article'
            # Missing decision and reviewer
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        assert response['body']['success'] is False
        assert 'required' in response['body']['error']
    
    def test_lambda_handler_unknown_operation(self):
        """Test Lambda handler with unknown operation."""
        event = {
            'operation': 'unknown_operation'
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        assert response['body']['success'] is False
        assert 'Unknown operation' in response['body']['error']
    
    def test_lambda_handler_empty_batch(self):
        """Test Lambda handler with empty batch decisions."""
        event = {
            'operation': 'process_batch_decisions',
            'decisions': []
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        assert response['body']['success'] is False
        assert 'required' in response['body']['error']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])