"""
Unit tests for HumanEscalation Lambda tool.

Tests escalation logic, priority calculation, queue management,
SES notifications, and error handling.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# Import the module under test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_tools.human_escalation import (
    HumanEscalationTool,
    PriorityCalculator,
    NotificationManager,
    QueueManager,
    EscalationResult,
    lambda_handler
)


class TestPriorityCalculator:
    """Test priority calculation logic."""
    
    def test_calculate_priority_score_high_relevancy(self):
        """Test priority calculation with high relevancy score."""
        article_data = {
            'relevancy_score': 0.9,
            'keyword_matches': [
                {'keyword': 'Azure', 'hit_count': 3},
                {'keyword': 'CVE', 'hit_count': 1}
            ],
            'entities': {
                'cves': ['CVE-2024-1234'],
                'vendors': ['Microsoft', 'Azure'],
                'products': ['Office 365']
            },
            'guardrail_flags': [],
            'published_at': datetime.now(timezone.utc).isoformat()
        }
        
        score = PriorityCalculator.calculate_priority_score(article_data, 'guardrail_violation')
        
        # Should be high priority due to high relevancy and guardrail violation multiplier
        assert score > 0.7
        assert score <= 1.0
    
    def test_calculate_priority_score_low_relevancy(self):
        """Test priority calculation with low relevancy score."""
        article_data = {
            'relevancy_score': 0.2,
            'keyword_matches': [],
            'entities': {},
            'guardrail_flags': [],
            'published_at': (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        }
        
        score = PriorityCalculator.calculate_priority_score(article_data, 'low_confidence')
        
        # Should be low priority
        assert score < 0.5
        assert score >= 0.0
    
    def test_calculate_priority_score_sensitive_content(self):
        """Test priority calculation for sensitive content."""
        article_data = {
            'relevancy_score': 0.6,
            'keyword_matches': [{'keyword': 'classified', 'hit_count': 1}],
            'entities': {'threat_actors': ['APT29']},
            'guardrail_flags': ['potential_pii', 'sensitive_data'],
            'published_at': datetime.now(timezone.utc).isoformat()
        }
        
        score = PriorityCalculator.calculate_priority_score(article_data, 'sensitive_content')
        
        # Should be high priority due to sensitive content multiplier (1.8)
        assert score > 0.8
    
    def test_calculate_priority_score_time_decay(self):
        """Test priority calculation with time decay."""
        # Recent article
        recent_data = {
            'relevancy_score': 0.5,
            'keyword_matches': [],
            'entities': {},
            'guardrail_flags': [],
            'published_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Old article (2 days ago)
        old_data = recent_data.copy()
        old_data['published_at'] = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        
        recent_score = PriorityCalculator.calculate_priority_score(recent_data, 'manual_review_requested')
        old_score = PriorityCalculator.calculate_priority_score(old_data, 'manual_review_requested')
        
        # Recent article should have higher priority
        assert recent_score > old_score
    
    def test_calculate_priority_score_invalid_date(self):
        """Test priority calculation with invalid date."""
        article_data = {
            'relevancy_score': 0.5,
            'keyword_matches': [],
            'entities': {},
            'guardrail_flags': [],
            'published_at': 'invalid-date'
        }
        
        # Should not crash and return reasonable score
        score = PriorityCalculator.calculate_priority_score(article_data, 'manual_review_requested')
        assert 0.0 <= score <= 1.0
    
    def test_calculate_priority_score_missing_data(self):
        """Test priority calculation with missing data."""
        article_data = {}
        
        score = PriorityCalculator.calculate_priority_score(article_data, 'manual_review_requested')
        
        # Should handle missing data gracefully
        assert 0.0 <= score <= 1.0


class TestNotificationManager:
    """Test notification management."""
    
    @patch('lambda_tools.human_escalation.ses_client')
    def test_send_escalation_notification_success(self, mock_ses):
        """Test successful escalation notification."""
        mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
        
        manager = NotificationManager(
            sender_email='test@example.com',
            escalation_emails=['analyst@example.com']
        )
        
        article_data = {
            'title': 'Test Security Alert',
            'url': 'https://example.com/alert',
            'source': 'test-source',
            'published_at': '2024-01-01T12:00:00Z',
            'relevancy_score': 0.8,
            'keyword_matches': [{'keyword': 'Azure'}],
            'entities': {'cves': ['CVE-2024-1234']},
            'guardrail_flags': []
        }
        
        result = manager.send_escalation_notification(
            article_data, 'guardrail_violation', 0.85, 'test-escalation-id'
        )
        
        assert result is True
        mock_ses.send_email.assert_called_once()
        
        # Verify email content
        call_args = mock_ses.send_email.call_args[1]
        assert call_args['Source'] == 'test@example.com'
        assert 'analyst@example.com' in call_args['Destination']['ToAddresses']
        assert 'SENTINEL' in call_args['Message']['Subject']['Data']
        assert 'Test Security Alert' in call_args['Message']['Body']['Text']['Data']
    
    @patch('lambda_tools.human_escalation.ses_client')
    def test_send_escalation_notification_failure(self, mock_ses):
        """Test escalation notification failure."""
        from botocore.exceptions import ClientError
        
        mock_ses.send_email.side_effect = ClientError(
            {'Error': {'Code': 'MessageRejected', 'Message': 'Email rejected'}},
            'SendEmail'
        )
        
        manager = NotificationManager(
            sender_email='test@example.com',
            escalation_emails=['analyst@example.com']
        )
        
        article_data = {'title': 'Test Alert'}
        
        result = manager.send_escalation_notification(
            article_data, 'guardrail_violation', 0.85, 'test-escalation-id'
        )
        
        assert result is False
    
    def test_send_escalation_notification_no_recipients(self):
        """Test escalation notification with no recipients."""
        manager = NotificationManager(
            sender_email='test@example.com',
            escalation_emails=[]
        )
        
        article_data = {'title': 'Test Alert'}
        
        result = manager.send_escalation_notification(
            article_data, 'guardrail_violation', 0.85, 'test-escalation-id'
        )
        
        assert result is False
    
    def test_generate_subject(self):
        """Test email subject generation."""
        manager = NotificationManager('test@example.com', ['analyst@example.com'])
        
        article_data = {'title': 'Very Long Article Title That Should Be Truncated'}
        subject = manager._generate_subject(article_data, 'guardrail_violation', 0.9)
        
        assert 'SENTINEL' in subject
        assert 'CRITICAL' in subject
        assert len(subject) < 100  # Should be truncated
    
    def test_get_priority_label(self):
        """Test priority label generation."""
        manager = NotificationManager('test@example.com', ['analyst@example.com'])
        
        assert manager._get_priority_label(0.9) == 'CRITICAL'
        assert manager._get_priority_label(0.7) == 'HIGH'
        assert manager._get_priority_label(0.5) == 'MEDIUM'
        assert manager._get_priority_label(0.2) == 'LOW'


class TestQueueManager:
    """Test queue management."""
    
    @patch('lambda_tools.human_escalation.dynamodb')
    def test_add_to_queue_success(self, mock_dynamodb):
        """Test successful addition to queue."""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.update_item.return_value = {'Attributes': {'version': 2}}
        
        manager = QueueManager('test-articles')
        
        result = manager.add_to_queue(
            'test-article-id', 'guardrail_violation', 0.8, {'test': 'context'}
        )
        
        assert result.success is True
        assert result.article_id == 'test-article-id'
        assert result.priority_score == 0.8
        assert result.escalation_id is not None
        
        mock_table.update_item.assert_called_once()
    
    @patch('lambda_tools.human_escalation.dynamodb')
    def test_add_to_queue_article_not_found(self, mock_dynamodb):
        """Test addition to queue when article doesn't exist."""
        from botocore.exceptions import ClientError
        
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.update_item.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}},
            'UpdateItem'
        )
        
        manager = QueueManager('test-articles')
        
        result = manager.add_to_queue(
            'nonexistent-article', 'guardrail_violation', 0.8, {}
        )
        
        assert result.success is False
        assert 'does not exist' in result.errors[0]
    
    @patch('lambda_tools.human_escalation.dynamodb')
    def test_estimate_queue_position(self, mock_dynamodb):
        """Test queue position estimation."""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.query.return_value = {'Count': 5}
        
        manager = QueueManager('test-articles')
        position = manager._estimate_queue_position(0.7)
        
        assert position == 6  # 5 higher priority items + 1


class TestHumanEscalationTool:
    """Test main escalation tool."""
    
    @patch('lambda_tools.human_escalation.dynamodb')
    @patch('lambda_tools.human_escalation.ses_client')
    def test_escalate_article_success(self, mock_ses, mock_dynamodb):
        """Test successful article escalation."""
        # Mock DynamoDB
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            'Item': {
                'article_id': 'test-article',
                'title': 'Test Article',
                'relevancy_score': Decimal('0.8'),
                'keyword_matches': [],
                'entities': {},
                'guardrail_flags': []
            }
        }
        mock_table.update_item.return_value = {'Attributes': {'version': 2}}
        
        # Mock SES
        mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
        
        tool = HumanEscalationTool(
            'test-articles', 'test@example.com', ['analyst@example.com']
        )
        
        result = tool.escalate_article('test-article', 'guardrail_violation')
        
        assert result.success is True
        assert result.article_id == 'test-article'
        assert result.escalation_id is not None
        assert result.priority_score is not None
        assert result.notification_sent is True
    
    @patch('lambda_tools.human_escalation.dynamodb')
    def test_escalate_article_with_provided_data(self, mock_dynamodb):
        """Test escalation with provided article data."""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.update_item.return_value = {'Attributes': {'version': 2}}
        
        tool = HumanEscalationTool(
            'test-articles', 'test@example.com', []
        )
        
        article_data = {
            'title': 'Test Article',
            'relevancy_score': 0.8,
            'keyword_matches': [],
            'entities': {},
            'guardrail_flags': []
        }
        
        result = tool.escalate_article(
            'test-article', 'guardrail_violation', article_data
        )
        
        assert result.success is True
        # Should not call get_item since data was provided
        mock_table.get_item.assert_not_called()
    
    @patch('lambda_tools.human_escalation.dynamodb')
    def test_escalate_article_not_found(self, mock_dynamodb):
        """Test escalation when article is not found."""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {}  # No Item key
        
        tool = HumanEscalationTool(
            'test-articles', 'test@example.com', ['analyst@example.com']
        )
        
        result = tool.escalate_article('nonexistent-article', 'guardrail_violation')
        
        assert result.success is False
        assert 'not found' in result.errors[0]


class TestLambdaHandler:
    """Test Lambda handler function."""
    
    @patch.dict(os.environ, {
        'ARTICLES_TABLE': 'test-articles',
        'SES_SENDER_EMAIL': 'test@example.com',
        'ESCALATION_EMAILS': 'analyst1@example.com,analyst2@example.com'
    })
    @patch('lambda_tools.human_escalation.HumanEscalationTool')
    def test_lambda_handler_escalate_article(self, mock_tool_class):
        """Test Lambda handler for escalate_article operation."""
        mock_tool = Mock()
        mock_tool_class.return_value = mock_tool
        mock_tool.escalate_article.return_value = EscalationResult(
            success=True,
            operation='escalate_article',
            article_id='test-article',
            escalation_id='test-escalation',
            priority_score=0.8,
            notification_sent=True
        )
        
        event = {
            'operation': 'escalate_article',
            'article_id': 'test-article',
            'escalation_reason': 'guardrail_violation'
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        assert response['body']['success'] is True
        assert response['body']['article_id'] == 'test-article'
        mock_tool.escalate_article.assert_called_once()
    
    @patch.dict(os.environ, {
        'ARTICLES_TABLE': 'test-articles',
        'SES_SENDER_EMAIL': 'test@example.com',
        'ESCALATION_EMAILS': 'analyst@example.com'
    })
    def test_lambda_handler_calculate_priority(self):
        """Test Lambda handler for calculate_priority operation."""
        event = {
            'operation': 'calculate_priority',
            'article_data': {
                'relevancy_score': 0.8,
                'keyword_matches': [],
                'entities': {},
                'guardrail_flags': []
            },
            'escalation_reason': 'guardrail_violation'
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        assert response['body']['success'] is True
        assert 'priority_score' in response['body']
    
    def test_lambda_handler_missing_article_id(self):
        """Test Lambda handler with missing article_id."""
        event = {
            'operation': 'escalate_article',
            'escalation_reason': 'guardrail_violation'
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        assert response['body']['success'] is False
        assert 'article_id is required' in response['body']['error']
    
    def test_lambda_handler_unknown_operation(self):
        """Test Lambda handler with unknown operation."""
        event = {
            'operation': 'unknown_operation'
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        assert response['body']['success'] is False
        assert 'Unknown operation' in response['body']['error']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])