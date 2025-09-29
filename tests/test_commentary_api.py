"""
Unit tests for CommentaryAPI Lambda tool.

Tests comment creation and management, threaded discussion support,
comment moderation, search and filtering capabilities.
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

from lambda_tools.commentary_api import (
    CommentaryAPI,
    CommentModerator,
    ThreadManager,
    CommentSearchManager,
    CommentResult,
    lambda_handler
)


class TestCommentModerator:
    """Test comment moderation logic."""
    
    def test_validate_comment_content_valid(self):
        """Test validation of valid comment content."""
        content = "This is a helpful comment about the security vulnerability."
        
        result = CommentModerator.validate_comment_content(content)
        
        assert result['is_valid'] is True
        assert len(result['flags']) == 0
        assert result['sanitized_content'] == content
    
    def test_validate_comment_content_too_short(self):
        """Test validation of too short comment."""
        content = "Hi"
        
        result = CommentModerator.validate_comment_content(content)
        
        assert result['is_valid'] is False
        assert 'too_short' in result['flags']
    
    def test_validate_comment_content_too_long(self):
        """Test validation of too long comment."""
        content = "x" * 6000  # Exceeds MAX_COMMENT_LENGTH
        
        result = CommentModerator.validate_comment_content(content)
        
        assert result['is_valid'] is False
        assert 'too_long' in result['flags']
    
    def test_validate_comment_content_banned_words(self):
        """Test validation with banned words."""
        content = "This looks like spam to me."
        
        result = CommentModerator.validate_comment_content(content)
        
        assert 'banned_word_spam' in result['flags']
        assert len(result['warnings']) > 0
    
    def test_validate_comment_content_urls(self):
        """Test validation with URLs."""
        content = "Check this out: https://example.com/article"
        
        result = CommentModerator.validate_comment_content(content)
        
        assert result['is_valid'] is True
        assert 'contains_urls' in result['flags']
        assert any('URL' in warning for warning in result['warnings'])
    
    def test_validate_comment_content_xss_attempt(self):
        """Test validation with potential XSS."""
        content = "Nice article <script>alert('xss')</script>"
        
        result = CommentModerator.validate_comment_content(content)
        
        assert result['is_valid'] is False
        assert 'potential_xss' in result['flags']
    
    def test_validate_comment_content_html_sanitization(self):
        """Test HTML sanitization."""
        content = "This is <b>bold</b> and this is <i>italic</i>"
        
        result = CommentModerator.validate_comment_content(content)
        
        assert result['is_valid'] is True
        assert '&lt;b&gt;' in result['sanitized_content']
        assert '&lt;/b&gt;' in result['sanitized_content']
    
    def test_should_auto_moderate(self):
        """Test auto-moderation decision."""
        # Should auto-moderate
        spam_result = {'flags': ['banned_word_spam']}
        assert CommentModerator.should_auto_moderate(spam_result) is True
        
        # Should not auto-moderate
        url_result = {'flags': ['contains_urls']}
        assert CommentModerator.should_auto_moderate(url_result) is False


class TestThreadManager:
    """Test thread management."""
    
    @patch('lambda_tools.commentary_api.dynamodb')
    def test_build_comment_tree(self, mock_dynamodb):
        """Test building comment tree from flat list."""
        manager = ThreadManager('test-comments')
        
        comments = [
            {
                'comment_id': 'comment-1',
                'parent_comment_id': None,
                'created_at': '2024-01-01T10:00:00Z',
                'content': 'Root comment'
            },
            {
                'comment_id': 'comment-2',
                'parent_comment_id': 'comment-1',
                'created_at': '2024-01-01T10:05:00Z',
                'content': 'Reply to root'
            },
            {
                'comment_id': 'comment-3',
                'parent_comment_id': 'comment-2',
                'created_at': '2024-01-01T10:10:00Z',
                'content': 'Reply to reply'
            },
            {
                'comment_id': 'comment-4',
                'parent_comment_id': None,
                'created_at': '2024-01-01T10:15:00Z',
                'content': 'Another root comment'
            }
        ]
        
        tree = manager.build_comment_tree(comments)
        
        # Should have 2 root comments
        assert len(tree) == 2
        
        # First root comment should have 1 child
        assert len(tree[0]['children']) == 1
        
        # That child should have 1 child (nested reply)
        assert len(tree[0]['children'][0]['children']) == 1
        
        # Second root comment should have no children
        assert len(tree[1]['children']) == 0
        
        # Check depth assignment
        assert tree[0]['depth'] == 0
        assert tree[0]['children'][0]['depth'] == 1
        assert tree[0]['children'][0]['children'][0]['depth'] == 2
    
    @patch('lambda_tools.commentary_api.dynamodb')
    def test_flatten_comment_tree(self, mock_dynamodb):
        """Test flattening comment tree."""
        manager = ThreadManager('test-comments')
        
        tree = [
            {
                'comment_id': 'comment-1',
                'content': 'Root',
                'children': [
                    {
                        'comment_id': 'comment-2',
                        'content': 'Reply',
                        'children': []
                    }
                ]
            }
        ]
        
        flattened = manager.flatten_comment_tree(tree)
        
        assert len(flattened) == 2
        assert flattened[0]['comment_id'] == 'comment-1'
        assert flattened[0]['depth'] == 0
        assert flattened[1]['comment_id'] == 'comment-2'
        assert flattened[1]['depth'] == 1
        assert 'children' not in flattened[0]  # Should be removed
    
    @patch('lambda_tools.commentary_api.dynamodb')
    def test_get_thread_statistics(self, mock_dynamodb):
        """Test thread statistics calculation."""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.query.return_value = {
            'Items': [
                {
                    'comment_id': 'comment-1',
                    'author': 'user1',
                    'parent_comment_id': None,
                    'created_at': '2024-01-01T10:00:00Z'
                },
                {
                    'comment_id': 'comment-2',
                    'author': 'user2',
                    'parent_comment_id': 'comment-1',
                    'created_at': '2024-01-01T10:05:00Z'
                },
                {
                    'comment_id': 'comment-3',
                    'author': 'user1',
                    'parent_comment_id': 'comment-1',
                    'created_at': '2024-01-01T10:10:00Z'
                }
            ]
        }
        
        manager = ThreadManager('test-comments')
        stats = manager.get_thread_statistics('test-article')
        
        assert stats['total_comments'] == 3
        assert stats['root_comments'] == 1
        assert stats['replies'] == 2
        assert stats['unique_authors'] == 2
        assert stats['most_recent_comment'] == '2024-01-01T10:10:00Z'


class TestCommentSearchManager:
    """Test comment search functionality."""
    
    @patch('lambda_tools.commentary_api.dynamodb')
    def test_search_comments_by_article(self, mock_dynamodb):
        """Test searching comments by article ID."""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.query.return_value = {
            'Items': [
                {
                    'comment_id': 'comment-1',
                    'article_id': 'article-1',
                    'author': 'user1',
                    'content': 'Great article about Azure security',
                    'created_at': '2024-01-01T10:00:00Z'
                },
                {
                    'comment_id': 'comment-2',
                    'article_id': 'article-1',
                    'author': 'user2',
                    'content': 'I disagree with the analysis',
                    'created_at': '2024-01-01T10:05:00Z'
                }
            ]
        }
        
        manager = CommentSearchManager('test-comments')
        
        search_params = {
            'article_id': 'article-1',
            'content_search': 'azure'
        }
        
        result = manager.search_comments(search_params)
        
        assert result.success is True
        assert result.comment_count == 1  # Only one comment contains 'azure'
        assert result.comments[0]['comment_id'] == 'comment-1'
    
    @patch('lambda_tools.commentary_api.dynamodb')
    def test_search_comments_by_author(self, mock_dynamodb):
        """Test searching comments by author."""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.query.return_value = {
            'Items': [
                {
                    'comment_id': 'comment-1',
                    'author': 'user1',
                    'content': 'Comment 1',
                    'created_at': '2024-01-01T10:00:00Z'
                },
                {
                    'comment_id': 'comment-2',
                    'author': 'user2',
                    'content': 'Comment 2',
                    'created_at': '2024-01-01T10:05:00Z'
                }
            ]
        }
        
        manager = CommentSearchManager('test-comments')
        
        search_params = {
            'article_id': 'article-1',
            'author': 'user1'
        }
        
        result = manager.search_comments(search_params)
        
        assert result.success is True
        assert result.comment_count == 1
        assert result.comments[0]['author'] == 'user1'


class TestCommentaryAPI:
    """Test main commentary API."""
    
    @patch('lambda_tools.commentary_api.dynamodb')
    def test_create_comment_success(self, mock_dynamodb):
        """Test successful comment creation."""
        mock_comments_table = Mock()
        mock_articles_table = Mock()
        mock_dynamodb.Table.side_effect = lambda name: (
            mock_comments_table if 'comments' in name else mock_articles_table
        )
        
        # Mock article exists
        mock_articles_table.get_item.return_value = {
            'Item': {'article_id': 'test-article', 'title': 'Test Article'}
        }
        
        api = CommentaryAPI('test-comments', 'test-articles')
        
        result = api.create_comment(
            'test-article', 'user@example.com', 'This is a great article!'
        )
        
        assert result.success is True
        assert result.article_id == 'test-article'
        assert result.comment_id is not None
        
        # Verify comment was stored
        mock_comments_table.put_item.assert_called_once()
        
        # Verify article comment count was updated
        mock_articles_table.update_item.assert_called_once()
    
    @patch('lambda_tools.commentary_api.dynamodb')
    def test_create_comment_article_not_found(self, mock_dynamodb):
        """Test comment creation when article doesn't exist."""
        mock_comments_table = Mock()
        mock_articles_table = Mock()
        mock_dynamodb.Table.side_effect = lambda name: (
            mock_comments_table if 'comments' in name else mock_articles_table
        )
        
        # Mock article doesn't exist
        mock_articles_table.get_item.return_value = {}
        
        api = CommentaryAPI('test-comments', 'test-articles')
        
        result = api.create_comment(
            'nonexistent-article', 'user@example.com', 'This is a comment'
        )
        
        assert result.success is False
        assert 'not found' in result.errors[0]
    
    @patch('lambda_tools.commentary_api.dynamodb')
    def test_create_comment_invalid_content(self, mock_dynamodb):
        """Test comment creation with invalid content."""
        mock_comments_table = Mock()
        mock_articles_table = Mock()
        mock_dynamodb.Table.side_effect = lambda name: (
            mock_comments_table if 'comments' in name else mock_articles_table
        )
        
        api = CommentaryAPI('test-comments', 'test-articles')
        
        result = api.create_comment(
            'test-article', 'user@example.com', 'x'  # Too short
        )
        
        assert result.success is False
        assert 'validation failed' in result.errors[0]
    
    @patch('lambda_tools.commentary_api.dynamodb')
    def test_create_reply_comment(self, mock_dynamodb):
        """Test creating a reply comment."""
        mock_comments_table = Mock()
        mock_articles_table = Mock()
        mock_dynamodb.Table.side_effect = lambda name: (
            mock_comments_table if 'comments' in name else mock_articles_table
        )
        
        # Mock article exists
        mock_articles_table.get_item.return_value = {
            'Item': {'article_id': 'test-article', 'title': 'Test Article'}
        }
        
        # Mock parent comment exists
        mock_comments_table.get_item.return_value = {
            'Item': {
                'comment_id': 'parent-comment',
                'thread_id': 'parent-comment',
                'depth': 0
            }
        }
        
        api = CommentaryAPI('test-comments', 'test-articles')
        
        result = api.create_comment(
            'test-article', 'user@example.com', 'This is a reply!',
            parent_comment_id='parent-comment'
        )
        
        assert result.success is True
        assert result.metadata['depth'] == 1
        
        # Verify parent comment reply count was updated
        assert mock_comments_table.update_item.call_count == 1
    
    @patch('lambda_tools.commentary_api.dynamodb')
    def test_get_comments_as_tree(self, mock_dynamodb):
        """Test getting comments formatted as tree."""
        mock_comments_table = Mock()
        mock_articles_table = Mock()
        mock_dynamodb.Table.side_effect = lambda name: (
            mock_comments_table if 'comments' in name else mock_articles_table
        )
        
        mock_comments_table.query.return_value = {
            'Items': [
                {
                    'comment_id': 'comment-1',
                    'parent_comment_id': None,
                    'visibility': 'public',
                    'created_at': '2024-01-01T10:00:00Z'
                },
                {
                    'comment_id': 'comment-2',
                    'parent_comment_id': 'comment-1',
                    'visibility': 'public',
                    'created_at': '2024-01-01T10:05:00Z'
                }
            ]
        }
        
        api = CommentaryAPI('test-comments', 'test-articles')
        
        result = api.get_comments('test-article', format_as_tree=True)
        
        assert result.success is True
        assert result.comment_count == 2
        # Tree format should have nested structure
        assert len(result.comments) == 1  # One root comment
        assert len(result.comments[0]['children']) == 1  # One reply
    
    @patch('lambda_tools.commentary_api.dynamodb')
    def test_update_comment_success(self, mock_dynamodb):
        """Test successful comment update."""
        mock_comments_table = Mock()
        mock_articles_table = Mock()
        mock_dynamodb.Table.side_effect = lambda name: (
            mock_comments_table if 'comments' in name else mock_articles_table
        )
        
        # Mock existing comment
        mock_comments_table.get_item.return_value = {
            'Item': {
                'comment_id': 'test-comment',
                'author': 'user@example.com',
                'content': 'Original content',
                'version': 1
            }
        }
        
        api = CommentaryAPI('test-comments', 'test-articles')
        
        updates = {'content': 'Updated content'}
        result = api.update_comment('test-comment', updates, 'user@example.com')
        
        assert result.success is True
        assert 'content' in result.metadata['updated_fields']
        
        # Verify update was called
        mock_comments_table.update_item.assert_called_once()
    
    @patch('lambda_tools.commentary_api.dynamodb')
    def test_update_comment_unauthorized(self, mock_dynamodb):
        """Test comment update by unauthorized user."""
        mock_comments_table = Mock()
        mock_articles_table = Mock()
        mock_dynamodb.Table.side_effect = lambda name: (
            mock_comments_table if 'comments' in name else mock_articles_table
        )
        
        # Mock existing comment by different author
        mock_comments_table.get_item.return_value = {
            'Item': {
                'comment_id': 'test-comment',
                'author': 'original@example.com',
                'content': 'Original content'
            }
        }
        
        api = CommentaryAPI('test-comments', 'test-articles')
        
        updates = {'content': 'Malicious update'}
        result = api.update_comment('test-comment', updates, 'hacker@example.com')
        
        assert result.success is False
        assert 'Unauthorized' in result.errors[0]
    
    @patch('lambda_tools.commentary_api.dynamodb')
    def test_delete_comment_success(self, mock_dynamodb):
        """Test successful comment deletion."""
        mock_comments_table = Mock()
        mock_articles_table = Mock()
        mock_dynamodb.Table.side_effect = lambda name: (
            mock_comments_table if 'comments' in name else mock_articles_table
        )
        
        # Mock existing comment
        mock_comments_table.get_item.return_value = {
            'Item': {
                'comment_id': 'test-comment',
                'author': 'user@example.com',
                'article_id': 'test-article'
            }
        }
        
        api = CommentaryAPI('test-comments', 'test-articles')
        
        result = api.delete_comment('test-comment', 'user@example.com')
        
        assert result.success is True
        
        # Verify soft delete (update to deleted status)
        mock_comments_table.update_item.assert_called()
        
        # Verify article comment count was decremented
        mock_articles_table.update_item.assert_called()


class TestLambdaHandler:
    """Test Lambda handler function."""
    
    @patch.dict(os.environ, {
        'COMMENTS_TABLE': 'test-comments',
        'ARTICLES_TABLE': 'test-articles'
    })
    @patch('lambda_tools.commentary_api.CommentaryAPI')
    def test_lambda_handler_create_comment(self, mock_api_class):
        """Test Lambda handler for create_comment operation."""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_api.create_comment.return_value = CommentResult(
            success=True,
            operation='create_comment',
            comment_id='test-comment',
            article_id='test-article'
        )
        
        event = {
            'operation': 'create_comment',
            'article_id': 'test-article',
            'author': 'user@example.com',
            'content': 'This is a test comment'
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        assert response['body']['success'] is True
        assert response['body']['comment_id'] == 'test-comment'
        mock_api.create_comment.assert_called_once()
    
    @patch.dict(os.environ, {
        'COMMENTS_TABLE': 'test-comments',
        'ARTICLES_TABLE': 'test-articles'
    })
    @patch('lambda_tools.commentary_api.CommentaryAPI')
    def test_lambda_handler_get_comments(self, mock_api_class):
        """Test Lambda handler for get_comments operation."""
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        mock_api.get_comments.return_value = CommentResult(
            success=True,
            operation='get_comments',
            article_id='test-article',
            comment_count=2,
            comments=[{'comment_id': 'comment-1'}, {'comment_id': 'comment-2'}]
        )
        
        event = {
            'operation': 'get_comments',
            'article_id': 'test-article',
            'format_as_tree': True
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        assert response['body']['success'] is True
        assert response['body']['comment_count'] == 2
        mock_api.get_comments.assert_called_once()
    
    def test_lambda_handler_missing_required_fields(self):
        """Test Lambda handler with missing required fields."""
        event = {
            'operation': 'create_comment',
            'article_id': 'test-article'
            # Missing author and content
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])