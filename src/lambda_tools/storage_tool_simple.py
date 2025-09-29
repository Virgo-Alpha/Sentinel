"""
Simple StorageTool Lambda tool for testing basic functionality.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import uuid

import boto3
from botocore.exceptions import ClientError

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


class StorageTool:
    """Simple storage tool for basic operations."""
    
    def __init__(self, articles_table_name: str):
        self.articles_table = dynamodb.Table(articles_table_name)
    
    def create_article(self, article_data: Dict[str, Any]) -> StorageResult:
        """Create a new article in DynamoDB."""
        try:
            article_id = article_data.get('article_id')
            if not article_id:
                article_id = str(uuid.uuid4())
                article_data['article_id'] = article_id
            
            # Add timestamps
            now = datetime.utcnow().isoformat()
            article_data.update({
                'created_at': now,
                'updated_at': now,
                'version': 1
            })
            
            # Create article
            self.articles_table.put_item(Item=article_data)
            
            return StorageResult(
                success=True,
                operation="create_article",
                article_id=article_id,
                items_processed=1,
                metadata={'created_at': now}
            )
            
        except Exception as e:
            return StorageResult(
                success=False,
                operation="create_article",
                article_id=article_id,
                errors=[f"Error: {str(e)}"]
            )
    
    def get_article(self, article_id: str) -> StorageResult:
        """Retrieve an article from DynamoDB."""
        try:
            response = self.articles_table.get_item(Key={'article_id': article_id})
            
            if 'Item' not in response:
                return StorageResult(
                    success=False,
                    operation="get_article",
                    article_id=article_id,
                    errors=[f"Article {article_id} not found"]
                )
            
            return StorageResult(
                success=True,
                operation="get_article",
                article_id=article_id,
                items_processed=1,
                metadata={'article': response['Item']}
            )
            
        except Exception as e:
            return StorageResult(
                success=False,
                operation="get_article",
                article_id=article_id,
                errors=[f"Error: {str(e)}"]
            )


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for storage operations."""
    try:
        operation = event.get('operation')
        if not operation:
            raise ValueError("operation is required")
        
        # Get table name from environment
        import os
        articles_table = os.environ.get('ARTICLES_TABLE', 'sentinel-articles')
        
        # Initialize storage tool
        storage_tool = StorageTool(articles_table)
        
        # Route operations
        if operation == 'create_article':
            article_data = event.get('article_data', {})
            result = storage_tool.create_article(article_data)
        elif operation == 'get_article':
            article_id = event.get('article_id')
            if not article_id:
                raise ValueError("article_id is required")
            result = storage_tool.get_article(article_id)
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
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
        return {
            'statusCode': 500,
            'body': {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
        }


if __name__ == "__main__":
    # Test the basic functionality
    test_event = {
        "operation": "create_article",
        "article_data": {
            "title": "Test Article",
            "url": "https://example.com/test",
            "source": "test-source",
            "feed_id": "test-feed"
        }
    }
    
    import os
    os.environ['ARTICLES_TABLE'] = 'test-articles'
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))