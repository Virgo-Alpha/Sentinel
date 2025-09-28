"""
Unit tests for FeedParser Lambda tool.
"""

import json
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from src.lambda_tools.feed_parser import (
    FeedParser, 
    ContentNormalizer, 
    FeedParserError,
    lambda_handler
)


class TestContentNormalizer:
    """Test cases for ContentNormalizer class."""
    
    def setup_method(self):
        self.normalizer = ContentNormalizer()
    
    def test_normalize_html_basic(self):
        """Test basic HTML normalization."""
        html = """
        <html>
            <head><title>Test Title</title></head>
            <body>
                <h1>Main Heading</h1>
                <p>This is a paragraph with <a href="http://example.com">a link</a>.</p>
                <script>alert('remove me');</script>
                <style>body { color: red; }</style>
            </body>
        </html>
        """
        
        result = self.normalizer.normalize_html(html)
        
        assert 'normalized_text' in result
        assert 'metadata' in result
        assert 'extracted_urls' in result
        assert 'word_count' in result
        assert 'character_count' in result
        
        # Check that script and style are removed
        assert 'alert' not in result['normalized_text']
        assert 'color: red' not in result['normalized_text']
        
        # Check that content is preserved
        assert 'Main Heading' in result['normalized_text']
        assert 'This is a paragraph' in result['normalized_text']
        
        # Check URL extraction
        assert 'http://example.com' in result['extracted_urls']
        
        # Check metadata extraction
        assert result['metadata']['html_title'] == 'Test Title'
        assert len(result['metadata']['links']) > 0
    
    def test_normalize_html_empty(self):
        """Test HTML normalization with empty content."""
        result = self.normalizer.normalize_html("")
        
        assert result['normalized_text'] == ""
        assert result['word_count'] == 0
        assert result['character_count'] == 0
        assert result['extracted_urls'] == []
    
    def test_normalize_html_malformed(self):
        """Test HTML normalization with malformed HTML."""
        html = "<p>Unclosed paragraph <div>Nested without closing"
        
        result = self.normalizer.normalize_html(html)
        
        assert 'Unclosed paragraph' in result['normalized_text']
        assert 'Nested without closing' in result['normalized_text']
        assert result['word_count'] > 0
    
    def test_extract_metadata_comprehensive(self):
        """Test comprehensive metadata extraction."""
        html = """
        <html>
            <head>
                <title>Test Article</title>
                <meta name="description" content="Test description">
                <meta property="og:title" content="OG Title">
                <meta name="author" content="Test Author">
            </head>
            <body>
                <a href="http://example.com">Link 1</a>
                <a href="http://test.com">Link 2</a>
                <img src="image1.jpg" alt="Image 1" title="First Image">
                <img src="image2.jpg" alt="Image 2">
            </body>
        </html>
        """
        
        result = self.normalizer.normalize_html(html)
        metadata = result['metadata']
        
        assert metadata['html_title'] == 'Test Article'
        assert metadata['meta_description'] == 'Test description'
        assert metadata['meta_og:title'] == 'OG Title'
        assert metadata['meta_author'] == 'Test Author'
        assert len(metadata['links']) == 2
        assert len(metadata['images']) == 2
        assert metadata['images'][0]['alt'] == 'Image 1'
        assert metadata['images'][0]['title'] == 'First Image'


class TestFeedParser:
    """Test cases for FeedParser class."""
    
    def setup_method(self):
        self.bucket_name = 'test-content-bucket'
        self.parser = FeedParser(self.bucket_name)
    
    def test_parse_date_valid(self):
        """Test date parsing with valid date tuple."""
        mock_entry = Mock()
        mock_entry.published_parsed = (2024, 1, 15, 10, 30, 0, 0, 15, 0)
        mock_entry.updated_parsed = None
        mock_entry.created_parsed = None
        
        result = self.parser._parse_date(mock_entry)
        
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
    
    def test_parse_date_fallback(self):
        """Test date parsing with fallback to updated_parsed."""
        mock_entry = Mock()
        mock_entry.published_parsed = None
        mock_entry.updated_parsed = (2024, 2, 20, 15, 45, 30, 0, 51, 0)
        mock_entry.created_parsed = None
        
        result = self.parser._parse_date(mock_entry)
        
        assert result is not None
        assert result.year == 2024
        assert result.month == 2
        assert result.day == 20
    
    def test_parse_date_none(self):
        """Test date parsing when no date is available."""
        mock_entry = Mock()
        mock_entry.published_parsed = None
        mock_entry.updated_parsed = None
        mock_entry.created_parsed = None
        mock_entry.published = None
        mock_entry.updated = None
        mock_entry.created = None
        
        result = self.parser._parse_date(mock_entry)
        
        assert result is None
    
    def test_extract_content_priority(self):
        """Test content extraction priority order."""
        mock_entry = Mock()
        
        # Test content field priority
        mock_content = Mock()
        mock_content.value = "Content from content field"
        mock_entry.content = [mock_content]
        mock_entry.description = "Description content"
        mock_entry.summary = "Summary content"
        mock_entry.title = "Title content"
        
        result = self.parser._extract_content(mock_entry)
        assert result == "Content from content field"
        
        # Test description fallback
        mock_entry.content = None
        result = self.parser._extract_content(mock_entry)
        assert result == "Description content"
        
        # Test summary fallback
        mock_entry.description = None
        result = self.parser._extract_content(mock_entry)
        assert result == "Summary content"
        
        # Test title fallback
        mock_entry.summary = None
        result = self.parser._extract_content(mock_entry)
        assert result == "Title content"
    
    def test_get_canonical_url(self):
        """Test canonical URL generation."""
        # Test absolute URL
        result = self.parser._get_canonical_url("https://example.com/article", "https://base.com")
        assert result == "https://example.com/article"
        
        # Test relative URL resolution
        result = self.parser._get_canonical_url("/article", "https://base.com")
        assert result == "https://base.com/article"
        
        # Test relative URL without base
        result = self.parser._get_canonical_url("/article", "")
        assert result == "/article"
    
    @patch('src.lambda_tools.feed_parser.s3_client')
    def test_store_content_s3_success(self, mock_s3):
        """Test successful S3 content storage."""
        mock_s3.put_object.return_value = {}
        
        result = self.parser._store_content_s3("test content", "test/key.html")
        
        assert result == f"s3://{self.bucket_name}/test/key.html"
        mock_s3.put_object.assert_called_once_with(
            Bucket=self.bucket_name,
            Key="test/key.html",
            Body=b"test content",
            ContentType="text/html",
            ServerSideEncryption="AES256"
        )
    
    @patch('src.lambda_tools.feed_parser.s3_client')
    def test_store_content_s3_failure(self, mock_s3):
        """Test S3 storage failure handling."""
        mock_s3.put_object.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'PutObject'
        )
        
        with pytest.raises(FeedParserError, match="S3 storage failed"):
            self.parser._store_content_s3("test content", "test/key.html")
    
    @patch('requests.Session.get')
    @patch('feedparser.parse')
    @patch('src.lambda_tools.feed_parser.s3_client')
    def test_parse_feed_success(self, mock_s3, mock_feedparser, mock_get):
        """Test successful feed parsing."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"<rss>test feed</rss>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Mock feedparser response
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.bozo_exception = None
        mock_feed.feed = Mock()
        mock_feed.feed.title = "Test Feed"
        mock_feed.feed.description = "Test Description"
        mock_feed.feed.link = "https://example.com"
        
        # Mock feed entry
        mock_entry = Mock()
        mock_entry.title = "Test Article"
        mock_entry.link = "https://example.com/article"
        mock_entry.published_parsed = (2024, 1, 15, 10, 30, 0, 0, 15, 0)
        mock_entry.author = "Test Author"
        mock_entry.tags = []
        mock_entry.id = "test-id"
        mock_entry.summary = "Test summary"
        mock_entry.content = [Mock(value="<p>Test content</p>")]
        mock_entry.description = None
        
        mock_feed.entries = [mock_entry]
        mock_feedparser.return_value = mock_feed
        
        # Mock S3 operations
        mock_s3.put_object.return_value = {}
        
        result = self.parser.parse_feed("https://example.com/feed.xml", "test-feed")
        
        assert len(result) == 1
        article = result[0]
        assert article['title'] == "Test Article"
        assert article['url'] == "https://example.com/article"
        assert article['author'] == "Test Author"
        assert 'content_hash' in article
        assert 'raw_s3_uri' in article
        assert 'normalized_s3_uri' in article
    
    @patch('requests.Session.get')
    def test_parse_feed_network_error(self, mock_get):
        """Test feed parsing with network error."""
        mock_get.side_effect = Exception("Network error")
        
        with pytest.raises(FeedParserError, match="Feed parsing failed"):
            self.parser.parse_feed("https://example.com/feed.xml", "test-feed")
    
    @patch('requests.Session.get')
    @patch('feedparser.parse')
    def test_parse_feed_with_since_filter(self, mock_feedparser, mock_get):
        """Test feed parsing with since date filter."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"<rss>test feed</rss>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Mock feedparser response
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.bozo_exception = None
        mock_feed.feed = Mock()
        mock_feed.feed.title = "Test Feed"
        
        # Mock old entry (should be filtered out)
        old_entry = Mock()
        old_entry.title = "Old Article"
        old_entry.link = "https://example.com/old"
        old_entry.published_parsed = (2023, 1, 1, 0, 0, 0, 0, 1, 0)  # Old date
        
        # Mock new entry (should be included)
        new_entry = Mock()
        new_entry.title = "New Article"
        new_entry.link = "https://example.com/new"
        new_entry.published_parsed = (2024, 6, 1, 0, 0, 0, 0, 153, 0)  # New date
        new_entry.author = ""
        new_entry.tags = []
        new_entry.id = "new-id"
        new_entry.summary = ""
        new_entry.content = [Mock(value="New content")]
        
        mock_feed.entries = [old_entry, new_entry]
        mock_feedparser.return_value = mock_feed
        
        # Mock S3 operations
        with patch('src.lambda_tools.feed_parser.s3_client') as mock_s3:
            mock_s3.put_object.return_value = {}
            
            since_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            result = self.parser.parse_feed("https://example.com/feed.xml", "test-feed", since_date)
            
            assert len(result) == 1
            assert result[0]['title'] == "New Article"


class TestLambdaHandler:
    """Test cases for Lambda handler function."""
    
    def test_lambda_handler_missing_params(self):
        """Test Lambda handler with missing parameters."""
        event = {'feed_id': 'test-feed'}  # Missing feed_url
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 500
        assert result['body']['success'] is False
        assert 'feed_url' in result['body']['error']
    
    def test_lambda_handler_missing_bucket(self):
        """Test Lambda handler with missing S3 bucket environment variable."""
        event = {
            'feed_id': 'test-feed',
            'feed_url': 'https://example.com/feed.xml'
        }
        
        # Ensure CONTENT_BUCKET is not set
        with patch.dict(os.environ, {}, clear=True):
            result = lambda_handler(event, None)
            
            assert result['statusCode'] == 500
            assert result['body']['success'] is False
            assert 'CONTENT_BUCKET' in result['body']['error']
    
    @patch('src.lambda_tools.feed_parser.FeedParser')
    def test_lambda_handler_success(self, mock_parser_class):
        """Test successful Lambda handler execution."""
        # Mock parser instance
        mock_parser = Mock()
        mock_articles = [
            {
                'title': 'Test Article',
                'url': 'https://example.com/article',
                'content_hash': 'abc123'
            }
        ]
        mock_parser.parse_feed.return_value = mock_articles
        mock_parser_class.return_value = mock_parser
        
        event = {
            'feed_id': 'test-feed',
            'feed_url': 'https://example.com/feed.xml',
            'since': '2024-01-01T00:00:00Z'
        }
        
        with patch.dict(os.environ, {'CONTENT_BUCKET': 'test-bucket'}):
            result = lambda_handler(event, None)
            
            assert result['statusCode'] == 200
            assert result['body']['success'] is True
            assert result['body']['articles_count'] == 1
            assert result['body']['articles'] == mock_articles
            
            # Verify parser was called correctly
            mock_parser.parse_feed.assert_called_once()
            args = mock_parser.parse_feed.call_args[0]
            assert args[0] == 'https://example.com/feed.xml'
            assert args[1] == 'test-feed'
            assert args[2] is not None  # since parameter
    
    def test_lambda_handler_invalid_since(self):
        """Test Lambda handler with invalid since parameter."""
        event = {
            'feed_id': 'test-feed',
            'feed_url': 'https://example.com/feed.xml',
            'since': 'invalid-date'
        }
        
        with patch.dict(os.environ, {'CONTENT_BUCKET': 'test-bucket'}):
            with patch('src.lambda_tools.feed_parser.FeedParser') as mock_parser_class:
                mock_parser = Mock()
                mock_parser.parse_feed.return_value = []
                mock_parser_class.return_value = mock_parser
                
                result = lambda_handler(event, None)
                
                # Should succeed but ignore invalid since parameter
                assert result['statusCode'] == 200
                
                # Verify since parameter was None (ignored)
                args = mock_parser.parse_feed.call_args[0]
                assert args[2] is None  # since parameter should be None
    
    @patch('src.lambda_tools.feed_parser.FeedParser')
    def test_lambda_handler_parser_error(self, mock_parser_class):
        """Test Lambda handler with parser error."""
        mock_parser = Mock()
        mock_parser.parse_feed.side_effect = FeedParserError("Parse failed")
        mock_parser_class.return_value = mock_parser
        
        event = {
            'feed_id': 'test-feed',
            'feed_url': 'https://example.com/feed.xml'
        }
        
        with patch.dict(os.environ, {'CONTENT_BUCKET': 'test-bucket'}):
            result = lambda_handler(event, None)
            
            assert result['statusCode'] == 500
            assert result['body']['success'] is False
            assert 'Parse failed' in result['body']['error']
            assert result['body']['error_type'] == 'FeedParserError'


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def setup_method(self):
        self.normalizer = ContentNormalizer()
        self.parser = FeedParser('test-bucket')
    
    def test_normalize_html_error(self):
        """Test HTML normalization error handling."""
        # Test with None input
        with pytest.raises(FeedParserError):
            self.normalizer.normalize_html(None)
    
    def test_feed_parser_malformed_feed(self):
        """Test feed parser with malformed feed data."""
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.content = b"not a valid feed"
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            with patch('feedparser.parse') as mock_feedparser:
                mock_feed = Mock()
                mock_feed.bozo = True
                mock_feed.bozo_exception = Exception("Malformed feed")
                mock_feed.feed = Mock()
                mock_feed.entries = []
                mock_feedparser.return_value = mock_feed
                
                # Should not raise exception, just log warning
                result = self.parser.parse_feed("https://example.com/bad-feed.xml", "test-feed")
                assert result == []