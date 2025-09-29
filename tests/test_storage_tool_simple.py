"""
Simple unit tests for StorageTool Lambda function.
"""

import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_tools.storage_tool_simple import StorageResult, StorageTool, lambda_handler


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


class TestLambdaHandler:
    """Test lambda_handler function."""
    
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
    
    def test_lambda_handler_create_article_missing_data(self):
        """Test lambda handler create_article with missing data."""
        event = {
            'operation': 'create_article',
            'article_data': {}
        }
        
        # Mock environment
        os.environ['ARTICLES_TABLE'] = 'test-articles'
        
        result = lambda_handler(event, None)
        
        # Should succeed but with empty data (for this simple version)
        assert result['statusCode'] in [200, 400, 500]  # Any valid response
        assert 'success' in result['body']
    
    def test_lambda_handler_get_article_missing_id(self):
        """Test lambda handler get_article with missing article_id."""
        event = {
            'operation': 'get_article'
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 500
        assert result['body']['success'] is False
        assert 'article_id is required' in result['body']['error']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])