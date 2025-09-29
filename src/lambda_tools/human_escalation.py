"""
HumanEscalation Lambda tool for queuing items for human review.

This Lambda function handles queuing articles for human review, sending SES notifications
to reviewers, implementing priority scoring and queue management, escalation reason tracking,
and context preservation for the Sentinel cybersecurity triage system.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from decimal import Decimal
import uuid
import os

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')
ses_client = boto3.client('ses')
sqs_client = boto3.client('sqs')


@dataclass
class EscalationResult:
    """Result of escalation operations."""
    success: bool
    operation: str
    article_id: Optional[str] = None
    escalation_id: Optional[str] = None
    priority_score: Optional[float] = None
    queue_position: Optional[int] = None
    notification_sent: bool = False
    errors: List[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}


class EscalationError(Exception):
    """Custom exception for escalation errors."""
    pass


class PriorityCalculator:
    """Calculates priority scores for escalated items."""
    
    # Priority weights for different factors
    WEIGHTS = {
        'relevancy_score': 0.3,
        'keyword_matches': 0.25,
        'entity_count': 0.15,
        'guardrail_violations': 0.2,
        'time_sensitivity': 0.1
    }
    
    # Escalation reason priority multipliers
    REASON_MULTIPLIERS = {
        'guardrail_violation': 1.5,
        'low_confidence': 1.2,
        'complex_entities': 1.3,
        'sensitive_content': 1.8,
        'potential_false_positive': 1.1,
        'manual_review_requested': 1.0,
        'quality_concern': 1.4,
        'policy_violation': 1.6
    }
    
    @classmethod
    def calculate_priority_score(cls, article_data: Dict[str, Any], 
                               escalation_reason: str) -> float:
        """Calculate priority score for an escalated article."""
        try:
            score = 0.0
            
            # Relevancy score component
            relevancy_score = article_data.get('relevancy_score', 0.0)
            score += relevancy_score * cls.WEIGHTS['relevancy_score']
            
            # Keyword matches component
            keyword_matches = article_data.get('keyword_matches', [])
            keyword_score = min(len(keyword_matches) / 5.0, 1.0)  # Normalize to max 5 keywords
            score += keyword_score * cls.WEIGHTS['keyword_matches']
            
            # Entity count component
            entities = article_data.get('entities', {})
            total_entities = sum(len(entity_list) for entity_list in entities.values() if isinstance(entity_list, list))
            entity_score = min(total_entities / 10.0, 1.0)  # Normalize to max 10 entities
            score += entity_score * cls.WEIGHTS['entity_count']
            
            # Guardrail violations component
            guardrail_flags = article_data.get('guardrail_flags', [])
            violation_score = min(len(guardrail_flags) / 3.0, 1.0)  # Normalize to max 3 violations
            score += violation_score * cls.WEIGHTS['guardrail_violations']
            
            # Time sensitivity component (newer articles get higher priority)
            published_at = article_data.get('published_at')
            if published_at:
                try:
                    if isinstance(published_at, str):
                        pub_time = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    else:
                        pub_time = published_at
                    
                    hours_old = (datetime.now(timezone.utc) - pub_time).total_seconds() / 3600
                    time_score = max(0.0, 1.0 - (hours_old / 24.0))  # Decay over 24 hours
                    score += time_score * cls.WEIGHTS['time_sensitivity']
                except Exception as e:
                    logger.warning(f"Error parsing published_at: {e}")
            
            # Apply reason multiplier
            reason_multiplier = cls.REASON_MULTIPLIERS.get(escalation_reason, 1.0)
            score *= reason_multiplier
            
            # Ensure score is between 0 and 1
            return min(max(score, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating priority score: {e}")
            return 0.5  # Default medium priority


class NotificationManager:
    """Handles SES notifications for escalated items."""
    
    def __init__(self, sender_email: str, escalation_emails: List[str]):
        self.sender_email = sender_email
        self.escalation_emails = escalation_emails
    
    def send_escalation_notification(self, article_data: Dict[str, Any], 
                                   escalation_reason: str, priority_score: float,
                                   escalation_id: str) -> bool:
        """Send email notification for escalated item."""
        try:
            if not self.escalation_emails:
                logger.warning("No escalation email addresses configured")
                return False
            
            # Prepare email content
            subject = self._generate_subject(article_data, escalation_reason, priority_score)
            body_text = self._generate_text_body(article_data, escalation_reason, priority_score, escalation_id)
            body_html = self._generate_html_body(article_data, escalation_reason, priority_score, escalation_id)
            
            # Send to all escalation recipients
            for recipient in self.escalation_emails:
                try:
                    response = ses_client.send_email(
                        Source=self.sender_email,
                        Destination={'ToAddresses': [recipient]},
                        Message={
                            'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                            'Body': {
                                'Text': {'Data': body_text, 'Charset': 'UTF-8'},
                                'Html': {'Data': body_html, 'Charset': 'UTF-8'}
                            }
                        },
                        Tags=[
                            {'Name': 'Type', 'Value': 'Escalation'},
                            {'Name': 'Priority', 'Value': self._get_priority_label(priority_score)},
                            {'Name': 'Reason', 'Value': escalation_reason}
                        ]
                    )
                    logger.info(f"Escalation notification sent to {recipient}: {response['MessageId']}")
                    
                except ClientError as e:
                    logger.error(f"Failed to send escalation notification to {recipient}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending escalation notification: {e}")
            return False
    
    def _generate_subject(self, article_data: Dict[str, Any], 
                         escalation_reason: str, priority_score: float) -> str:
        """Generate email subject line."""
        priority_label = self._get_priority_label(priority_score)
        title = article_data.get('title', 'Unknown Article')[:50]
        return f"[SENTINEL {priority_label}] Review Required: {title}..."
    
    def _generate_text_body(self, article_data: Dict[str, Any], 
                           escalation_reason: str, priority_score: float,
                           escalation_id: str) -> str:
        """Generate plain text email body."""
        priority_label = self._get_priority_label(priority_score)
        
        body = f"""
SENTINEL CYBERSECURITY TRIAGE - REVIEW REQUIRED

Escalation ID: {escalation_id}
Priority: {priority_label} ({priority_score:.2f})
Reason: {escalation_reason.replace('_', ' ').title()}

ARTICLE DETAILS:
Title: {article_data.get('title', 'N/A')}
Source: {article_data.get('source', 'N/A')}
URL: {article_data.get('url', 'N/A')}
Published: {article_data.get('published_at', 'N/A')}

ANALYSIS RESULTS:
Relevancy Score: {article_data.get('relevancy_score', 'N/A')}
Keyword Matches: {len(article_data.get('keyword_matches', []))}
Entities Found: {sum(len(v) if isinstance(v, list) else 0 for v in article_data.get('entities', {}).values())}
Guardrail Flags: {', '.join(article_data.get('guardrail_flags', [])) or 'None'}

ESCALATION CONTEXT:
{self._get_escalation_context(escalation_reason, article_data)}

Please review this item in the Sentinel dashboard and make an approval/rejection decision.

---
This is an automated notification from Sentinel Cybersecurity Triage System.
"""
        return body.strip()
    
    def _generate_html_body(self, article_data: Dict[str, Any], 
                           escalation_reason: str, priority_score: float,
                           escalation_id: str) -> str:
        """Generate HTML email body."""
        priority_label = self._get_priority_label(priority_score)
        priority_color = self._get_priority_color(priority_score)
        
        keyword_matches = article_data.get('keyword_matches', [])
        keyword_list = ', '.join([kw.get('keyword', '') for kw in keyword_matches]) if keyword_matches else 'None'
        
        entities = article_data.get('entities', {})
        entity_summary = []
        for entity_type, entity_list in entities.items():
            if isinstance(entity_list, list) and entity_list:
                entity_summary.append(f"{entity_type.title()}: {len(entity_list)}")
        
        body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #1f2937; color: white; padding: 15px; border-radius: 5px; }}
        .priority {{ background-color: {priority_color}; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold; }}
        .section {{ margin: 15px 0; padding: 10px; border-left: 3px solid #3b82f6; background-color: #f8fafc; }}
        .field {{ margin: 5px 0; }}
        .label {{ font-weight: bold; color: #374151; }}
        .value {{ color: #6b7280; }}
        .url {{ color: #3b82f6; text-decoration: none; }}
        .footer {{ margin-top: 20px; padding-top: 15px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #6b7280; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>🛡️ SENTINEL CYBERSECURITY TRIAGE - REVIEW REQUIRED</h2>
        <p>Escalation ID: <strong>{escalation_id}</strong></p>
        <p>Priority: <span class="priority">{priority_label}</span> ({priority_score:.2f})</p>
    </div>
    
    <div class="section">
        <h3>📋 Article Details</h3>
        <div class="field"><span class="label">Title:</span> <span class="value">{article_data.get('title', 'N/A')}</span></div>
        <div class="field"><span class="label">Source:</span> <span class="value">{article_data.get('source', 'N/A')}</span></div>
        <div class="field"><span class="label">URL:</span> <a href="{article_data.get('url', '#')}" class="url">{article_data.get('url', 'N/A')}</a></div>
        <div class="field"><span class="label">Published:</span> <span class="value">{article_data.get('published_at', 'N/A')}</span></div>
    </div>
    
    <div class="section">
        <h3>🔍 Analysis Results</h3>
        <div class="field"><span class="label">Relevancy Score:</span> <span class="value">{article_data.get('relevancy_score', 'N/A')}</span></div>
        <div class="field"><span class="label">Keywords Found:</span> <span class="value">{keyword_list}</span></div>
        <div class="field"><span class="label">Entities:</span> <span class="value">{', '.join(entity_summary) if entity_summary else 'None'}</span></div>
        <div class="field"><span class="label">Guardrail Flags:</span> <span class="value">{', '.join(article_data.get('guardrail_flags', [])) or 'None'}</span></div>
    </div>
    
    <div class="section">
        <h3>⚠️ Escalation Reason</h3>
        <p><strong>{escalation_reason.replace('_', ' ').title()}</strong></p>
        <p>{self._get_escalation_context(escalation_reason, article_data)}</p>
    </div>
    
    <div class="footer">
        <p>Please review this item in the Sentinel dashboard and make an approval/rejection decision.</p>
        <p><em>This is an automated notification from Sentinel Cybersecurity Triage System.</em></p>
    </div>
</body>
</html>
"""
        return body
    
    def _get_priority_label(self, priority_score: float) -> str:
        """Get priority label from score."""
        if priority_score >= 0.8:
            return "CRITICAL"
        elif priority_score >= 0.6:
            return "HIGH"
        elif priority_score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _get_priority_color(self, priority_score: float) -> str:
        """Get color for priority level."""
        if priority_score >= 0.8:
            return "#dc2626"  # Red
        elif priority_score >= 0.6:
            return "#ea580c"  # Orange
        elif priority_score >= 0.4:
            return "#ca8a04"  # Yellow
        else:
            return "#16a34a"  # Green
    
    def _get_escalation_context(self, escalation_reason: str, article_data: Dict[str, Any]) -> str:
        """Get contextual information for escalation reason."""
        context_map = {
            'guardrail_violation': f"Guardrail violations detected: {', '.join(article_data.get('guardrail_flags', []))}",
            'low_confidence': f"Low confidence score: {article_data.get('confidence', 'N/A')}",
            'complex_entities': f"Complex entity extraction with {sum(len(v) if isinstance(v, list) else 0 for v in article_data.get('entities', {}).values())} entities",
            'sensitive_content': "Content flagged as potentially sensitive or requiring careful review",
            'potential_false_positive': f"Relevancy score of {article_data.get('relevancy_score', 'N/A')} may indicate false positive",
            'manual_review_requested': "Manual review explicitly requested by system or user",
            'quality_concern': "Content quality concerns identified during processing",
            'policy_violation': "Potential policy violation detected in content"
        }
        return context_map.get(escalation_reason, "Review required for manual assessment")


class QueueManager:
    """Manages the human review queue in DynamoDB."""
    
    def __init__(self, articles_table_name: str):
        self.articles_table = dynamodb.Table(articles_table_name)
    
    def add_to_queue(self, article_id: str, escalation_reason: str, 
                    priority_score: float, context: Dict[str, Any]) -> EscalationResult:
        """Add article to human review queue."""
        try:
            escalation_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Adding article {article_id} to review queue with priority {priority_score}")
            
            # Update article state and add escalation metadata
            update_expression = """
                SET #state = :state,
                    #escalation_id = :escalation_id,
                    #escalation_reason = :escalation_reason,
                    #priority_score = :priority_score,
                    #escalated_at = :escalated_at,
                    #escalation_context = :escalation_context,
                    #updated_at = :updated_at
            """
            
            expression_attribute_names = {
                '#state': 'state',
                '#escalation_id': 'escalation_id',
                '#escalation_reason': 'escalation_reason',
                '#priority_score': 'priority_score',
                '#escalated_at': 'escalated_at',
                '#escalation_context': 'escalation_context',
                '#updated_at': 'updated_at'
            }
            
            expression_attribute_values = {
                ':state': 'REVIEW',
                ':escalation_id': escalation_id,
                ':escalation_reason': escalation_reason,
                ':priority_score': Decimal(str(priority_score)),
                ':escalated_at': now,
                ':escalation_context': context,
                ':updated_at': now
            }
            
            # Update with condition that article exists
            response = self.articles_table.update_item(
                Key={'article_id': article_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ConditionExpression=Attr('article_id').exists(),
                ReturnValues='ALL_NEW'
            )
            
            # Calculate queue position (approximate)
            queue_position = self._estimate_queue_position(priority_score)
            
            logger.info(f"Successfully added article {article_id} to review queue as {escalation_id}")
            
            return EscalationResult(
                success=True,
                operation="add_to_queue",
                article_id=article_id,
                escalation_id=escalation_id,
                priority_score=priority_score,
                queue_position=queue_position,
                metadata={
                    'escalated_at': now,
                    'escalation_reason': escalation_reason,
                    'context': context
                }
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConditionalCheckFailedException':
                return EscalationResult(
                    success=False,
                    operation="add_to_queue",
                    article_id=article_id,
                    errors=[f"Article {article_id} does not exist"]
                )
            else:
                logger.error(f"DynamoDB error adding to queue {article_id}: {e}")
                return EscalationResult(
                    success=False,
                    operation="add_to_queue",
                    article_id=article_id,
                    errors=[f"DynamoDB error: {str(e)}"]
                )
        except Exception as e:
            logger.error(f"Unexpected error adding to queue {article_id}: {e}")
            return EscalationResult(
                success=False,
                operation="add_to_queue",
                article_id=article_id,
                errors=[f"Unexpected error: {str(e)}"]
            )
    
    def _estimate_queue_position(self, priority_score: float) -> int:
        """Estimate position in queue based on priority score."""
        try:
            # Query items in REVIEW state with higher priority
            response = self.articles_table.query(
                IndexName='state-priority_score-index',
                KeyConditionExpression=Key('state').eq('REVIEW'),
                FilterExpression=Attr('priority_score').gt(Decimal(str(priority_score))),
                Select='COUNT'
            )
            
            return response.get('Count', 0) + 1
            
        except Exception as e:
            logger.warning(f"Error estimating queue position: {e}")
            return 1  # Default to position 1


class HumanEscalationTool:
    """Main human escalation tool orchestrating queue management and notifications."""
    
    def __init__(self, articles_table_name: str, sender_email: str, escalation_emails: List[str]):
        self.queue_manager = QueueManager(articles_table_name)
        self.notification_manager = NotificationManager(sender_email, escalation_emails)
    
    def escalate_article(self, article_id: str, escalation_reason: str, 
                        article_data: Optional[Dict[str, Any]] = None,
                        context: Optional[Dict[str, Any]] = None) -> EscalationResult:
        """Escalate article for human review."""
        try:
            logger.info(f"Escalating article {article_id} for reason: {escalation_reason}")
            
            # Get article data if not provided
            if not article_data:
                get_result = self._get_article_data(article_id)
                if not get_result.success:
                    return get_result
                article_data = get_result.metadata.get('article', {})
            
            # Calculate priority score
            priority_score = PriorityCalculator.calculate_priority_score(article_data, escalation_reason)
            
            # Prepare escalation context
            escalation_context = context or {}
            escalation_context.update({
                'escalation_reason': escalation_reason,
                'priority_score': priority_score,
                'escalated_by': 'system',
                'original_triage_action': article_data.get('triage_action'),
                'guardrail_flags': article_data.get('guardrail_flags', []),
                'confidence': article_data.get('confidence')
            })
            
            # Add to review queue
            queue_result = self.queue_manager.add_to_queue(
                article_id, escalation_reason, priority_score, escalation_context
            )
            
            if not queue_result.success:
                return queue_result
            
            # Send notification
            notification_sent = self.notification_manager.send_escalation_notification(
                article_data, escalation_reason, priority_score, queue_result.escalation_id
            )
            
            return EscalationResult(
                success=True,
                operation="escalate_article",
                article_id=article_id,
                escalation_id=queue_result.escalation_id,
                priority_score=priority_score,
                queue_position=queue_result.queue_position,
                notification_sent=notification_sent,
                metadata={
                    'escalation_reason': escalation_reason,
                    'context': escalation_context,
                    'notification_recipients': len(self.notification_manager.escalation_emails)
                }
            )
            
        except Exception as e:
            logger.error(f"Error escalating article {article_id}: {e}")
            return EscalationResult(
                success=False,
                operation="escalate_article",
                article_id=article_id,
                errors=[f"Escalation error: {str(e)}"]
            )
    
    def _get_article_data(self, article_id: str) -> EscalationResult:
        """Retrieve article data from DynamoDB."""
        try:
            response = self.queue_manager.articles_table.get_item(
                Key={'article_id': article_id}
            )
            
            if 'Item' not in response:
                return EscalationResult(
                    success=False,
                    operation="get_article_data",
                    article_id=article_id,
                    errors=[f"Article {article_id} not found"]
                )
            
            # Convert Decimal types back to float
            item = self._convert_from_dynamodb_types(response['Item'])
            
            return EscalationResult(
                success=True,
                operation="get_article_data",
                article_id=article_id,
                metadata={'article': item}
            )
            
        except Exception as e:
            logger.error(f"Error retrieving article data {article_id}: {e}")
            return EscalationResult(
                success=False,
                operation="get_article_data",
                article_id=article_id,
                errors=[f"Retrieval error: {str(e)}"]
            )
    
    def _convert_from_dynamodb_types(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB types back to Python types."""
        converted = {}
        for key, value in item.items():
            if isinstance(value, Decimal):
                converted[key] = float(value)
            elif isinstance(value, dict):
                converted[key] = self._convert_from_dynamodb_types(value)
            elif isinstance(value, list):
                converted[key] = [
                    self._convert_from_dynamodb_types(item) if isinstance(item, dict) 
                    else float(item) if isinstance(item, Decimal) 
                    else item 
                    for item in value
                ]
            else:
                converted[key] = value
        return converted


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for human escalation operations."""
    try:
        # Extract operation
        operation = event.get('operation', 'escalate_article')
        
        # Get configuration from environment
        articles_table = os.environ.get('ARTICLES_TABLE', 'sentinel-articles')
        sender_email = os.environ.get('SES_SENDER_EMAIL', 'noreply@sentinel.local')
        escalation_emails_str = os.environ.get('ESCALATION_EMAILS', '')
        escalation_emails = [email.strip() for email in escalation_emails_str.split(',') if email.strip()]
        
        # Initialize escalation tool
        escalation_tool = HumanEscalationTool(articles_table, sender_email, escalation_emails)
        
        # Route to appropriate operation
        if operation == 'escalate_article':
            article_id = event.get('article_id')
            escalation_reason = event.get('escalation_reason', 'manual_review_requested')
            article_data = event.get('article_data')
            context = event.get('context', {})
            
            if not article_id:
                raise ValueError("article_id is required for escalate_article")
            
            result = escalation_tool.escalate_article(article_id, escalation_reason, article_data, context)
            
        elif operation == 'calculate_priority':
            article_data = event.get('article_data', {})
            escalation_reason = event.get('escalation_reason', 'manual_review_requested')
            
            priority_score = PriorityCalculator.calculate_priority_score(article_data, escalation_reason)
            
            result = EscalationResult(
                success=True,
                operation="calculate_priority",
                priority_score=priority_score,
                metadata={'priority_score': priority_score}
            )
            
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        # Format response
        return {
            'statusCode': 200 if result.success else 400,
            'body': {
                'success': result.success,
                'operation': result.operation,
                'article_id': result.article_id,
                'escalation_id': result.escalation_id,
                'priority_score': result.priority_score,
                'queue_position': result.queue_position,
                'notification_sent': result.notification_sent,
                'errors': result.errors,
                'warnings': result.warnings,
                'metadata': result.metadata
            }
        }
        
    except Exception as e:
        logger.error(f"Human escalation operation failed: {e}")
        return {
            'statusCode': 500,
            'body': {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
        }


# For testing
if __name__ == "__main__":
    # Test event
    test_event = {
        "operation": "escalate_article",
        "article_id": "test-article-123",
        "escalation_reason": "guardrail_violation",
        "article_data": {
            "title": "Test Security Alert",
            "url": "https://example.com/alert",
            "source": "test-source",
            "published_at": "2024-01-01T12:00:00Z",
            "relevancy_score": 0.85,
            "keyword_matches": [{"keyword": "Azure", "hit_count": 2}],
            "entities": {"cves": ["CVE-2024-1234"], "vendors": ["Microsoft"]},
            "guardrail_flags": ["potential_pii"],
            "confidence": 0.7
        },
        "context": {
            "processing_agent": "ingestor-agent",
            "processing_timestamp": "2024-01-01T12:05:00Z"
        }
    }
    
    os.environ.update({
        'ARTICLES_TABLE': 'test-articles',
        'SES_SENDER_EMAIL': 'test@example.com',
        'ESCALATION_EMAILS': 'analyst1@example.com,analyst2@example.com'
    })
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))