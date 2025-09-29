"""
StorageTool Lambda tool for DynamoDB and S3 operations.

This Lambda function handles article creation, updates, state management,
batch operations for performance optimization, data consistency checks,
and comprehensive error handling for the Sentinel cybersecurity triage system.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from decimal import Decimal
import uuid

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')


@dataclass
class StorageResult:
    """Result of storage operations."""
    success: bool
    operation: str
    article_id: Optional[str] = None
    items_processed: int = 0
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


@dataclass
class BatchOperationResult:
    """Result of batch operations."""
    total_items: int
    successful_items: int
    failed_items: int
    errors: List[Dict[str, Any]]
    warnings: List[str]
    processing_time_seconds: float
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class StorageToolError(Exception):
    """Custom exception for storage tool errors."""
    pass


class DataConsistencyError(Exception):
    """Exception for data consistency violations."""
    pass


class DynamoDBManager:
    """Handles DynamoDB operations with consistency checks and error handling."""
    
    def __init__(self, articles_table_name: str, comments_table_name: str, memory_table_name: str):
        self.articles_table = dynamodb.Table(articles_table_name)
        self.comments_table = dynamodb.Table(comments_table_name)
        self.memory_table = dynamodb.Table(memory_table_name)
        
        # Batch operation limits
        self.max_batch_write_items = 25
        self.max_batch_get_items = 100
    
    def create_article(self, article_data: Dict[str, Any]) -> StorageResult:
        """Create a new article in DynamoDB."""
        try:
            article_id = article_data.get('article_id')
            if not article_id:
                article_id = str(uuid.uuid4())
                article_data['article_id'] = article_id
            
            logger.info(f"Creating article: {article_id}")
            
            # Validate required fields
            validation_result = self._validate_article_data(article_data)
            if not validation_result.success:
                return validation_result
            
            # Prepare item for DynamoDB
            item = self._prepare_dynamodb_item(article_data)
            
            # Add audit fields
            now = datetime.now(timezone.utc).isoformat()
            item.update({
                'created_at': now,
                'updated_at': now,
                'version': 1
            })
            
            # Create article with condition to prevent overwrites
            self.articles_table.put_item(
                Item=item,
                ConditionExpression=Attr('article_id').not_exists()
            )
            
            logger.info(f"Successfully created article: {article_id}")
            return StorageResult(
                success=True,
                operation="create_article",
                article_id=article_id,
                items_processed=1,
                metadata={'created_at': now}
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConditionalCheckFailedException':
                return StorageResult(
                    success=False,
                    operation="create_article",
                    article_id=article_id,
                    errors=[f"Article {article_id} already exists"]
                )
            else:
                logger.error(f"DynamoDB error creating article {article_id}: {e}")
                return StorageResult(
                    success=False,
                    operation="create_article",
                    article_id=article_id,
                    errors=[f"DynamoDB error: {str(e)}"]
                )
        except Exception as e:
            logger.error(f"Unexpected error creating article {article_id}: {e}")
            return StorageResult(
                success=False,
                operation="create_article",
                article_id=article_id,
                errors=[f"Unexpected error: {str(e)}"]
            )
    
    def update_article(self, article_id: str, updates: Dict[str, Any], 
                      increment_version: bool = True) -> StorageResult:
        """Update an existing article in DynamoDB."""
        try:
            logger.info(f"Updating article: {article_id}")
            
            if not updates:
                return StorageResult(
                    success=False,
                    operation="update_article",
                    article_id=article_id,
                    errors=["No updates provided"]
                )
            
            # Prepare update expression
            update_expression_parts = []
            expression_attribute_names = {}
            expression_attribute_values = {}
            
            # Add updated_at timestamp
            updates['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            for key, value in updates.items():
                # Handle reserved keywords
                attr_name = f"#{key}"
                attr_value = f":{key}"
                
                update_expression_parts.append(f"{attr_name} = {attr_value}")
                expression_attribute_names[attr_name] = key
                expression_attribute_values[attr_value] = self._convert_to_dynamodb_type(value)
            
            # Increment version if requested
            if increment_version:
                update_expression_parts.append("#version = #version + :version_inc")
                expression_attribute_names["#version"] = "version"
                expression_attribute_values[":version_inc"] = 1
            
            update_expression = "SET " + ", ".join(update_expression_parts)
            
            # Perform update with condition that article exists
            response = self.articles_table.update_item(
                Key={'article_id': article_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ConditionExpression=Attr('article_id').exists(),
                ReturnValues='ALL_NEW'
            )
            
            logger.info(f"Successfully updated article: {article_id}")
            return StorageResult(
                success=True,
                operation="update_article",
                article_id=article_id,
                items_processed=1,
                metadata={
                    'updated_fields': list(updates.keys()),
                    'new_version': response['Attributes'].get('version', 1)
                }
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConditionalCheckFailedException':
                return StorageResult(
                    success=False,
                    operation="update_article",
                    article_id=article_id,
                    errors=[f"Article {article_id} does not exist"]
                )
            else:
                logger.error(f"DynamoDB error updating article {article_id}: {e}")
                return StorageResult(
                    success=False,
                    operation="update_article",
                    article_id=article_id,
                    errors=[f"DynamoDB error: {str(e)}"]
                )
        except Exception as e:
            logger.error(f"Unexpected error updating article {article_id}: {e}")
            return StorageResult(
                success=False,
                operation="update_article",
                article_id=article_id,
                errors=[f"Unexpected error: {str(e)}"]
            )
    
    def get_article(self, article_id: str, consistent_read: bool = False) -> StorageResult:
        """Retrieve an article from DynamoDB."""
        try:
            logger.info(f"Retrieving article: {article_id}")
            
            response = self.articles_table.get_item(
                Key={'article_id': article_id},
                ConsistentRead=consistent_read
            )
            
            if 'Item' not in response:
                return StorageResult(
                    success=False,
                    operation="get_article",
                    article_id=article_id,
                    errors=[f"Article {article_id} not found"]
                )
            
            item = self._convert_from_dynamodb_types(response['Item'])
            
            return StorageResult(
                success=True,
                operation="get_article",
                article_id=article_id,
                items_processed=1,
                metadata={'article': item}
            )
            
        except ClientError as e:
            logger.error(f"DynamoDB error retrieving article {article_id}: {e}")
            return StorageResult(
                success=False,
                operation="get_article",
                article_id=article_id,
                errors=[f"DynamoDB error: {str(e)}"]
            )
        except Exception as e:
            logger.error(f"Unexpected error retrieving article {article_id}: {e}")
            return StorageResult(
                success=False,
                operation="get_article",
                article_id=article_id,
                errors=[f"Unexpected error: {str(e)}"]
            )
    
    def update_article_state(self, article_id: str, new_state: str, 
                           metadata: Optional[Dict[str, Any]] = None) -> StorageResult:
        """Update article state with optional metadata."""
        try:
            logger.info(f"Updating article state: {article_id} -> {new_state}")
            
            # Validate state
            valid_states = ['INGESTED', 'PROCESSED', 'PUBLISHED', 'ARCHIVED', 'REVIEW']
            if new_state not in valid_states:
                return StorageResult(
                    success=False,
                    operation="update_article_state",
                    article_id=article_id,
                    errors=[f"Invalid state: {new_state}. Valid states: {valid_states}"]
                )
            
            updates = {
                'state': new_state,
                'state_updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            if metadata:
                updates.update(metadata)
            
            return self.update_article(article_id, updates)
            
        except Exception as e:
            logger.error(f"Error updating article state {article_id}: {e}")
            return StorageResult(
                success=False,
                operation="update_article_state",
                article_id=article_id,
                errors=[f"State update error: {str(e)}"]
            )
    
    def _validate_article_data(self, article_data: Dict[str, Any]) -> StorageResult:
        """Validate article data before storage."""
        required_fields = ['title', 'url', 'source', 'feed_id']
        missing_fields = []
        
        for field in required_fields:
            if not article_data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            return StorageResult(
                success=False,
                operation="validate_article_data",
                errors=[f"Missing required fields: {missing_fields}"]
            )
        
        # Validate URL format
        url = article_data.get('url', '')
        if not (url.startswith('http://') or url.startswith('https://')):
            return StorageResult(
                success=False,
                operation="validate_article_data",
                errors=["Invalid URL format"]
            )
        
        return StorageResult(success=True, operation="validate_article_data")
    
    def _prepare_dynamodb_item(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for DynamoDB storage."""
        item = {}
        for key, value in data.items():
            item[key] = self._convert_to_dynamodb_type(value)
        return item
    
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


class S3Manager:
    """Handles S3 operations for content storage."""
    
    def __init__(self, content_bucket: str, artifacts_bucket: str, traces_bucket: str):
        self.content_bucket = content_bucket
        self.artifacts_bucket = artifacts_bucket
        self.traces_bucket = traces_bucket
    
    def store_content(self, content: Union[str, bytes], key: str, 
                     bucket: Optional[str] = None, content_type: str = 'text/plain') -> StorageResult:
        """Store content in S3."""
        try:
            bucket = bucket or self.content_bucket
            logger.info(f"Storing content to S3: s3://{bucket}/{key}")
            
            # Prepare content
            if isinstance(content, str):
                body = content.encode('utf-8')
            else:
                body = content
            
            # Store in S3
            s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
                ServerSideEncryption='AES256'
            )
            
            s3_uri = f"s3://{bucket}/{key}"
            
            logger.info(f"Successfully stored content: {s3_uri}")
            return StorageResult(
                success=True,
                operation="store_content",
                items_processed=1,
                metadata={'s3_uri': s3_uri, 'size_bytes': len(body)}
            )
            
        except ClientError as e:
            logger.error(f"S3 error storing content: {e}")
            return StorageResult(
                success=False,
                operation="store_content",
                errors=[f"S3 error: {str(e)}"]
            )
        except Exception as e:
            logger.error(f"Unexpected error storing content: {e}")
            return StorageResult(
                success=False,
                operation="store_content",
                errors=[f"Unexpected error: {str(e)}"]
            )


class StorageTool:
    """Main storage tool orchestrating DynamoDB and S3 operations."""
    
    def __init__(self, articles_table_name: str, comments_table_name: str, 
                 memory_table_name: str, content_bucket: str, 
                 artifacts_bucket: str, traces_bucket: str):
        self.dynamodb_manager = DynamoDBManager(
            articles_table_name, comments_table_name, memory_table_name
        )
        self.s3_manager = S3Manager(content_bucket, artifacts_bucket, traces_bucket)
    
    def store_article(self, article_data: Dict[str, Any]) -> StorageResult:
        """Store complete article with content and metadata."""
        try:
            article_id = article_data.get('article_id')
            logger.info(f"Storing complete article: {article_id}")
            
            # Store article in DynamoDB
            db_result = self.dynamodb_manager.create_article(article_data)
            if not db_result.success:
                return db_result
            
            # Store additional content in S3 if provided
            s3_operations = []
            
            # Store raw content
            raw_content = article_data.get('raw_content')
            if raw_content:
                key = f"raw/{article_data.get('feed_id', 'unknown')}/{article_id}.html"
                s3_result = self.s3_manager.store_content(
                    raw_content, key, content_type='text/html'
                )
                if s3_result.success:
                    s3_operations.append(s3_result.metadata['s3_uri'])
                    # Update article with S3 URI
                    self.dynamodb_manager.update_article(
                        article_id, {'raw_s3_uri': s3_result.metadata['s3_uri']}, 
                        increment_version=False
                    )
            
            return StorageResult(
                success=True,
                operation="store_article",
                article_id=article_id,
                items_processed=1,
                metadata={
                    'dynamodb_stored': True,
                    's3_operations': len(s3_operations),
                    's3_uris': s3_operations
                }
            )
            
        except Exception as e:
            logger.error(f"Error storing article {article_id}: {e}")
            return StorageResult(
                success=False,
                operation="store_article",
                article_id=article_id,
                errors=[f"Storage error: {str(e)}"]
            )


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for storage operations."""
    try:
        # Extract operation
        operation = event.get('operation')
        if not operation:
            raise ValueError("operation is required")
        
        # Get configuration from environment
        import os
        articles_table = os.environ.get('ARTICLES_TABLE', 'sentinel-articles')
        comments_table = os.environ.get('COMMENTS_TABLE', 'sentinel-comments')
        memory_table = os.environ.get('MEMORY_TABLE', 'sentinel-memory')
        content_bucket = os.environ.get('CONTENT_BUCKET', 'sentinel-content')
        artifacts_bucket = os.environ.get('ARTIFACTS_BUCKET', 'sentinel-artifacts')
        traces_bucket = os.environ.get('TRACES_BUCKET', 'sentinel-traces')
        
        # Initialize storage tool
        storage_tool = StorageTool(
            articles_table, comments_table, memory_table,
            content_bucket, artifacts_bucket, traces_bucket
        )
        
        # Route to appropriate operation
        if operation == 'create_article':
            article_data = event.get('article_data', {})
            result = storage_tool.dynamodb_manager.create_article(article_data)
            
        elif operation == 'store_article':
            article_data = event.get('article_data', {})
            result = storage_tool.store_article(article_data)
            
        elif operation == 'update_article':
            article_id = event.get('article_id')
            updates = event.get('updates', {})
            if not article_id:
                raise ValueError("article_id is required for update_article")
            result = storage_tool.dynamodb_manager.update_article(article_id, updates)
            
        elif operation == 'get_article':
            article_id = event.get('article_id')
            consistent_read = event.get('consistent_read', False)
            if not article_id:
                raise ValueError("article_id is required for get_article")
            result = storage_tool.dynamodb_manager.get_article(article_id, consistent_read)
            
        elif operation == 'update_state':
            article_id = event.get('article_id')
            new_state = event.get('state')
            metadata = event.get('metadata', {})
            if not article_id or not new_state:
                raise ValueError("article_id and state are required for update_state")
            result = storage_tool.dynamodb_manager.update_article_state(article_id, new_state, metadata)
            
        elif operation == 'store_content':
            content = event.get('content', '')
            key = event.get('key', '')
            bucket = event.get('bucket')
            content_type = event.get('content_type', 'text/plain')
            if not content or not key:
                raise ValueError("content and key are required for store_content")
            result = storage_tool.s3_manager.store_content(content, key, bucket, content_type)
            
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        # Format response
        return {
            'statusCode': 200 if result.success else 400,
            'body': {
                'success': result.success,
                'operation': result.operation,
                'article_id': result.article_id,
                'items_processed': result.items_processed,
                'errors': result.errors,
                'warnings': result.warnings,
                'metadata': result.metadata
            }
        }
        
    except Exception as e:
        logger.error(f"Storage tool operation failed: {e}")
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
        "operation": "create_article",
        "article_data": {
            "title": "Test Article",
            "url": "https://example.com/test",
            "source": "test-source",
            "feed_id": "test-feed",
            "published_at": "2024-01-01T00:00:00Z",
            "content_hash": "test-hash",
            "normalized_content": "Test content"
        }
    }
    
    import os
    os.environ.update({
        'ARTICLES_TABLE': 'test-articles',
        'COMMENTS_TABLE': 'test-comments',
        'MEMORY_TABLE': 'test-memory',
        'CONTENT_BUCKET': 'test-content',
        'ARTIFACTS_BUCKET': 'test-artifacts',
        'TRACES_BUCKET': 'test-traces'
    })
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))