"""
Unit tests for DedupTool Lambda function.

Tests both heuristic and semantic deduplication functionality including
URL comparison, title similarity, domain clustering, and OpenSearch k-NN integration.
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from moto import mock_aws
import boto3

# Import the modules to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock the OpenSearch dependencies before importing the module
sys.modules['opensearchpy'] = Mock()
sys.modules['aws_requests_auth'] = Mock()
sys.modules['aws_requests_auth.aws_auth'] = Mock()

from lambda_tools.dedup_tool import (
    DedupTool, HeuristicDeduplicator, ClusterManager,
    ArticleFingerprint, DuplicationResult, lambda_handler
)


class TestArticleFingerprint:
    """Test ArticleFingerprint data class."""
    
    def test_article_fingerprint_creation(self):
        """Test creating an ArticleFingerprint."""
        published_at = datetime.utcnow()
        fingerprint = ArticleFingerprint(
            article_id="test-123",
            url="https://example.com/article",
            canonical_url="https://example.com/article",
            title="Test Article",
            normalized_title="test article",
            domain="example.com",
            published_at=published_at,
            content_hash="abc123",
            title_hash="def456",
            url_hash="ghi789"
        )
        
        assert fingerprint.article_id == "test-123"
        assert fingerprint.domain == "example.com"
        assert fingerprint.published_at == published_at


class TestHeuristicDeduplicator:
    """Test heuristic deduplication functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.deduplicator = HeuristicDeduplicator()
        self.base_time = datetime.utcnow()
        
        # Create test articles
        self.article1 = ArticleFingerprint(
            article_id="article-1",
            url="https://example.com/security-breach-2024",
            canonical_url="https://example.com/security-breach-2024",
            title="Major Security Breach Affects Users",
            normalized_title="major security breach affects users",
            domain="example.com",
            published_at=self.base_time,
            content_hash="hash1",
            title_hash="title1",
            url_hash="url1"
        )
        
        self.article2 = ArticleFingerprint(
            article_id="article-2",
            url="https://example.com/security-breach-2024",  # Same URL
            canonical_url="https://example.com/security-breach-2024",
            title="Security Breach: Major Impact on Users",
            normalized_title="security breach major impact on users",
            domain="example.com",
            published_at=self.base_time - timedelta(hours=1),
            content_hash="hash2",
            title_hash="title2",
            url_hash="url2"
        )
        
        self.article3 = ArticleFingerprint(
            article_id="article-3",
            url="https://different.com/other-news",
            canonical_url="https://different.com/other-news",
            title="Completely Different News",
            normalized_title="completely different news",
            domain="different.com",
            published_at=self.base_time - timedelta(hours=2),
            content_hash="hash3",
            title_hash="title3",
            url_hash="url3"
        )
    
    def test_exact_url_match(self):
        """Test exact URL duplicate detection."""
        existing_articles = [self.article2, self.article3]
        result = self.deduplicator.find_heuristic_duplicates(self.article1, existing_articles)
        
        assert result.is_duplicate is True
        assert result.duplicate_of == "article-2"
        assert result.similarity_score == 1.0
        assert "exact_url_match" in result.method
    
    def test_canonical_url_match(self):
        """Test canonical URL duplicate detection."""
        # Create article with different URL but same canonical
        article_variant = ArticleFingerprint(
            article_id="article-variant",
            url="https://example.com/security-breach-2024?utm_source=twitter",
            canonical_url="https://example.com/security-breach-2024",
            title="Different Title",
            normalized_title="different title",
            domain="example.com",
            published_at=self.base_time,
            content_hash="hash_variant",
            title_hash="title_variant",
            url_hash="url_variant"
        )
        
        existing_articles = [self.article2]
        result = self.deduplicator.find_heuristic_duplicates(article_variant, existing_articles)
        
        assert result.is_duplicate is True
        assert result.duplicate_of == "article-2"
        assert "canonical_url_match" in result.method
    
    def test_title_similarity_same_domain(self):
        """Test title similarity detection within same domain."""
        # Create similar title article
        similar_article = ArticleFingerprint(
            article_id="similar-article",
            url="https://example.com/different-url",
            canonical_url="https://example.com/different-url",
            title="Major Security Breach Impacts Users",  # Very similar title
            normalized_title="major security breach impacts users",
            domain="example.com",
            published_at=self.base_time,
            content_hash="hash_similar",
            title_hash="title_similar",
            url_hash="url_similar"
        )
        
        existing_articles = [self.article1]
        result = self.deduplicator.find_heuristic_duplicates(similar_article, existing_articles)
        
        assert result.is_duplicate is True
        assert result.duplicate_of == "article-1"
        assert result.similarity_score >= 0.85
        assert "title_similarity" in result.method
    
    def test_no_duplicate_found(self):
        """Test when no duplicates are found."""
        existing_articles = [self.article3]  # Completely different article
        result = self.deduplicator.find_heuristic_duplicates(self.article1, existing_articles)
        
        assert result.is_duplicate is False
        assert result.similarity_score == 0.0
        assert result.method == "heuristic"
    
    def test_time_window_filtering(self):
        """Test that articles outside time window are filtered out."""
        # Create old article (outside 72-hour window)
        old_article = ArticleFingerprint(
            article_id="old-article",
            url="https://example.com/security-breach-2024",  # Same URL
            canonical_url="https://example.com/security-breach-2024",
            title="Old Security Breach",
            normalized_title="old security breach",
            domain="example.com",
            published_at=self.base_time - timedelta(days=5),  # 5 days old
            content_hash="hash_old",
            title_hash="title_old",
            url_hash="url_old"
        )
        
        existing_articles = [old_article]
        result = self.deduplicator.find_heuristic_duplicates(self.article1, existing_articles)
        
        assert result.is_duplicate is False  # Should not match due to time window
    
    def test_title_similarity_calculation(self):
        """Test title similarity calculation."""
        similarity = self.deduplicator._calculate_title_similarity(
            "major security breach affects users",
            "major security breach impacts users"
        )
        assert similarity > 0.8  # Should be high similarity
    
    def test_url_normalization(self):
        """Test URL path normalization."""
        # Test that numeric IDs are replaced
        normalized1 = self.deduplicator._normalize_url_path("https://news.com/article/123/details")
        assert "article/ID/details" in normalized1
        
        # Test that paths are lowercased and stripped
        normalized2 = self.deduplicator._normalize_url_path("https://news.com/PATH/")
        assert "path" in normalized2


class TestSemanticDeduplicator:
    """Test semantic deduplication functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.opensearch_endpoint = "https://test-opensearch.us-east-1.es.amazonaws.com"
        self.opensearch_index = "test-vectors"
        
    @patch('lambda_tools.dedup_tool.SemanticDeduplicator._generate_embedding')
    @patch('lambda_tools.dedup_tool.SemanticDeduplicator._create_opensearch_client')
    def test_semantic_duplicate_found(self, mock_create_client, mock_generate_embedding):
        """Test semantic duplicate detection."""
        # Import SemanticDeduplicator here to avoid import issues
        from lambda_tools.dedup_tool import SemanticDeduplicator
        
        # Mock embedding generation
        mock_generate_embedding.return_value = [0.1, 0.2, 0.3] * 512  # Mock 1536-dim embedding
        
        # Mock OpenSearch client
        mock_opensearch = Mock()
        mock_create_client.return_value = mock_opensearch
        
        # Mock search response with high similarity
        mock_opensearch.search.return_value = {
            'hits': {
                'hits': [
                    {
                        '_score': 0.92,  # High similarity
                        '_source': {
                            'article_id': 'similar-article-123',
                            'title': 'Similar Security Breach Article',
                            'url': 'https://example.com/similar',
                            'published_at': '2024-01-15T10:00:00Z'
                        }
                    }
                ]
            }
        }
        
        deduplicator = SemanticDeduplicator(self.opensearch_endpoint, self.opensearch_index)
        result = deduplicator.find_semantic_duplicates(
            "This is a test article about security breaches",
            "Security Breach Test",
            "test-article-456"
        )
        
        assert result.is_duplicate is True
        assert result.duplicate_of == "similar-article-123"
        assert result.similarity_score == 0.92
        assert result.method == "semantic"
    
    @patch('lambda_tools.dedup_tool.SemanticDeduplicator._generate_embedding')
    @patch('lambda_tools.dedup_tool.SemanticDeduplicator._create_opensearch_client')
    def test_embedding_generation_failure(self, mock_create_client, mock_generate_embedding):
        """Test handling of embedding generation failure."""
        # Import SemanticDeduplicator here to avoid import issues
        from lambda_tools.dedup_tool import SemanticDeduplicator
        
        # Mock embedding generation to raise an exception
        mock_generate_embedding.side_effect = Exception("Bedrock error")
        
        deduplicator = SemanticDeduplicator(self.opensearch_endpoint, self.opensearch_index)
        result = deduplicator.find_semantic_duplicates(
            "Test content",
            "Test title",
            "test-article"
        )
        
        # Should return non-duplicate result on failure
        assert result.is_duplicate is False
        assert "failed" in result.rationale.lower()


class TestClusterManager:
    """Test cluster management functionality."""
    
    def setup_method(self, method):
        """Set up test fixtures."""
        self.table_name = 'test-articles'
        self.cluster_manager = ClusterManager(self.table_name)
    
    @patch('lambda_tools.dedup_tool.ClusterManager._update_article_cluster')
    def test_create_new_cluster(self, mock_update):
        """Test creating a new cluster for non-duplicate article."""
        mock_update.return_value = None
        
        duplicate_result = DuplicationResult(
            is_duplicate=False,
            similarity_score=0.0,
            method="heuristic",
            rationale="No duplicates found"
        )
        
        cluster_id = self.cluster_manager.assign_cluster("article-123", duplicate_result)
        
        assert cluster_id == "cluster_article-123"
        
        # Verify update was called correctly
        mock_update.assert_called_once_with("article-123", "cluster_article-123", None)
    
    @patch('lambda_tools.dedup_tool.ClusterManager._update_article_cluster')
    @patch('lambda_tools.dedup_tool.ClusterManager._get_article_cluster')
    def test_assign_to_existing_cluster(self, mock_get_cluster, mock_update):
        """Test assigning article to existing cluster."""
        # Mock that the original article already has a cluster
        mock_get_cluster.return_value = "cluster_original-article"
        mock_update.return_value = None
        
        # Create duplicate result
        duplicate_result = DuplicationResult(
            is_duplicate=True,
            duplicate_of="original-article",
            similarity_score=0.95,
            method="heuristic",
            rationale="Exact URL match"
        )
        
        cluster_id = self.cluster_manager.assign_cluster("duplicate-article", duplicate_result)
        
        assert cluster_id == "cluster_original-article"
        
        # Verify methods were called correctly
        mock_get_cluster.assert_called_once_with("original-article")
        mock_update.assert_called_once_with("duplicate-article", "cluster_original-article", "original-article")
    
    @patch('lambda_tools.dedup_tool.ClusterManager._update_article_cluster')
    @patch('lambda_tools.dedup_tool.ClusterManager._get_article_cluster')
    def test_create_cluster_for_original_when_none_exists(self, mock_get_cluster, mock_update):
        """Test creating a new cluster when original article has no cluster."""
        # Mock that the original article has no cluster yet
        mock_get_cluster.return_value = None
        mock_update.return_value = None
        
        # Create duplicate result
        duplicate_result = DuplicationResult(
            is_duplicate=True,
            duplicate_of="original-article",
            similarity_score=0.95,
            method="heuristic",
            rationale="Exact URL match"
        )
        
        cluster_id = self.cluster_manager.assign_cluster("duplicate-article", duplicate_result)
        
        assert cluster_id == "cluster_original-article"
        
        # Verify methods were called correctly - should create cluster for original first
        mock_get_cluster.assert_called_once_with("original-article")
        assert mock_update.call_count == 2  # Once for original, once for duplicate
        
        # Check the calls
        calls = mock_update.call_args_list
        assert calls[0] == (("original-article", "cluster_original-article", None),)
        assert calls[1] == (("duplicate-article", "cluster_original-article", "original-article"),)


class TestDedupTool:
    """Test main DedupTool orchestration."""
    
    @patch('lambda_tools.dedup_tool.DedupTool._get_existing_articles')
    @patch('lambda_tools.dedup_tool.SemanticDeduplicator.find_semantic_duplicates')
    @patch('lambda_tools.dedup_tool.SemanticDeduplicator.store_article_embedding')
    def test_find_duplicates_heuristic_match(self, mock_store_embedding, mock_semantic_dedup, mock_get_existing):
        """Test finding duplicates with heuristic match."""
        from datetime import datetime
        
        # Mock existing articles
        existing_article = ArticleFingerprint(
            article_id='existing-article',
            url='https://example.com/test',
            canonical_url='https://example.com/test',
            title='Test Article',
            normalized_title='test article',
            domain='example.com',
            published_at=datetime.utcnow(),
            content_hash='hash123',
            title_hash='title123',
            url_hash='url123'
        )
        mock_get_existing.return_value = [existing_article]
        
        # Mock semantic deduplication to return no duplicates (so heuristic takes precedence)
        mock_semantic_dedup.return_value = DuplicationResult(
            is_duplicate=False,
            similarity_score=0.0,
            method="semantic",
            rationale="No semantic duplicates found"
        )
        mock_store_embedding.return_value = True
        
        # Create test article data
        article_data = {
            'article_id': 'new-article',
            'url': 'https://example.com/test',  # Same URL as existing
            'canonical_url': 'https://example.com/test',
            'title': 'Test Article Duplicate',
            'published_at': datetime.utcnow().isoformat(),
            'content_hash': 'hash456',
            'normalized_content': 'Test content'
        }
        
        dedup_tool = DedupTool("dummy-table", "dummy-opensearch", "dummy-index")
        result = dedup_tool.find_duplicates(article_data)
        
        assert result.is_duplicate is True
        assert result.duplicate_of == 'existing-article'
        assert "heuristic" in result.method
    
    def test_create_article_fingerprint(self):
        """Test creating article fingerprint from data."""
        article_data = {
            'article_id': 'test-123',
            'url': 'https://example.com/article?utm_source=twitter',
            'canonical_url': 'https://example.com/article',
            'title': 'Breaking: Major Security Breach!',
            'published_at': '2024-01-15T10:30:00Z',
            'content_hash': 'abc123'
        }
        
        dedup_tool = DedupTool("dummy-table", "dummy-opensearch", "dummy-index")
        fingerprint = dedup_tool._create_article_fingerprint(article_data)
        
        assert fingerprint.article_id == 'test-123'
        assert fingerprint.url == 'https://example.com/article?utm_source=twitter'
        assert fingerprint.canonical_url == 'https://example.com/article'
        assert fingerprint.normalized_title == 'major security breach'
        assert fingerprint.domain == 'example.com'
    
    def test_normalize_title(self):
        """Test title normalization."""
        dedup_tool = DedupTool("dummy-table", "dummy-opensearch", "dummy-index")
        
        test_cases = [
            ("Breaking: Security Alert!", "security alert"),
            ("URGENT: System Down", "system down"),
            ("Update: Patch Available", "patch available"),
            ("Exclusive: New Vulnerability", "new vulnerability"),
            ("Multiple   Spaces", "multiple spaces"),
            ("Special!@#$%Characters", "special characters")
        ]
        
        for original, expected in test_cases:
            result = dedup_tool._normalize_title(original)
            assert result == expected
    
    def test_extract_domain(self):
        """Test domain extraction from URLs."""
        dedup_tool = DedupTool("dummy-table", "dummy-opensearch", "dummy-index")
        
        test_cases = [
            ("https://example.com/path", "example.com"),
            ("http://subdomain.example.com/path", "subdomain.example.com"),
            ("https://Example.COM/PATH", "example.com"),
            ("invalid-url", ""),
            ("", "")
        ]
        
        for url, expected in test_cases:
            result = dedup_tool._extract_domain(url)
            assert result == expected


class TestLambdaHandler:
    """Test Lambda handler function."""
    
    @patch.dict(os.environ, {
        'ARTICLES_TABLE': 'test-articles',
        'OPENSEARCH_ENDPOINT': 'https://test-opensearch.us-east-1.es.amazonaws.com',
        'OPENSEARCH_INDEX_VECTORS': 'test-vectors'
    })
    @patch('lambda_tools.dedup_tool.DedupTool')
    def test_lambda_handler_success(self, mock_dedup_tool_class):
        """Test successful Lambda handler execution."""
        # Mock DedupTool
        mock_dedup_tool = Mock()
        mock_dedup_tool_class.return_value = mock_dedup_tool
        
        # Mock deduplication result
        mock_result = DuplicationResult(
            is_duplicate=True,
            duplicate_of="existing-article",
            similarity_score=0.95,
            method="heuristic_exact_url_match",
            rationale="Exact URL match found"
        )
        mock_dedup_tool.find_duplicates.return_value = mock_result
        mock_dedup_tool.assign_cluster.return_value = "cluster_existing-article"
        
        # Test event
        event = {
            'article_id': 'test-article',
            'url': 'https://example.com/test',
            'title': 'Test Article',
            'published_at': '2024-01-15T10:30:00Z',
            'content_hash': 'abc123',
            'normalized_content': 'Test content'
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 200
        assert result['body']['success'] is True
        assert result['body']['article_id'] == 'test-article'
        assert result['body']['cluster_id'] == 'cluster_existing-article'
        assert result['body']['result']['is_duplicate'] is True
    
    def test_lambda_handler_missing_required_field(self):
        """Test Lambda handler with missing required field."""
        event = {
            'article_id': 'test-article',
            # Missing 'url', 'title', 'published_at'
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 500
        assert result['body']['success'] is False
        assert 'missing' in result['body']['error'].lower()
    
    @patch.dict(os.environ, {})
    def test_lambda_handler_missing_env_vars(self):
        """Test Lambda handler with missing environment variables."""
        event = {
            'article_id': 'test-article',
            'url': 'https://example.com/test',
            'title': 'Test Article',
            'published_at': '2024-01-15T10:30:00Z'
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 500
        assert result['body']['success'] is False
        assert 'ARTICLES_TABLE' in result['body']['error']
    
    @patch.dict(os.environ, {
        'ARTICLES_TABLE': 'test-articles'
        # Missing OPENSEARCH_ENDPOINT - should still work with warning
    })
    @patch('lambda_tools.dedup_tool.DedupTool')
    def test_lambda_handler_no_opensearch(self, mock_dedup_tool_class):
        """Test Lambda handler without OpenSearch configuration."""
        # Mock DedupTool
        mock_dedup_tool = Mock()
        mock_dedup_tool_class.return_value = mock_dedup_tool
        
        mock_result = DuplicationResult(
            is_duplicate=False,
            similarity_score=0.0,
            method="heuristic",
            rationale="No duplicates found"
        )
        mock_dedup_tool.find_duplicates.return_value = mock_result
        mock_dedup_tool.assign_cluster.return_value = "cluster_test-article"
        
        event = {
            'article_id': 'test-article',
            'url': 'https://example.com/test',
            'title': 'Test Article',
            'published_at': '2024-01-15T10:30:00Z'
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 200
        assert result['body']['success'] is True
        # Should still work even without OpenSearch


if __name__ == "__main__":
    pytest.main([__file__, "-v"])