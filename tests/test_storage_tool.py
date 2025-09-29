"""
Unit tests for StorageTool Lambda function.

Tests cover DynamoDB operations, S3 operations, batch processing,
data consistency checks, and error handling scenarios.
"""

import json
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from moto import mock_aws
import boto3

# Import the module under test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_tools.storage_tool import (
    StorageTool, DynamoDBManager, S3Manager, DataConsistencyChecker,
    StorageResult, BatchOperationResult, StorageToolError, DataConsistencyError,
    lambda_handler
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


@mock_aws
class TestDynamoDBManager:
    """Test DynamoDBManager class."""
    
    @pytest.fixture
    def setup_dynamodb(self):
        """Set up DynamoDB tables for testing."""
        # Create DynamoDB resource
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create articles table
        articles_table = dynamodb.create_table(
            TableName='test-articles',
            KeySchema=[
                {'AttributeName': 'article_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'article_id', 'AttributeType': 'S'},
                {'AttributeName': 'state', 'AttributeType': 'S'},
                {'AttributeName': 'published_at', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'state-published_at-index',
                    'KeySchema': [
                        {'AttributeName': 'state', 'KeyType': 'HASH'},
                        {'AttributeName': 'published_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        # Create comments table
        comments_table = dynamodb.create_table(
            TableName='test-comments',
            KeySchema=[
                {'AttributeName': 'comment_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'comment_id', 'AttributeType': 'S'}
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        # Create memory table
        memory_table = dynamodb.create_table(
            TableName='test-memory',
            KeySchema=[
                {'AttributeName': 'memory_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'memory_id', 'AttributeType': 'S'}
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        # Wait for tables to be created
        articles_table.wait_until_exists()
        comments_table.wait_until_exists()
        memory_table.wait_until_exists()
        
        return dynamodb
    
    def test_create_article_success(self, setup_dynamodb):
        """Test successful article creation."""
        manager = DynamoDBManager('test-articles', 'test-comments', 'test-memory')
        
        article_data = {
            'title': 'Test Article',
            'url': 'https://example.com/test',
            'source': 'test-source',
            'feed_id': 'test-feed',
            'published_at': '2024-01-01T00:00:00Z'
        }
        
        result = manager.create_article(article_data)
        
        assert result.success is True
        assert result.operation == "create_article"
        assert result.article_id is not None
        assert result.items_processed == 1
        assert 'created_at' in result.metadata
    
    def test_create_article_missing_fields(self, setup_dynamodb):
        """Test article creation with missing required fields."""
        manager = DynamoDBManager('test-articles', 'test-comments', 'test-memory')
        
        article_data = {
            'title': 'Test Article'
            # Missing url, source, feed_id
        }
        
        result = manager.create_article(article_data)
        
        assert result.success is False
        assert result.operation == "validate_article_data"
        assert "Missing required fields" in result.errors[0]
    
    def test_create_article_invalid_url(self, setup_dynamodb):
        """Test article creation with invalid URL."""
        manager = DynamoDBManager('test-articles', 'test-comments', 'test-memory')
        
        article_data = {
            'title': 'Test Article',
            'url': 'invalid-url',
            'source': 'test-source',
            'feed_id': 'test-feed'
        }
        
        result = manager.create_article(article_data)
        
        assert result.success is False
        assert "Invalid URL format" in result.errors[0]
    
    def test_update_article_success(self, setup_dynamodb):
        """Test successful article update."""
        manager = DynamoDBManager('test-articles', 'test-comments', 'test-memory')
        
        # First create an article
        article_data = {
            'article_id': 'test-123',
            'title': 'Test Article',
            'url': 'https://example.com/test',
            'source': 'test-source',
            'feed_id': 'test-feed'
        }
        
        create_result = manager.create_article(article_data)
        assert create_result.success is True
        
        # Now update it
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
    
    def test_update_nonexistent_article(self, setup_dynamodb):
        """Test updating a non-existent article."""
        manager = DynamoDBManager('test-articles', 'test-comments', 'test-memory')
        
        updates = {'state': 'PROCESSED'}
        result = manager.update_article('nonexistent-123', updates)
        
        assert result.success is False
        assert "does not exist" in result.errors[0]
    
    def test_get_article_success(self, setup_dynamodb):
        """Test successful article retrieval."""
        manager = DynamoDBManager('test-articles', 'test-comments', 'test-memory')
        
        # Create an article first
        article_data = {
            'article_id': 'test-123',
            'title': 'Test Article',
            'url': 'https://example.com/test',
            'source': 'test-source',
            'feed_id': 'test-feed'
        }
        
        create_result = manager.create_article(article_data)
        assert create_result.success is True
        
        # Retrieve the article
        result = manager.get_article('test-123')
        
        assert result.success is True
        assert result.operation == "get_article"
        assert result.article_id == 'test-123'
        assert 'article' in result.metadata
        assert result.metadata['article']['title'] == 'Test Article'
    
    def test_get_nonexistent_article(self, setup_dynamodb):
        """Test retrieving a non-existent article."""
        manager = DynamoDBManager('test-articles', 'test-comments', 'test-memory')
        
        result = manager.get_article('nonexistent-123')
        
        assert result.success is False
        assert "not found" in result.errors[0]
    
    def test_update_article_state_success(self, setup_dynamodb):
        """Test successful article state update."""
        manager = DynamoDBManager('test-articles', 'test-comments', 'test-memory')
        
        # Create an article first
        article_data = {
            'article_id': 'test-123',
            'title': 'Test Article',
            'url': 'https://example.com/test',
            'source': 'test-source',
            'feed_id': 'test-feed'
        }
        
        create_result = manager.create_article(article_data)
        assert create_result.success is True
        
        # Update state
        result = manager.update_article_state('test-123', 'PROCESSED')
        
        assert result.success is True
        assert result.operation == "update_article"
    
    def test_update_article_state_invalid(self, setup_dynamodb):
        """Test article state update with invalid state."""
        manager = DynamoDBManager('test-articles', 'test-comments', 'test-memory')
        
        result = manager.update_article_state('test-123', 'INVALID_STATE')
        
        assert result.success is False
        assert "Invalid state" in result.errors[0]
    
    def test_batch_create_articles(self, setup_dynamodb):
        """Test batch article creation."""
        manager = DynamoDBManager('test-articles', 'test-comments', 'test-memory')
        
        articles = [
            {
                'title': f'Test Article {i}',
                'url': f'https://example.com/test{i}',
                'source': 'test-source',
                'feed_id': 'test-feed'
            }
            for i in range(5)
        ]
        
        result = manager.batch_create_articles(articles)
        
        assert result.total_items == 5
        assert result.successful_items == 5
        assert result.failed_items == 0
        assert len(result.errors) == 0
    
    def test_query_articles_by_state(self, setup_dynamodb):
        """Test querying articles by state."""
        manager = DynamoDBManager('test-articles', 'test-comments', 'test-memory')
        
        # Create articles with different states
        for i, state in enumerate(['INGESTED', 'PROCESSED', 'PUBLISHED']):
            article_data = {
                'article_id': f'test-{i}',
                'title': f'Test Article {i}',
                'url': f'https://example.com/test{i}',
                'source': 'test-source',
                'feed_id': 'test-feed',
                'state': state,
                'published_at': f'2024-01-0{i+1}T00:00:00Z'
            }
            create_result = manager.create_article(article_data)
            assert create_result.success is True
        
        # Query for PROCESSED articles
        result = manager.query_articles_by_state('PROCESSED')
        
        assert result.success is True
        assert result.operation == "query_articles_by_state"
        assert len(result.metadata['articles']) == 1
        assert result.metadata['articles'][0]['state'] == 'PROCESSED'
    
    def test_create_comment_success(self, setup_dynamodb):
        """Test successful comment creation."""
        manager = DynamoDBManager('test-articles', 'test-comments', 'test-memory')
        
        # Create an article first
        article_data = {
            'article_id': 'test-123',
            'title': 'Test Article',
            'url': 'https://example.com/test',
            'source': 'test-source',
            'feed_id': 'test-feed'
        }
        
        create_result = manager.create_article(article_data)
        assert create_result.success is True
        
        # Create a comment
        comment_data = {
            'article_id': 'test-123',
            'author': 'test-user',
            'content': 'This is a test comment'
        }
        
        result = manager.create_comment(comment_data)
        
        assert result.success is True
        assert result.operation == "create_comment"
        assert result.items_processed == 1
    
    def test_create_comment_missing_article(self, setup_dynamodb):
        """Test comment creation for non-existent article."""
        manager = DynamoDBManager('test-articles', 'test-comments', 'test-memory')
        
        comment_data = {
            'article_id': 'nonexistent-123',
            'author': 'test-user',
            'content': 'This is a test comment'
        }
        
        result = manager.create_comment(comment_data)
        
        assert result.success is False
        assert "does not exist" in result.errors[0]
    
    def test_convert_dynamodb_types(self, setup_dynamodb):
        """Test DynamoDB type conversion methods."""
        manager = DynamoDBManager('test-articles', 'test-comments', 'test-memory')
        
        # Test conversion to DynamoDB types
        data = {
            'string_field': 'test',
            'float_field': 3.14,
            'dict_field': {'nested': 2.71},
            'list_field': [1.41, {'nested': 1.73}]
        }
        
        converted = manager._convert_to_dynamodb_type(data)
        
        assert isinstance(converted['float_field'], Decimal)
        assert isinstance(converted['dict_field']['nested'], Decimal)
        assert isinstance(converted['list_field'][0], Decimal)
        
        # Test conversion from DynamoDB types
        back_converted = manager._convert_from_dynamodb_types(converted)
        
        assert isinstance(back_converted['float_field'], float)
        assert isinstance(back_converted['dict_field']['nested'], float)
        assert isinstance(back_converted['list_field'][0], float)


@mock_aws
class TestS3Manager:
    """Test S3Manager class."""
    
    @pytest.fixture
    def setup_s3(self):
        """Set up S3 buckets for testing."""
        s3_client = boto3.client('s3', region_name='us-east-1')
        
        # Create test buckets
        s3_client.create_bucket(Bucket='test-content')
        s3_client.create_bucket(Bucket='test-artifacts')
        s3_client.create_bucket(Bucket='test-traces')
        
        return s3_client
    
    def test_store_content_success(self, setup_s3):
        """Test successful content storage in S3."""
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
    
    def test_store_content_bytes(self, setup_s3):
        """Test storing bytes content in S3."""
        manager = S3Manager('test-content', 'test-artifacts', 'test-traces')
        
        content = b"This is test content as bytes"
        key = "test/content.bin"
        
        result = manager.store_content(content, key, content_type='application/octet-stream')
        
        assert result.success is True
        assert result.metadata['size_bytes'] == len(content)
    
    def test_store_content_custom_bucket(self, setup_s3):
        """Test storing content in custom bucket."""
        manager = S3Manager('test-content', 'test-artifacts', 'test-traces')
        
        content = "Test content"
        key = "test/content.txt"
        
        result = manager.store_content(content, key, bucket='test-artifacts')
        
        assert result.success is True
        assert result.metadata['s3_uri'] == f"s3://test-artifacts/{key}"
    
    def test_retrieve_content_success(self, setup_s3):
        """Test successful content retrieval from S3."""
        manager = S3Manager('test-content', 'test-artifacts', 'test-traces')
        
        # Store content first
        content = "This is test content for retrieval"
        key = "test/retrieve.txt"
        
        store_result = manager.store_content(content, key)
        assert store_result.success is True
        
        # Retrieve content
        result = manager.retrieve_content(key)
        
        assert result.success is True
        assert result.operation == "retrieve_content"
        assert result.items_processed == 1
        assert result.metadata['content'] == content
        assert 'size_bytes' in result.metadata
        assert 'last_modified' in result.metadata
    
    def test_retrieve_nonexistent_content(self, setup_s3):
        """Test retrieving non-existent content from S3."""
        manager = S3Manager('test-content', 'test-artifacts', 'test-traces')
        
        result = manager.retrieve_content('nonexistent/file.txt')
        
        assert result.success is False
        assert "not found" in result.errors[0]


class TestDataConsistencyChecker:
    """Test DataConsistencyChecker class."""
    
    @pytest.fixture
    def setup_checker(self):
        """Set up DataConsistencyChecker with mocked managers."""
        mock_dynamodb_manager = Mock()
        mock_s3_manager = Mock()
        
        checker = DataConsistencyChecker(mock_dynamodb_manager, mock_s3_manager)
        return checker, mock_dynamodb_manager, mock_s3_manager
    
    def test_verify_article_integrity_success(self, setup_checker):
        """Test successful article integrity verification."""
        checker, mock_dynamodb, mock_s3 = setup_checker
        
        # Mock article data
        article_data = {
            'article_id': 'test-123',
            'title': 'Test Article',
            'url': 'https://example.com/test',
            'source': 'test-source',
            'feed_id': 'test-feed',
            'state': 'PROCESSED',
            'is_duplicate': False,
            'cluster_id': 'cluster_test-123'
        }
        
        mock_dynamodb.get_article.return_value = StorageResult(
            success=True,
            operation="get_article",
            metadata={'article': article_data}
        )
        
        result = checker.verify_article_integrity('test-123')
        
        assert result.success is True
        assert result.operation == "verify_article_integrity"
        assert result.article_id == 'test-123'
        assert 'integrity_score' in result.metadata
    
    def test_verify_article_integrity_missing_fields(self, setup_checker):
        """Test integrity verification with missing required fields."""
        checker, mock_dynamodb, mock_s3 = setup_checker
        
        # Mock article data with missing fields
        article_data = {
            'article_id': 'test-123',
            'title': 'Test Article'
            # Missing url, source, feed_id, state
        }
        
        mock_dynamodb.get_article.return_value = StorageResult(
            success=True,
            operation="get_article",
            metadata={'article': article_data}
        )
        
        result = checker.verify_article_integrity('test-123')
        
        assert result.success is False
        assert len(result.errors) > 0
        assert any("Missing required field" in error for error in result.errors)
    
    def test_verify_article_integrity_duplicate_inconsistency(self, setup_checker):
        """Test integrity verification with duplicate inconsistency."""
        checker, mock_dynamodb, mock_s3 = setup_checker
        
        # Mock article data with duplicate inconsistency
        article_data = {
            'article_id': 'test-123',
            'title': 'Test Article',
            'url': 'https://example.com/test',
            'source': 'test-source',
            'feed_id': 'test-feed',
            'state': 'PROCESSED',
            'is_duplicate': True
            # Missing duplicate_of field
        }
        
        mock_dynamodb.get_article.return_value = StorageResult(
            success=True,
            operation="get_article",
            metadata={'article': article_data}
        )
        
        result = checker.verify_article_integrity('test-123')
        
        assert result.success is False
        assert any("marked as duplicate but missing duplicate_of" in error for error in result.errors)
    
    def test_batch_verify_integrity(self, setup_checker):
        """Test batch integrity verification."""
        checker, mock_dynamodb, mock_s3 = setup_checker
        
        # Mock successful integrity checks
        def mock_verify(article_id):
            return StorageResult(
                success=True,
                operation="verify_article_integrity",
                article_id=article_id,
                metadata={'integrity_score': 1.0}
            )
        
        checker.verify_article_integrity = Mock(side_effect=mock_verify)
        
        article_ids = ['test-1', 'test-2', 'test-3']
        result = checker.batch_verify_integrity(article_ids)
        
        assert result.total_items == 3
        assert result.successful_items == 3
        assert result.failed_items == 0
        assert hasattr(result, 'integrity_results')
        assert len(result.integrity_results) == 3


class TestStorageTool:
    """Test StorageTool main class."""
    
    @pytest.fixture
    def setup_storage_tool(self):
        """Set up StorageTool with mocked managers."""
        with patch('lambda_tools.storage_tool.DynamoDBManager') as mock_dynamodb_cls, \
             patch('lambda_tools.storage_tool.S3Manager') as mock_s3_cls, \
             patch('lambda_tools.storage_tool.DataConsistencyChecker') as mock_checker_cls:
            
            mock_dynamodb = Mock()
            mock_s3 = Mock()
            mock_checker = Mock()
            
            mock_dynamodb_cls.return_value = mock_dynamodb
            mock_s3_cls.return_value = mock_s3
            mock_checker_cls.return_value = mock_checker
            
            storage_tool = StorageTool(
                'test-articles', 'test-comments', 'test-memory',
                'test-content', 'test-artifacts', 'test-traces'
            )
            
            return storage_tool, mock_dynamodb, mock_s3, mock_checker
    
    def test_store_article_success(self, setup_storage_tool):
        """Test successful complete article storage."""
        storage_tool, mock_dynamodb, mock_s3, mock_checker = setup_storage_tool
        
        article_data = {
            'article_id': 'test-123',
            'title': 'Test Article',
            'url': 'https://example.com/test',
            'source': 'test-source',
            'feed_id': 'test-feed',
            'raw_content': '<html>Test content</html>',
            'normalized_content': 'Test content'
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
    
    def test_update_article_processing_results(self, setup_storage_tool):
        """Test updating article with processing results."""
        storage_tool, mock_dynamodb, mock_s3, mock_checker = setup_storage_tool
        
        processing_results = {
            'relevancy_score': 0.85,
            'keyword_matches': [{'keyword': 'test', 'hit_count': 2}],
            'entities': {'cves': ['CVE-2024-1234']},
            'is_duplicate': False,
            'triage_action': 'AUTO_PUBLISH',
            'summary_short': 'Test summary',
            'processing_trace': {'step1': 'completed'}
        }
        
        # Mock successful S3 trace storage
        mock_s3.store_content.return_value = StorageResult(
            success=True,
            operation="store_content",
            metadata={'s3_uri': 's3://test-traces/trace.json'}
        )
        
        # Mock successful DynamoDB update
        mock_dynamodb.update_article.return_value = StorageResult(
            success=True,
            operation="update_article",
            article_id='test-123'
        )
        
        result = storage_tool.update_article_processing_results('test-123', processing_results)
        
        assert result.success is True
        assert result.operation == "update_article"
        
        # Verify update_article was called with correct parameters
        mock_dynamodb.update_article.assert_called_once()
        call_args = mock_dynamodb.update_article.call_args
        updates = call_args[0][1]  # Second argument (updates dict)
        
        assert updates['relevancy_score'] == 0.85
        assert updates['state'] == 'PROCESSED'
        assert 'processing_completed_at' in updates
    
    def test_get_articles_for_processing(self, setup_storage_tool):
        """Test getting articles for processing."""
        storage_tool, mock_dynamodb, mock_s3, mock_checker = setup_storage_tool
        
        mock_dynamodb.query_articles_by_state.return_value = StorageResult(
            success=True,
            operation="query_articles_by_state",
            metadata={'articles': [{'article_id': 'test-1'}, {'article_id': 'test-2'}]}
        )
        
        result = storage_tool.get_articles_for_processing('INGESTED', 10)
        
        assert result.success is True
        mock_dynamodb.query_articles_by_state.assert_called_once_with('INGESTED', 10)
    
    def test_verify_data_integrity_single_article(self, setup_storage_tool):
        """Test data integrity verification for single article."""
        storage_tool, mock_dynamodb, mock_s3, mock_checker = setup_storage_tool
        
        mock_checker.verify_article_integrity.return_value = StorageResult(
            success=True,
            operation="verify_article_integrity",
            article_id='test-123'
        )
        
        result = storage_tool.verify_data_integrity(['test-123'])
        
        assert result.success is True
        mock_checker.verify_article_integrity.assert_called_once_with('test-123')
    
    def test_verify_data_integrity_multiple_articles(self, setup_storage_tool):
        """Test data integrity verification for multiple articles."""
        storage_tool, mock_dynamodb, mock_s3, mock_checker = setup_storage_tool
        
        mock_checker.batch_verify_integrity.return_value = BatchOperationResult(
            total_items=2,
            successful_items=2,
            failed_items=0,
            errors=[],
            warnings=[],
            processing_time_seconds=1.0
        )
        
        result = storage_tool.verify_data_integrity(['test-1', 'test-2'])
        
        assert result.total_items == 2
        assert result.successful_items == 2
        mock_checker.batch_verify_integrity.assert_called_once_with(['test-1', 'test-2'])


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
    
    @patch.dict(os.environ, {
        'ARTICLES_TABLE': 'test-articles',
        'COMMENTS_TABLE': 'test-comments',
        'MEMORY_TABLE': 'test-memory',
        'CONTENT_BUCKET': 'test-content',
        'ARTIFACTS_BUCKET': 'test-artifacts',
        'TRACES_BUCKET': 'test-traces'
    })
    @patch('lambda_tools.storage_tool.StorageTool')
    def test_lambda_handler_batch_operation(self, mock_storage_tool_cls):
        """Test lambda handler for batch operation."""
        mock_storage_tool = Mock()
        mock_storage_tool_cls.return_value = mock_storage_tool
        
        mock_storage_tool.dynamodb_manager.batch_create_articles.return_value = BatchOperationResult(
            total_items=3,
            successful_items=3,
            failed_items=0,
            errors=[],
            warnings=[],
            processing_time_seconds=1.5
        )
        
        event = {
            'operation': 'batch_create',
            'articles': [
                {'title': 'Article 1', 'url': 'https://example.com/1', 'source': 'test', 'feed_id': 'test'},
                {'title': 'Article 2', 'url': 'https://example.com/2', 'source': 'test', 'feed_id': 'test'},
                {'title': 'Article 3', 'url': 'https://example.com/3', 'source': 'test', 'feed_id': 'test'}
            ]
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 200
        assert result['body']['success'] is True
        assert result['body']['total_items'] == 3
        assert result['body']['successful_items'] == 3
        assert result['body']['failed_items'] == 0
    
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])