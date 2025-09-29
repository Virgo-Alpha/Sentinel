"""
CommentaryAPI Lambda tool for comment creation and management.

This Lambda function handles comment creation and management, threaded discussion support
with author attribution, comment moderation and visibility controls, search and filtering
capabilities for the Sentinel cybersecurity triage system.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from decimal import Decimal
import uuid
import os
import re

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')


@dataclass
class CommentResult:
    """Result of comment operations."""
    success: bool
    operation: str
    comment_id: Optional[str] = None
    article_id: Optional[str] = None
    thread_id: Optional[str] = None
    comment_count: Optional[int] = None
    comments: List[Dict[str, Any]] = None
    errors: List[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.comments is None:
            self.comments = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}


class CommentError(Exception):
    """Custom exception for comment operations."""
    pass


class CommentModerator:
    """Handles comment moderation and content validation."""
    
    # Banned words/phrases for content moderation
    BANNED_WORDS = [
        'spam', 'scam', 'phishing', 'malware_link', 'suspicious_url',
        'inappropriate', 'offensive', 'harassment'
    ]
    
    # Maximum comment length
    MAX_COMMENT_LENGTH = 5000
    
    # Minimum comment length
    MIN_COMMENT_LENGTH = 3
    
    @classmethod
    def validate_comment_content(cls, content: str) -> Dict[str, Any]:
        """Validate comment content for moderation."""
        validation_result = {
            'is_valid': True,
            'flags': [],
            'warnings': [],
            'sanitized_content': content.strip()
        }
        
        try:
            # Check length
            if len(content.strip()) < cls.MIN_COMMENT_LENGTH:
                validation_result['is_valid'] = False
                validation_result['flags'].append('too_short')
                return validation_result
            
            if len(content) > cls.MAX_COMMENT_LENGTH:
                validation_result['is_valid'] = False
                validation_result['flags'].append('too_long')
                return validation_result
            
            # Check for banned words
            content_lower = content.lower()
            for banned_word in cls.BANNED_WORDS:
                if banned_word in content_lower:
                    validation_result['flags'].append(f'banned_word_{banned_word}')
                    validation_result['warnings'].append(f'Contains potentially inappropriate content: {banned_word}')
            
            # Check for potential URLs (basic detection)
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            urls = re.findall(url_pattern, content)
            if urls:
                validation_result['warnings'].append(f'Contains {len(urls)} URL(s)')
                validation_result['flags'].append('contains_urls')
            
            # Check for excessive capitalization
            if len(re.findall(r'[A-Z]', content)) > len(content) * 0.5:
                validation_result['warnings'].append('Excessive capitalization detected')
                validation_result['flags'].append('excessive_caps')
            
            # Basic HTML/script injection detection
            if '<script' in content_lower or 'javascript:' in content_lower:
                validation_result['is_valid'] = False
                validation_result['flags'].append('potential_xss')
            
            # Sanitize content (basic HTML escape)
            sanitized = content.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
            validation_result['sanitized_content'] = sanitized
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating comment content: {e}")
            validation_result['is_valid'] = False
            validation_result['flags'].append('validation_error')
            return validation_result
    
    @classmethod
    def should_auto_moderate(cls, validation_result: Dict[str, Any]) -> bool:
        """Determine if comment should be auto-moderated."""
        auto_moderate_flags = ['banned_word_spam', 'banned_word_scam', 'potential_xss']
        return any(flag in validation_result['flags'] for flag in auto_moderate_flags)


class ThreadManager:
    """Manages threaded comment discussions."""
    
    def __init__(self, comments_table_name: str):
        self.comments_table = dynamodb.Table(comments_table_name)
    
    def build_comment_tree(self, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build hierarchical comment tree from flat comment list."""
        try:
            # Create lookup maps
            comment_map = {comment['comment_id']: comment for comment in comments}
            root_comments = []
            
            # Add children list to each comment
            for comment in comments:
                comment['children'] = []
                comment['depth'] = 0
            
            # Build tree structure
            for comment in comments:
                parent_id = comment.get('parent_comment_id')
                if parent_id and parent_id in comment_map:
                    # This is a reply
                    parent_comment = comment_map[parent_id]
                    parent_comment['children'].append(comment)
                    comment['depth'] = parent_comment['depth'] + 1
                else:
                    # This is a root comment
                    root_comments.append(comment)
            
            # Sort comments by creation time
            def sort_comments(comment_list):
                comment_list.sort(key=lambda x: x.get('created_at', ''))
                for comment in comment_list:
                    if comment['children']:
                        sort_comments(comment['children'])
            
            sort_comments(root_comments)
            
            return root_comments
            
        except Exception as e:
            logger.error(f"Error building comment tree: {e}")
            return comments  # Return flat list as fallback
    
    def flatten_comment_tree(self, comment_tree: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Flatten hierarchical comment tree to list with depth indicators."""
        flattened = []
        
        def flatten_recursive(comments, depth=0):
            for comment in comments:
                comment_copy = comment.copy()
                comment_copy['depth'] = depth
                # Remove children from flattened version to avoid circular references
                if 'children' in comment_copy:
                    children = comment_copy.pop('children')
                    flattened.append(comment_copy)
                    flatten_recursive(children, depth + 1)
                else:
                    flattened.append(comment_copy)
        
        flatten_recursive(comment_tree)
        return flattened
    
    def get_thread_statistics(self, article_id: str) -> Dict[str, Any]:
        """Get statistics for comment thread."""
        try:
            # Query all comments for article
            response = self.comments_table.query(
                IndexName='article_id-created_at-index',
                KeyConditionExpression=Key('article_id').eq(article_id)
            )
            
            comments = response.get('Items', [])
            
            # Calculate statistics
            total_comments = len(comments)
            unique_authors = len(set(comment.get('author', '') for comment in comments))
            root_comments = len([c for c in comments if not c.get('parent_comment_id')])
            replies = total_comments - root_comments
            
            # Find most recent comment
            most_recent = None
            if comments:
                most_recent = max(comments, key=lambda x: x.get('created_at', ''))
            
            return {
                'total_comments': total_comments,
                'root_comments': root_comments,
                'replies': replies,
                'unique_authors': unique_authors,
                'most_recent_comment': most_recent.get('created_at') if most_recent else None,
                'most_recent_author': most_recent.get('author') if most_recent else None
            }
            
        except Exception as e:
            logger.error(f"Error getting thread statistics for {article_id}: {e}")
            return {
                'total_comments': 0,
                'root_comments': 0,
                'replies': 0,
                'unique_authors': 0,
                'most_recent_comment': None,
                'most_recent_author': None
            }


class CommentSearchManager:
    """Handles comment search and filtering."""
    
    def __init__(self, comments_table_name: str):
        self.comments_table = dynamodb.Table(comments_table_name)
    
    def search_comments(self, search_params: Dict[str, Any]) -> CommentResult:
        """Search comments with various filters."""
        try:
            # Extract search parameters
            article_id = search_params.get('article_id')
            author = search_params.get('author')
            content_search = search_params.get('content_search', '').lower()
            date_from = search_params.get('date_from')
            date_to = search_params.get('date_to')
            include_replies = search_params.get('include_replies', True)
            limit = min(search_params.get('limit', 100), 1000)  # Cap at 1000
            
            # Build query
            if article_id:
                # Search within specific article
                response = self.comments_table.query(
                    IndexName='article_id-created_at-index',
                    KeyConditionExpression=Key('article_id').eq(article_id),
                    Limit=limit
                )
            else:
                # Scan all comments (expensive operation)
                response = self.comments_table.scan(Limit=limit)
            
            comments = response.get('Items', [])
            
            # Apply filters
            filtered_comments = []
            for comment in comments:
                # Convert DynamoDB types
                comment = self._convert_from_dynamodb_types(comment)
                
                # Author filter
                if author and comment.get('author', '').lower() != author.lower():
                    continue
                
                # Content search filter
                if content_search and content_search not in comment.get('content', '').lower():
                    continue
                
                # Date range filter
                comment_date = comment.get('created_at', '')
                if date_from and comment_date < date_from:
                    continue
                if date_to and comment_date > date_to:
                    continue
                
                # Include/exclude replies filter
                if not include_replies and comment.get('parent_comment_id'):
                    continue
                
                filtered_comments.append(comment)
            
            # Sort by creation date (newest first)
            filtered_comments.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return CommentResult(
                success=True,
                operation="search_comments",
                comment_count=len(filtered_comments),
                comments=filtered_comments,
                metadata={
                    'search_params': search_params,
                    'total_scanned': len(comments),
                    'filtered_count': len(filtered_comments)
                }
            )
            
        except Exception as e:
            logger.error(f"Error searching comments: {e}")
            return CommentResult(
                success=False,
                operation="search_comments",
                errors=[f"Search error: {str(e)}"]
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


class CommentaryAPI:
    """Main commentary API orchestrating comment operations."""
    
    def __init__(self, comments_table_name: str, articles_table_name: str):
        self.comments_table = dynamodb.Table(comments_table_name)
        self.articles_table = dynamodb.Table(articles_table_name)
        self.thread_manager = ThreadManager(comments_table_name)
        self.search_manager = CommentSearchManager(comments_table_name)
    
    def create_comment(self, article_id: str, author: str, content: str,
                      parent_comment_id: Optional[str] = None,
                      visibility: str = 'public') -> CommentResult:
        """Create a new comment."""
        try:
            comment_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Creating comment {comment_id} for article {article_id} by {author}")
            
            # Validate comment content
            validation = CommentModerator.validate_comment_content(content)
            if not validation['is_valid']:
                return CommentResult(
                    success=False,
                    operation="create_comment",
                    article_id=article_id,
                    errors=[f"Content validation failed: {', '.join(validation['flags'])}"]
                )
            
            # Check if auto-moderation is needed
            is_moderated = CommentModerator.should_auto_moderate(validation)
            if is_moderated:
                visibility = 'moderated'
            
            # Verify article exists
            article_response = self.articles_table.get_item(Key={'article_id': article_id})
            if 'Item' not in article_response:
                return CommentResult(
                    success=False,
                    operation="create_comment",
                    article_id=article_id,
                    errors=[f"Article {article_id} not found"]
                )
            
            # Verify parent comment exists if specified
            thread_id = comment_id  # Root comment is its own thread
            depth = 0
            
            if parent_comment_id:
                parent_response = self.comments_table.get_item(Key={'comment_id': parent_comment_id})
                if 'Item' not in parent_response:
                    return CommentResult(
                        success=False,
                        operation="create_comment",
                        article_id=article_id,
                        errors=[f"Parent comment {parent_comment_id} not found"]
                    )
                
                parent_comment = parent_response['Item']
                # Inherit thread_id from parent, or use parent's comment_id if it's a root comment
                thread_id = parent_comment.get('thread_id', parent_comment_id)
                depth = parent_comment.get('depth', 0) + 1
                
                # Limit nesting depth
                if depth > 10:
                    return CommentResult(
                        success=False,
                        operation="create_comment",
                        article_id=article_id,
                        errors=["Maximum comment nesting depth exceeded"]
                    )
            
            # Create comment item
            comment_item = {
                'comment_id': comment_id,
                'article_id': article_id,
                'thread_id': thread_id,
                'author': author,
                'content': validation['sanitized_content'],
                'parent_comment_id': parent_comment_id,
                'depth': depth,
                'visibility': visibility,
                'is_moderated': is_moderated,
                'moderation_flags': validation['flags'],
                'created_at': now,
                'updated_at': now,
                'version': 1,
                'like_count': 0,
                'reply_count': 0
            }
            
            # Store comment
            self.comments_table.put_item(Item=comment_item)
            
            # Update parent comment reply count if this is a reply
            if parent_comment_id:
                self.comments_table.update_item(
                    Key={'comment_id': parent_comment_id},
                    UpdateExpression='ADD reply_count :inc',
                    ExpressionAttributeValues={':inc': 1}
                )
            
            # Update article comment count
            self.articles_table.update_item(
                Key={'article_id': article_id},
                UpdateExpression='ADD comment_count :inc',
                ExpressionAttributeValues={':inc': 1}
            )
            
            logger.info(f"Successfully created comment {comment_id}")
            
            return CommentResult(
                success=True,
                operation="create_comment",
                comment_id=comment_id,
                article_id=article_id,
                thread_id=thread_id,
                metadata={
                    'author': author,
                    'depth': depth,
                    'visibility': visibility,
                    'is_moderated': is_moderated,
                    'moderation_flags': validation['flags'],
                    'warnings': validation['warnings']
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating comment for article {article_id}: {e}")
            return CommentResult(
                success=False,
                operation="create_comment",
                article_id=article_id,
                errors=[f"Creation error: {str(e)}"]
            )
    
    def get_comments(self, article_id: str, include_moderated: bool = False,
                    format_as_tree: bool = True) -> CommentResult:
        """Get comments for an article."""
        try:
            logger.info(f"Retrieving comments for article {article_id}")
            
            # Query comments for article
            response = self.comments_table.query(
                IndexName='article_id-created_at-index',
                KeyConditionExpression=Key('article_id').eq(article_id)
            )
            
            comments = response.get('Items', [])
            
            # Convert DynamoDB types and filter
            filtered_comments = []
            for comment in comments:
                comment = self._convert_from_dynamodb_types(comment)
                
                # Filter moderated comments if not requested
                if not include_moderated and comment.get('visibility') == 'moderated':
                    continue
                
                filtered_comments.append(comment)
            
            # Format as tree or flat list
            if format_as_tree:
                comment_tree = self.thread_manager.build_comment_tree(filtered_comments)
                result_comments = comment_tree
            else:
                # Sort by creation date
                filtered_comments.sort(key=lambda x: x.get('created_at', ''))
                result_comments = filtered_comments
            
            # Get thread statistics
            thread_stats = self.thread_manager.get_thread_statistics(article_id)
            
            return CommentResult(
                success=True,
                operation="get_comments",
                article_id=article_id,
                comment_count=len(filtered_comments),
                comments=result_comments,
                metadata={
                    'format_as_tree': format_as_tree,
                    'include_moderated': include_moderated,
                    'thread_statistics': thread_stats
                }
            )
            
        except Exception as e:
            logger.error(f"Error retrieving comments for article {article_id}: {e}")
            return CommentResult(
                success=False,
                operation="get_comments",
                article_id=article_id,
                errors=[f"Retrieval error: {str(e)}"]
            )
    
    def update_comment(self, comment_id: str, updates: Dict[str, Any],
                      author: str) -> CommentResult:
        """Update an existing comment."""
        try:
            logger.info(f"Updating comment {comment_id}")
            
            # Get existing comment
            response = self.comments_table.get_item(Key={'comment_id': comment_id})
            if 'Item' not in response:
                return CommentResult(
                    success=False,
                    operation="update_comment",
                    comment_id=comment_id,
                    errors=[f"Comment {comment_id} not found"]
                )
            
            existing_comment = self._convert_from_dynamodb_types(response['Item'])
            
            # Verify author can update (only original author or admin)
            if existing_comment.get('author') != author and not author.endswith('@admin'):
                return CommentResult(
                    success=False,
                    operation="update_comment",
                    comment_id=comment_id,
                    errors=["Unauthorized to update this comment"]
                )
            
            # Validate content if being updated
            if 'content' in updates:
                validation = CommentModerator.validate_comment_content(updates['content'])
                if not validation['is_valid']:
                    return CommentResult(
                        success=False,
                        operation="update_comment",
                        comment_id=comment_id,
                        errors=[f"Content validation failed: {', '.join(validation['flags'])}"]
                    )
                updates['content'] = validation['sanitized_content']
            
            # Prepare update
            now = datetime.now(timezone.utc).isoformat()
            updates['updated_at'] = now
            updates['version'] = existing_comment.get('version', 1) + 1
            
            # Build update expression
            update_expression_parts = []
            expression_attribute_names = {}
            expression_attribute_values = {}
            
            for key, value in updates.items():
                attr_name = f"#{key}"
                attr_value = f":{key}"
                
                update_expression_parts.append(f"{attr_name} = {attr_value}")
                expression_attribute_names[attr_name] = key
                expression_attribute_values[attr_value] = self._convert_to_dynamodb_type(value)
            
            update_expression = "SET " + ", ".join(update_expression_parts)
            
            # Update comment
            self.comments_table.update_item(
                Key={'comment_id': comment_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values
            )
            
            logger.info(f"Successfully updated comment {comment_id}")
            
            return CommentResult(
                success=True,
                operation="update_comment",
                comment_id=comment_id,
                article_id=existing_comment.get('article_id'),
                metadata={
                    'updated_fields': list(updates.keys()),
                    'new_version': updates['version']
                }
            )
            
        except Exception as e:
            logger.error(f"Error updating comment {comment_id}: {e}")
            return CommentResult(
                success=False,
                operation="update_comment",
                comment_id=comment_id,
                errors=[f"Update error: {str(e)}"]
            )
    
    def delete_comment(self, comment_id: str, author: str) -> CommentResult:
        """Delete a comment (soft delete)."""
        try:
            logger.info(f"Deleting comment {comment_id}")
            
            # Get existing comment
            response = self.comments_table.get_item(Key={'comment_id': comment_id})
            if 'Item' not in response:
                return CommentResult(
                    success=False,
                    operation="delete_comment",
                    comment_id=comment_id,
                    errors=[f"Comment {comment_id} not found"]
                )
            
            existing_comment = self._convert_from_dynamodb_types(response['Item'])
            
            # Verify author can delete (only original author or admin)
            if existing_comment.get('author') != author and not author.endswith('@admin'):
                return CommentResult(
                    success=False,
                    operation="delete_comment",
                    comment_id=comment_id,
                    errors=["Unauthorized to delete this comment"]
                )
            
            # Soft delete - mark as deleted but keep record
            now = datetime.now(timezone.utc).isoformat()
            self.comments_table.update_item(
                Key={'comment_id': comment_id},
                UpdateExpression='SET visibility = :deleted, deleted_at = :now, updated_at = :now',
                ExpressionAttributeValues={
                    ':deleted': 'deleted',
                    ':now': now
                }
            )
            
            # Update article comment count
            article_id = existing_comment.get('article_id')
            if article_id:
                self.articles_table.update_item(
                    Key={'article_id': article_id},
                    UpdateExpression='ADD comment_count :dec',
                    ExpressionAttributeValues={':dec': -1}
                )
            
            logger.info(f"Successfully deleted comment {comment_id}")
            
            return CommentResult(
                success=True,
                operation="delete_comment",
                comment_id=comment_id,
                article_id=article_id,
                metadata={'deleted_at': now}
            )
            
        except Exception as e:
            logger.error(f"Error deleting comment {comment_id}: {e}")
            return CommentResult(
                success=False,
                operation="delete_comment",
                comment_id=comment_id,
                errors=[f"Deletion error: {str(e)}"]
            )
    
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
    """Lambda handler for commentary API operations."""
    try:
        # Extract operation
        operation = event.get('operation', 'create_comment')
        
        # Get configuration from environment
        comments_table = os.environ.get('COMMENTS_TABLE', 'sentinel-comments')
        articles_table = os.environ.get('ARTICLES_TABLE', 'sentinel-articles')
        
        # Initialize commentary API
        api = CommentaryAPI(comments_table, articles_table)
        
        # Route to appropriate operation
        if operation == 'create_comment':
            article_id = event.get('article_id')
            author = event.get('author')
            content = event.get('content')
            parent_comment_id = event.get('parent_comment_id')
            visibility = event.get('visibility', 'public')
            
            if not all([article_id, author, content]):
                raise ValueError("article_id, author, and content are required")
            
            result = api.create_comment(article_id, author, content, parent_comment_id, visibility)
            
        elif operation == 'get_comments':
            article_id = event.get('article_id')
            include_moderated = event.get('include_moderated', False)
            format_as_tree = event.get('format_as_tree', True)
            
            if not article_id:
                raise ValueError("article_id is required")
            
            result = api.get_comments(article_id, include_moderated, format_as_tree)
            
        elif operation == 'update_comment':
            comment_id = event.get('comment_id')
            updates = event.get('updates', {})
            author = event.get('author')
            
            if not all([comment_id, author]):
                raise ValueError("comment_id and author are required")
            
            result = api.update_comment(comment_id, updates, author)
            
        elif operation == 'delete_comment':
            comment_id = event.get('comment_id')
            author = event.get('author')
            
            if not all([comment_id, author]):
                raise ValueError("comment_id and author are required")
            
            result = api.delete_comment(comment_id, author)
            
        elif operation == 'search_comments':
            search_params = event.get('search_params', {})
            
            result = api.search_manager.search_comments(search_params)
            
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        # Format response
        return {
            'statusCode': 200 if result.success else 400,
            'body': {
                'success': result.success,
                'operation': result.operation,
                'comment_id': result.comment_id,
                'article_id': result.article_id,
                'thread_id': result.thread_id,
                'comment_count': result.comment_count,
                'comments': result.comments,
                'errors': result.errors,
                'warnings': result.warnings,
                'metadata': result.metadata
            }
        }
        
    except Exception as e:
        logger.error(f"Commentary API operation failed: {e}")
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
        "operation": "create_comment",
        "article_id": "test-article-123",
        "author": "analyst@example.com",
        "content": "This article provides valuable insights into the Azure vulnerability. The CVE details are particularly useful for our security team.",
        "visibility": "public"
    }
    
    os.environ.update({
        'COMMENTS_TABLE': 'test-comments',
        'ARTICLES_TABLE': 'test-articles'
    })
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))