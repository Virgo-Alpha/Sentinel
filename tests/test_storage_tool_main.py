"""
Unit tests for the main StorageTool Lambda function.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_tools.storage_tool import (
    StorageResult, BatchOperationResult, DynamoDBManager, S3Manager, 
    StorageTool, lambda_handler
)


class TestStorageResult:
    """Test StorageResult dataclass."""
    
    def test_storage_result_initialization(self):
        """Test StorageResult initialization with defaults."""
        result = StorageResult(success=True, operation="test")
        
        assert result.success is True
        assert result.operation == "test"
        assert result.article_id is None
        assert result.items_processed == 0
        assert result.errors == []
        assert result.warnings == []
        assert result.metadata == {}
    
    def test_storage_result_with_data(self):
        """Test StorageResult with all fields populated."""
        result = StorageResult(
            success=False,
            operation="create_article",
            article_id="test-123",
            items_processed=1,
            errors=["Test error"],
            warnings=["Test warning"],
            metadata={"key": "value"}
        )
        
        assert result.success is False
        assert result.operation == "create_article"
        assert result.article_id == "test-123"
        assert result.items_processed == 1
        assert result.errors == ["Test error"]
        assert result.warnings == ["Test warning"]
        assert result.metadata == {"key": "value"}


class TestBatchOperationResult:
    """Test BatchOperationResult dataclass."""
    
    def test_batch_result_initialization(self):
        """Test BatchOperationResult initialization."""
        result = BatchOperationResult(
            total_items=10,
            successful_items=8,
            failed_items=2,
            errors=[],
            warnings=[],
            processing_time_seconds=1.5
        )
        
        assert result.total_items == 10
        assert result.successful_items == 8
        assert result.failed_items == 2
        assert result.errors == []
        assert result.warnings == []
        assert result.processing_time_seconds == 1.5


class TestDynamoDBManager:
    """Test DynamoDBManager class with mocked AWS services."""
    
    @pytest.fixture
    def setup_dynamodb_manager(self):
        """Set up DynamoDBManager with mocked tables."""
        with patch('lambda_tools.storage_tool.dynamodb') as mock_dynamodb:
            mock_articles_table = Mock()
            mock_comments_table = Mock()
            mock_memory_table = Mock()
            
            mock_dynamodb.Table.side_effect = lambda name: {
                'test-articles': mock_articles_table,
                'test-comments': mock_comments_table,
                'test-memory': mock_memory_table
            }[name]
            
            manager = DynamoDBManager('test-articles', 'test-comments', 'test-memory')
            
            return manager, mock_articles_table, mock_comments_table, mock_memory_table
    
    def test_create_article_success(self, setup_dynamodb_manager):
        """Test successful article creation."""
        manager, mock_articles_table, _, _ = setup_dynamodb_manager
        
        article_data = {
            'title': 'Test Article',
            'url': 'https://example.com/test',
            'source': 'test-source',
            'feed_id': 'test-feed'
        }
        
        # Mock successful put_item
        mock_articles_table.put_item.return_value = {}
        
        result = manager.create_article(article_data)
        
        assert result.success is True
        assert result.operation == "create_article"
        assert result.article_id is not None
        assert result.items_processed == 1
        assert 'created_at' in result.metadata
        
        # Verify put_item was called
        mock_articles_table.put_item.assert_called_once()
    
    def test_create_article_missing_fields(self, setup_dynamodb_manager):
        """Test article creation with missing required fields."""
        manager, _, _, _ = setup_dynamodb_manager
        
        article_data = {
            'title': 'Test Article'
            # Missing url, source, feed_id
        }
        
        result = manager.create_article(article_data)
        
        assert result.success is False
        assert result.operation == "validate_article_data"
        assert "Missing required fields" in result.errors[0]
    
    def test_create_article_invalid_url(self, setup_dynamodb_manager):
        """Test article creation with invalid URL."""
        manager, _, _, _ = setup_dynamodb_manager
        
        article_data = {
            'title': 'Test Article',
            'url': 'invalid-url',
            'source': 'test-source',
            'feed_id': 'test-feed'
        }
        
        result = manager.create_article(article_data)
        
        assert result.success is False
        assert "Invalid URL format" in result.errors[0]
    
    def test_update_article_success(self, setup_dynamodb_manager):
        """Test successful article update."""
        manager, mock_articles_table, _, _ = setup_dynamodb_manager
        
        # Mock successful update_item
        mock_articles_table.update_item.return_value = {
            'Attributes': {'version': 2}
        }
        
        updates = {
            'state': 'PROCESSED',
            'relevancy_score': 0.85
        }
        
        result = manager.update_article('test-123', updates)
        
        assert result.success is True
        assert result.operation == "update_article"
        assert result.article_id == 'test-123'
        assert 'updated_fields' in result.metadata
        assert 'new_version' in result.metadata
        
        # Verify update_item was called
        mock_articles_table.update_item.assert_called_once()
    
    def test_get_article_success(self, setup_dynamodb_manager):
        """Test successful article retrieval."""
        manager, mock_articles_table, _, _ = setup_dynamodb_manager
        
        # Mock successful get_item
        mock_articles_table.get_item.return_value = {
            'Item': {
                'article_id': 'test-123',
                'title': 'Test Article',
                'url': 'https://example.com/test'
            }
        }
        
        result = manager.get_article('test-123')
        
        assert result.success is True
        assert result.operation == "get_article"
        assert result.article_id == 'test-123'
        assert 'article' in result.metadata
        assert result.metadata['article']['title'] == 'Test Article'
        
        # Verify get_item was called
        mock_articles_table.get_item.assert_called_once()
    
    def test_get_nonexistent_article(self, setup_dynamodb_manager):
        """Test retrieving a non-existent article."""
        manager, mock_articles_table, _, _ = setup_dynamodb_manager
        
        # Mock get_item returning no item
        mock_articles_table.get_item.return_value = {}
        
        result = manager.get_article('nonexistent-123')
        
        assert result.success is False
        assert "not found" in result.errors[0]
    
    def test_update_article_state_success(self, setup_dynamodb_manager):
        """Test successful article state update."""
        manager, mock_articles_table, _, _ = setup_dynamodb_manager
        
        # Mock successful update_item
        mock_articles_table.update_item.return_value = {
            'Attributes': {'version': 2}
        }
        
        result = manager.update_article_state('test-123', 'PROCESSED')
        
        assert result.success is True
        assert result.operation == "update_article"
    
    def test_update_article_state_invalid(self, setup_dynamodb_manager):
        """Test article state update with invalid state."""
        manager, _, _, _ = setup_dynamodb_manager
        
        result = manager.update_article_state('test-123', 'INVALID_STATE')
        
        assert result.success is False
        assert "Invalid state" in result.errors[0]
    
    def test_convert_dynamodb_types(self, setup_dynamodb_manager):
        """Test DynamoDB type conversion methods."""
        manager, _, _, _ = setup_dynamodb_manager
        
        # Test conversion to DynamoDB types
        data = {
            'string_field': 'test',
            'float_field': 3.14,
            'dict_field': {'nested': 2.71},
            'list_field': [1.41, {'nested': 1.73}]
        }
        
        converted = manager._convert_to_dynamodb_type(data)
        
        from decimal import Decimal
        assert isinstance(converted['float_field'], Decimal)
        assert isinstance(converted['dict_field']['nested'], Decimal)
        assert isinstance(converted['list_field'][0], Decimal)
        
        # Test conversion from DynamoDB types
        back_converted = manager._convert_from_dynamodb_types(converted)
        
        assert isinstance(back_converted['float_field'], float)
        assert isinstance(back_converted['dict_field']['nested'], float)
        assert isinstance(back_converted['list_field'][0], float)


@patch('lambda_tools.storage_tool.s3_client')
class TestS3Manager:
    """Test S3Manager class with mocked AWS services."""
    
    def test_store_content_success(self, mock_s3_client):
        """Test successful content storage in S3."""
        # Configure the mock
        mock_s3_client.put_object.return_value = {}
        
        manager = S3Manager('test-content', 'test-artifacts', 'test-traces')
        
        content = "This is test content"
        key = "test/content.txt"
        
        result = manager.store_content(content, key)
        
        assert result.success is True
        assert result.operation == "store_content"
        assert result.items_processed == 1
        assert 's3_uri' in result.metadata
        assert result.metadata['s3_uri'] == f"s3://test-content/{key}"
        assert 'size_bytes' in result.metadata
        
        # Verify put_object was called
        mock_s3_client.put_object.assert_called_once()
    
    def test_store_content_bytes(self, mock_s3_client):
        """Test storing bytes content in S3."""
        # Configure the mock
        mock_s3_client.put_object.return_value = {}
        
        manager = S3Manager('test-content', 'test-artifacts', 'test-traces')
        
        content = b"This is test content as bytes"
        key = "test/content.bin"
        
        result = manager.store_content(content, key, content_type='application/octet-stream')
        
        assert result.success is True
        assert result.metadata['size_bytes'] == len(content)
    
    def test_store_content_custom_bucket(self, mock_s3_client):
        """Test storing content in custom bucket."""
        # Configure the mock
        mock_s3_client.put_object.return_value = {}
        
        manager = S3Manager('test-content', 'test-artifacts', 'test-traces')
        
        content = "Test content"
        key = "test/content.txt"
        
        result = manager.store_content(content, key, bucket='test-artifacts')
        
        assert result.success is True
        assert result.metadata['s3_uri'] == f"s3://test-artifacts/{key}"
    
    def test_store_content_success(self, mock_s3_client):
        """Test successful content storage in S3."""
        # Configure the mock
        mock_s3_client.put_object.return_value = {}
        
        manager = S3Manager('test-content', 'test-artifacts', 'test-traces')
        
        content = "This is test content"
        key = "test/content.txt"
        
        result = manager.store_content(content, key)
        
        assert result.success is True
        assert result.operation == "store_content"
        assert result.items_processed == 1
        assert 's3_uri' in result.metadata
        assert result.metadata['s3_uri'] == f"s3://test-content/{key}"
        assert 'size_bytes' in result.metadata
        
        # Verify put_object was called
        mock_s3_client.put_object.assert_called_once()
    
    def test_store_content_bytes(self, mock_s3_client):
        """Test storing bytes content in S3."""
        # Configure the mock
        mock_s3_client.put_object.return_value = {}
        
        manager = S3Manager('test-content', 'test-artifacts', 'test-traces')
        
        content = b"This is test content as bytes"
        key = "test/content.bin"
        
        result = manager.store_content(content, key, content_type='application/octet-stream')
        
        assert result.success is True
        assert result.metadata['size_bytes'] == len(content)
    
    def test_store_content_custom_bucket(self, mock_s3_client):
        """Test storing content in custom bucket."""
        # Configure the mock
        mock_s3_client.put_object.return_value = {}
        
        manager = S3Manager('test-content', 'test-artifacts', 'test-traces')
        
        content = "Test content"
        key = "test/content.txt"
        
        result = manager.store_content(content, key, bucket='test-artifacts')
        
        assert result.success is True
        assert result.metadata['s3_uri'] == f"s3://test-artifacts/{key}"


class TestStorageTool:
    """Test StorageTool main class."""
    
    @pytest.fixture
    def setup_storage_tool(self):
        """Set up StorageTool with mocked managers."""
        with patch('lambda_tools.storage_tool.DynamoDBManager') as mock_dynamodb_cls, \
             patch('lambda_tools.storage_tool.S3Manager') as mock_s3_cls:
            
            mock_dynamodb = Mock()
            mock_s3 = Mock()
            
            mock_dynamodb_cls.return_value = mock_dynamodb
            mock_s3_cls.return_value = mock_s3
            
            storage_tool = StorageTool(
                'test-articles', 'test-comments', 'test-memory',
                'test-content', 'test-artifacts', 'test-traces'
            )
            
            return storage_tool, mock_dynamodb, mock_s3
    
    def test_store_article_success(self, setup_storage_tool):
        """Test successful complete article storage."""
        storage_tool, mock_dynamodb, mock_s3 = setup_storage_tool
        
        article_data = {
            'article_id': 'test-123',
            'title': 'Test Article',
            'url': 'https://example.com/test',
            'source': 'test-source',
            'feed_id': 'test-feed',
            'raw_content': '<html>Test content</html>'
        }
        
        # Mock successful DynamoDB creation
        mock_dynamodb.create_article.return_value = StorageResult(
            success=True,
            operation="create_article",
            article_id='test-123'
        )
        
        # Mock successful S3 storage
        mock_s3.store_content.return_value = StorageResult(
            success=True,
            operation="store_content",
            metadata={'s3_uri': 's3://test-bucket/test-key'}
        )
        
        # Mock successful DynamoDB update
        mock_dynamodb.update_article.return_value = StorageResult(
            success=True,
            operation="update_article"
        )
        
        result = storage_tool.store_article(article_data)
        
        assert result.success is True
        assert result.operation == "store_article"
        assert result.article_id == 'test-123'
        assert 'dynamodb_stored' in result.metadata
        assert 's3_operations' in result.metadata


class TestLambdaHandler:
    """Test lambda_handler function."""
    
    @patch.dict(os.environ, {
        'ARTICLES_TABLE': 'test-articles',
        'COMMENTS_TABLE': 'test-comments',
        'MEMORY_TABLE': 'test-memory',
        'CONTENT_BUCKET': 'test-content',
        'ARTIFACTS_BUCKET': 'test-artifacts',
        'TRACES_BUCKET': 'test-traces'
    })
    @patch('lambda_tools.storage_tool.StorageTool')
    def test_lambda_handler_create_article(self, mock_storage_tool_cls):
        """Test lambda handler for create_article operation."""
        mock_storage_tool = Mock()
        mock_storage_tool_cls.return_value = mock_storage_tool
        
        mock_storage_tool.dynamodb_manager.create_article.return_value = StorageResult(
            success=True,
            operation="create_article",
            article_id='test-123',
            items_processed=1
        )
        
        event = {
            'operation': 'create_article',
            'article_data': {
                'title': 'Test Article',
                'url': 'https://example.com/test',
                'source': 'test-source',
                'feed_id': 'test-feed'
            }
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 200
        assert result['body']['success'] is True
        assert result['body']['operation'] == 'create_article'
        assert result['body']['article_id'] == 'test-123'
    
    def test_lambda_handler_missing_operation(self):
        """Test lambda handler with missing operation."""
        event = {}
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 500
        assert result['body']['success'] is False
        assert 'operation is required' in result['body']['error']
    
    def test_lambda_handler_unknown_operation(self):
        """Test lambda handler with unknown operation."""
        event = {'operation': 'unknown_operation'}
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 500
        assert result['body']['success'] is False
        assert 'Unknown operation' in result['body']['error']
    
    @patch.dict(os.environ, {
        'ARTICLES_TABLE': 'test-articles',
        'COMMENTS_TABLE': 'test-comments',
        'MEMORY_TABLE': 'test-memory',
        'CONTENT_BUCKET': 'test-content',
        'ARTIFACTS_BUCKET': 'test-artifacts',
        'TRACES_BUCKET': 'test-traces'
    })
    @patch('lambda_tools.storage_tool.StorageTool')
    def test_lambda_handler_operation_failure(self, mock_storage_tool_cls):
        """Test lambda handler with operation failure."""
        mock_storage_tool = Mock()
        mock_storage_tool_cls.return_value = mock_storage_tool
        
        mock_storage_tool.dynamodb_manager.create_article.return_value = StorageResult(
            success=False,
            operation="create_article",
            errors=["Test error"]
        )
        
        event = {
            'operation': 'create_article',
            'article_data': {'title': 'Test'}
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 400
        assert result['body']['success'] is False
        assert result['body']['errors'] == ["Test error"]
    
    @patch.dict(os.environ, {
        'ARTICLES_TABLE': 'test-articles',
        'COMMENTS_TABLE': 'test-comments',
        'MEMORY_TABLE': 'test-memory',
        'CONTENT_BUCKET': 'test-content',
        'ARTIFACTS_BUCKET': 'test-artifacts',
        'TRACES_BUCKET': 'test-traces'
    })
    @patch('lambda_tools.storage_tool.StorageTool')
    def test_lambda_handler_store_content(self, mock_storage_tool_cls):
        """Test lambda handler for store_content operation."""
        mock_storage_tool = Mock()
        mock_storage_tool_cls.return_value = mock_storage_tool
        
        mock_storage_tool.s3_manager.store_content.return_value = StorageResult(
            success=True,
            operation="store_content",
            items_processed=1,
            metadata={'s3_uri': 's3://test-bucket/test-key', 'size_bytes': 100}
        )
        
        event = {
            'operation': 'store_content',
            'content': 'Test content',
            'key': 'test/file.txt',
            'content_type': 'text/plain'
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 200
        assert result['body']['success'] is True
        assert result['body']['operation'] == 'store_content'
        assert 's3_uri' in result['body']['metadata']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])