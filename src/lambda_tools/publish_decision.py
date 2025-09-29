"""
PublishDecision Lambda tool for human approval/rejection processing.

This Lambda function handles human approval/rejection processing, state transitions,
downstream action triggering, audit trail creation, and batch decision processing
for the Sentinel cybersecurity triage system.
"""

import json
import logging
from datetime import datetime, timezone
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
eventbridge_client = boto3.client('events')


@dataclass
class DecisionResult:
    """Result of decision processing operations."""
    success: bool
    operation: str
    article_id: Optional[str] = None
    decision_id: Optional[str] = None
    decision: Optional[str] = None
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    downstream_actions: List[str] = None
    audit_trail_created: bool = False
    errors: List[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.downstream_actions is None:
            self.downstream_actions = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class BatchDecisionResult:
    """Result of batch decision processing."""
    total_items: int
    successful_decisions: int
    failed_decisions: int
    decisions: List[DecisionResult]
    processing_time_seconds: float
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class DecisionError(Exception):
    """Custom exception for decision processing errors."""
    pass


class StateTransitionManager:
    """Manages article state transitions based on decisions."""
    
    # Valid state transitions
    VALID_TRANSITIONS = {
        'REVIEW': ['PUBLISHED', 'ARCHIVED', 'REVIEW'],  # Can stay in review for edits
        'PUBLISHED': ['ARCHIVED'],  # Can only archive published items
        'ARCHIVED': []  # Terminal state
    }
    
    # Decision to state mapping
    DECISION_STATE_MAP = {
        'approve': 'PUBLISHED',
        'reject': 'ARCHIVED',
        'edit': 'REVIEW',  # Stay in review for further editing
        'escalate': 'REVIEW'  # Stay in review but escalate priority
    }
    
    @classmethod
    def validate_transition(cls, current_state: str, decision: str) -> bool:
        """Validate if state transition is allowed."""
        if current_state not in cls.VALID_TRANSITIONS:
            return False
        
        new_state = cls.DECISION_STATE_MAP.get(decision)
        if not new_state:
            return False
        
        return new_state in cls.VALID_TRANSITIONS[current_state]
    
    @classmethod
    def get_new_state(cls, decision: str) -> Optional[str]:
        """Get new state based on decision."""
        return cls.DECISION_STATE_MAP.get(decision)


class AuditTrailManager:
    """Manages audit trail creation for decisions."""
    
    def __init__(self, articles_table_name: str):
        self.articles_table = dynamodb.Table(articles_table_name)
    
    def create_audit_entry(self, article_id: str, decision_data: Dict[str, Any]) -> bool:
        """Create audit trail entry for decision."""
        try:
            audit_entry = {
                'audit_id': str(uuid.uuid4()),
                'article_id': article_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'action': 'human_decision',
                'decision': decision_data.get('decision'),
                'reviewer': decision_data.get('reviewer', 'unknown'),
                'previous_state': decision_data.get('previous_state'),
                'new_state': decision_data.get('new_state'),
                'rationale': decision_data.get('rationale', ''),
                'confidence': decision_data.get('confidence'),
                'tags_modified': decision_data.get('tags_modified', []),
                'summary_modified': decision_data.get('summary_modified', False),
                'processing_time_ms': decision_data.get('processing_time_ms', 0),
                'metadata': decision_data.get('metadata', {})
            }
            
            # Store audit entry in article's audit_trail list
            self.articles_table.update_item(
                Key={'article_id': article_id},
                UpdateExpression='SET audit_trail = list_append(if_not_exists(audit_trail, :empty_list), :audit_entry)',
                ExpressionAttributeValues={
                    ':empty_list': [],
                    ':audit_entry': [audit_entry]
                }
            )
            
            logger.info(f"Created audit trail entry for article {article_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating audit trail for {article_id}: {e}")
            return False


class DownstreamActionManager:
    """Manages downstream actions triggered by decisions."""
    
    def __init__(self, event_bus_name: Optional[str] = None):
        self.event_bus_name = event_bus_name or 'default'
    
    def trigger_downstream_actions(self, article_id: str, decision: str, 
                                 article_data: Dict[str, Any]) -> List[str]:
        """Trigger appropriate downstream actions based on decision."""
        actions_triggered = []
        
        try:
            if decision == 'approve':
                actions_triggered.extend(self._handle_approval_actions(article_id, article_data))
            elif decision == 'reject':
                actions_triggered.extend(self._handle_rejection_actions(article_id, article_data))
            elif decision == 'edit':
                actions_triggered.extend(self._handle_edit_actions(article_id, article_data))
            elif decision == 'escalate':
                actions_triggered.extend(self._handle_escalation_actions(article_id, article_data))
            
            return actions_triggered
            
        except Exception as e:
            logger.error(f"Error triggering downstream actions for {article_id}: {e}")
            return actions_triggered
    
    def _handle_approval_actions(self, article_id: str, article_data: Dict[str, Any]) -> List[str]:
        """Handle actions for approved articles."""
        actions = []
        
        try:
            # Publish to EventBridge for publication workflow
            event_detail = {
                'article_id': article_id,
                'action': 'publish_approved',
                'title': article_data.get('title', ''),
                'source': article_data.get('source', ''),
                'keyword_matches': article_data.get('keyword_matches', []),
                'priority_score': article_data.get('priority_score', 0.0),
                'approved_at': datetime.now(timezone.utc).isoformat()
            }
            
            eventbridge_client.put_events(
                Entries=[
                    {
                        'Source': 'sentinel.publish-decision',
                        'DetailType': 'Article Approved',
                        'Detail': json.dumps(event_detail),
                        'EventBusName': self.event_bus_name
                    }
                ]
            )
            actions.append('publication_event_sent')
            
            # Send notification to digest subscribers
            self._send_publication_notification(article_id, article_data)
            actions.append('publication_notification_sent')
            
        except Exception as e:
            logger.error(f"Error handling approval actions for {article_id}: {e}")
        
        return actions
    
    def _handle_rejection_actions(self, article_id: str, article_data: Dict[str, Any]) -> List[str]:
        """Handle actions for rejected articles."""
        actions = []
        
        try:
            # Archive content but keep for analysis
            event_detail = {
                'article_id': article_id,
                'action': 'archive_rejected',
                'rejection_reason': article_data.get('rejection_reason', 'manual_rejection'),
                'rejected_at': datetime.now(timezone.utc).isoformat()
            }
            
            eventbridge_client.put_events(
                Entries=[
                    {
                        'Source': 'sentinel.publish-decision',
                        'DetailType': 'Article Rejected',
                        'Detail': json.dumps(event_detail),
                        'EventBusName': self.event_bus_name
                    }
                ]
            )
            actions.append('archival_event_sent')
            
        except Exception as e:
            logger.error(f"Error handling rejection actions for {article_id}: {e}")
        
        return actions
    
    def _handle_edit_actions(self, article_id: str, article_data: Dict[str, Any]) -> List[str]:
        """Handle actions for articles requiring edits."""
        actions = []
        
        try:
            # Keep in review queue but update priority if needed
            event_detail = {
                'article_id': article_id,
                'action': 'update_for_edit',
                'edit_requested_at': datetime.now(timezone.utc).isoformat(),
                'edit_instructions': article_data.get('edit_instructions', '')
            }
            
            eventbridge_client.put_events(
                Entries=[
                    {
                        'Source': 'sentinel.publish-decision',
                        'DetailType': 'Article Edit Requested',
                        'Detail': json.dumps(event_detail),
                        'EventBusName': self.event_bus_name
                    }
                ]
            )
            actions.append('edit_event_sent')
            
        except Exception as e:
            logger.error(f"Error handling edit actions for {article_id}: {e}")
        
        return actions
    
    def _handle_escalation_actions(self, article_id: str, article_data: Dict[str, Any]) -> List[str]:
        """Handle actions for escalated articles."""
        actions = []
        
        try:
            # Escalate to higher priority or different reviewer group
            event_detail = {
                'article_id': article_id,
                'action': 'escalate_priority',
                'escalated_at': datetime.now(timezone.utc).isoformat(),
                'escalation_reason': article_data.get('escalation_reason', 'manual_escalation')
            }
            
            eventbridge_client.put_events(
                Entries=[
                    {
                        'Source': 'sentinel.publish-decision',
                        'DetailType': 'Article Escalated',
                        'Detail': json.dumps(event_detail),
                        'EventBusName': self.event_bus_name
                    }
                ]
            )
            actions.append('escalation_event_sent')
            
        except Exception as e:
            logger.error(f"Error handling escalation actions for {article_id}: {e}")
        
        return actions
    
    def _send_publication_notification(self, article_id: str, article_data: Dict[str, Any]):
        """Send notification about published article."""
        try:
            # This would integrate with the notification system
            # For now, just log the action
            logger.info(f"Publication notification would be sent for article {article_id}")
            
        except Exception as e:
            logger.error(f"Error sending publication notification for {article_id}: {e}")


class DecisionProcessor:
    """Main decision processing logic."""
    
    def __init__(self, articles_table_name: str, event_bus_name: Optional[str] = None):
        self.articles_table = dynamodb.Table(articles_table_name)
        self.audit_manager = AuditTrailManager(articles_table_name)
        self.action_manager = DownstreamActionManager(event_bus_name)
    
    def process_decision(self, article_id: str, decision: str, reviewer: str,
                        rationale: Optional[str] = None, 
                        modifications: Optional[Dict[str, Any]] = None) -> DecisionResult:
        """Process a human decision on an article."""
        try:
            start_time = datetime.now(timezone.utc)
            decision_id = str(uuid.uuid4())
            
            logger.info(f"Processing decision {decision} for article {article_id} by {reviewer}")
            
            # Get current article state
            article_response = self.articles_table.get_item(Key={'article_id': article_id})
            if 'Item' not in article_response:
                return DecisionResult(
                    success=False,
                    operation="process_decision",
                    article_id=article_id,
                    errors=[f"Article {article_id} not found"]
                )
            
            article_data = self._convert_from_dynamodb_types(article_response['Item'])
            current_state = article_data.get('state', 'UNKNOWN')
            
            # Validate decision and state transition
            if not StateTransitionManager.validate_transition(current_state, decision):
                return DecisionResult(
                    success=False,
                    operation="process_decision",
                    article_id=article_id,
                    errors=[f"Invalid transition from {current_state} with decision {decision}"]
                )
            
            new_state = StateTransitionManager.get_new_state(decision)
            
            # Prepare update data
            update_data = {
                'state': new_state,
                'decision': decision,
                'reviewer': reviewer,
                'reviewed_at': start_time.isoformat(),
                'decision_id': decision_id,
                'rationale': rationale or '',
                'updated_at': start_time.isoformat()
            }
            
            # Apply modifications if provided
            if modifications:
                if 'tags' in modifications:
                    update_data['tags'] = modifications['tags']
                    update_data['tags_modified'] = True
                
                if 'summary_short' in modifications:
                    update_data['summary_short'] = modifications['summary_short']
                    update_data['summary_modified'] = True
                
                if 'summary_card' in modifications:
                    update_data['summary_card'] = modifications['summary_card']
                    update_data['summary_modified'] = True
                
                if 'confidence' in modifications:
                    update_data['confidence'] = modifications['confidence']
            
            # Update article in DynamoDB
            update_result = self._update_article_with_decision(article_id, update_data)
            if not update_result:
                return DecisionResult(
                    success=False,
                    operation="process_decision",
                    article_id=article_id,
                    errors=["Failed to update article with decision"]
                )
            
            # Create audit trail
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            audit_data = {
                'decision': decision,
                'reviewer': reviewer,
                'previous_state': current_state,
                'new_state': new_state,
                'rationale': rationale or '',
                'confidence': update_data.get('confidence'),
                'tags_modified': update_data.get('tags_modified', False),
                'summary_modified': update_data.get('summary_modified', False),
                'processing_time_ms': processing_time,
                'metadata': modifications or {}
            }
            
            audit_created = self.audit_manager.create_audit_entry(article_id, audit_data)
            
            # Trigger downstream actions
            downstream_actions = self.action_manager.trigger_downstream_actions(
                article_id, decision, article_data
            )
            
            return DecisionResult(
                success=True,
                operation="process_decision",
                article_id=article_id,
                decision_id=decision_id,
                decision=decision,
                previous_state=current_state,
                new_state=new_state,
                downstream_actions=downstream_actions,
                audit_trail_created=audit_created,
                metadata={
                    'reviewer': reviewer,
                    'processing_time_ms': processing_time,
                    'modifications_applied': bool(modifications)
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing decision for {article_id}: {e}")
            return DecisionResult(
                success=False,
                operation="process_decision",
                article_id=article_id,
                errors=[f"Processing error: {str(e)}"]
            )
    
    def process_batch_decisions(self, decisions: List[Dict[str, Any]]) -> BatchDecisionResult:
        """Process multiple decisions in batch."""
        start_time = datetime.now(timezone.utc)
        results = []
        successful = 0
        failed = 0
        
        logger.info(f"Processing batch of {len(decisions)} decisions")
        
        for decision_data in decisions:
            try:
                article_id = decision_data.get('article_id')
                decision = decision_data.get('decision')
                reviewer = decision_data.get('reviewer')
                rationale = decision_data.get('rationale')
                modifications = decision_data.get('modifications')
                
                if not all([article_id, decision, reviewer]):
                    result = DecisionResult(
                        success=False,
                        operation="process_batch_decisions",
                        article_id=article_id,
                        errors=["Missing required fields: article_id, decision, reviewer"]
                    )
                    results.append(result)
                    failed += 1
                    continue
                
                result = self.process_decision(article_id, decision, reviewer, rationale, modifications)
                results.append(result)
                
                if result.success:
                    successful += 1
                else:
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Error in batch processing: {e}")
                result = DecisionResult(
                    success=False,
                    operation="process_batch_decisions",
                    errors=[f"Batch processing error: {str(e)}"]
                )
                results.append(result)
                failed += 1
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        return BatchDecisionResult(
            total_items=len(decisions),
            successful_decisions=successful,
            failed_decisions=failed,
            decisions=results,
            processing_time_seconds=processing_time
        )
    
    def _update_article_with_decision(self, article_id: str, update_data: Dict[str, Any]) -> bool:
        """Update article with decision data."""
        try:
            # Build update expression
            update_expression_parts = []
            expression_attribute_names = {}
            expression_attribute_values = {}
            
            for key, value in update_data.items():
                attr_name = f"#{key}"
                attr_value = f":{key}"
                
                update_expression_parts.append(f"{attr_name} = {attr_value}")
                expression_attribute_names[attr_name] = key
                expression_attribute_values[attr_value] = self._convert_to_dynamodb_type(value)
            
            update_expression = "SET " + ", ".join(update_expression_parts)
            
            self.articles_table.update_item(
                Key={'article_id': article_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ConditionExpression=Attr('article_id').exists()
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating article {article_id}: {e}")
            return False
    
    def _convert_to_dynamodb_type(self, value: Any) -> Any:
        """Convert Python types to DynamoDB compatible types."""
        if isinstance(value, float):
            return Decimal(str(value))
        elif isinstance(value, dict):
            return {k: self._convert_to_dynamodb_type(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._convert_to_dynamodb_type(item) for item in value]
        else:
            return value
    
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
    """Lambda handler for publish decision operations."""
    try:
        # Extract operation
        operation = event.get('operation', 'process_decision')
        
        # Get configuration from environment
        articles_table = os.environ.get('ARTICLES_TABLE', 'sentinel-articles')
        event_bus_name = os.environ.get('EVENT_BUS_NAME', 'default')
        
        # Initialize decision processor
        processor = DecisionProcessor(articles_table, event_bus_name)
        
        # Route to appropriate operation
        if operation == 'process_decision':
            article_id = event.get('article_id')
            decision = event.get('decision')
            reviewer = event.get('reviewer')
            rationale = event.get('rationale')
            modifications = event.get('modifications')
            
            if not all([article_id, decision, reviewer]):
                raise ValueError("article_id, decision, and reviewer are required")
            
            result = processor.process_decision(article_id, decision, reviewer, rationale, modifications)
            
            return {
                'statusCode': 200 if result.success else 400,
                'body': {
                    'success': result.success,
                    'operation': result.operation,
                    'article_id': result.article_id,
                    'decision_id': result.decision_id,
                    'decision': result.decision,
                    'previous_state': result.previous_state,
                    'new_state': result.new_state,
                    'downstream_actions': result.downstream_actions,
                    'audit_trail_created': result.audit_trail_created,
                    'errors': result.errors,
                    'warnings': result.warnings,
                    'metadata': result.metadata
                }
            }
            
        elif operation == 'process_batch_decisions':
            decisions = event.get('decisions', [])
            
            if not decisions:
                raise ValueError("decisions list is required for batch processing")
            
            result = processor.process_batch_decisions(decisions)
            
            return {
                'statusCode': 200,
                'body': {
                    'success': True,
                    'operation': 'process_batch_decisions',
                    'total_items': result.total_items,
                    'successful_decisions': result.successful_decisions,
                    'failed_decisions': result.failed_decisions,
                    'processing_time_seconds': result.processing_time_seconds,
                    'decisions': [
                        {
                            'success': d.success,
                            'article_id': d.article_id,
                            'decision': d.decision,
                            'errors': d.errors
                        } for d in result.decisions
                    ],
                    'errors': result.errors,
                    'warnings': result.warnings
                }
            }
            
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
    except Exception as e:
        logger.error(f"Publish decision operation failed: {e}")
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
        "operation": "process_decision",
        "article_id": "test-article-123",
        "decision": "approve",
        "reviewer": "analyst@example.com",
        "rationale": "Article contains relevant security information about Azure vulnerabilities",
        "modifications": {
            "tags": ["azure", "vulnerability", "critical"],
            "confidence": 0.9
        }
    }
    
    os.environ.update({
        'ARTICLES_TABLE': 'test-articles',
        'EVENT_BUS_NAME': 'test-event-bus'
    })
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))