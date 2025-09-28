"""
Unit tests for configuration loaders.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.shared.config_loader import ConfigurationError, FeedConfigLoader
from src.shared.models import FeedCategory


class TestFeedConfigLoader:
    """Test cases for FeedConfigLoader."""
    
    @pytest.fixture
    def sample_config(self):
        """Sample valid configuration for testing."""
        return {
            'feeds': [
                {
                    'name': 'Test Feed 1',
                    'url': 'https://example.com/feed1.xml',
                    'category': 'News',
                    'enabled': True,
                    'fetch_interval': '1h',
                    'description': 'Test feed 1'
                },
                {
                    'name': 'Test Feed 2',
                    'url': 'https://example.com/feed2.xml',
                    'category': 'Advisories',
                    'enabled': False,
                    'fetch_interval': '30m',
                    'description': 'Test feed 2'
                }
            ],
            'categories': [
                {
                    'name': 'News',
                    'description': 'General news',
                    'priority': 'low'
                }
            ],
            'settings': {
                'default_fetch_interval': '2h',
                'max_articles_per_fetch': 50
            }
        }
    
    @pytest.fixture
    def temp_config_file(self, sample_config):
        """Create a temporary configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            return Path(f.name)
    
    def test_load_valid_config(self, temp_config_file):
        """Test loading a valid configuration file."""
        loader = FeedConfigLoader(temp_config_file)
        config = loader.load_config()
        
        assert len(config.feeds) == 2
        assert config.feeds[0].name == 'Test Feed 1'
        assert config.feeds[0].category == FeedCategory.NEWS
        assert config.feeds[0].enabled is True
        assert config.feeds[1].enabled is False
        
        # Clean up
        temp_config_file.unlink()
    
    def test_load_nonexistent_file(self):
        """Test loading a non-existent configuration file."""
        loader = FeedConfigLoader('nonexistent.yaml')
        
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            loader.load_config()
    
    def test_invalid_yaml(self):
        """Test loading invalid YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = Path(f.name)
        
        loader = FeedConfigLoader(temp_path)
        
        with pytest.raises(ConfigurationError, match="Invalid YAML"):
            loader.load_config()
        
        temp_path.unlink()
    
    def test_invalid_url_format(self):
        """Test validation of invalid URL formats."""
        invalid_config = {
            'feeds': [
                {
                    'name': 'Invalid Feed',
                    'url': 'not-a-url',
                    'category': 'News',
                    'enabled': True
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            temp_path = Path(f.name)
        
        loader = FeedConfigLoader(temp_path)
        
        with pytest.raises(ConfigurationError, match="Invalid feed configuration"):
            loader.load_config()
        
        temp_path.unlink()
    
    def test_invalid_fetch_interval(self):
        """Test validation of invalid fetch intervals."""
        invalid_config = {
            'feeds': [
                {
                    'name': 'Invalid Interval Feed',
                    'url': 'https://example.com/feed.xml',
                    'category': 'News',
                    'enabled': True,
                    'fetch_interval': 'invalid'
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            temp_path = Path(f.name)
        
        loader = FeedConfigLoader(temp_path)
        
        with pytest.raises(ConfigurationError, match="Invalid feed configuration"):
            loader.load_config()
        
        temp_path.unlink()
    
    def test_invalid_category(self):
        """Test validation of invalid categories."""
        invalid_config = {
            'feeds': [
                {
                    'name': 'Invalid Category Feed',
                    'url': 'https://example.com/feed.xml',
                    'category': 'InvalidCategory',
                    'enabled': True
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            temp_path = Path(f.name)
        
        loader = FeedConfigLoader(temp_path)
        
        with pytest.raises(ConfigurationError, match="Invalid feed configuration"):
            loader.load_config()
        
        temp_path.unlink()
    
    def test_get_feeds_by_category(self, temp_config_file):
        """Test getting feeds by category."""
        loader = FeedConfigLoader(temp_config_file)
        loader.load_config()
        
        news_feeds = loader.get_feeds_by_category(FeedCategory.NEWS)
        advisory_feeds = loader.get_feeds_by_category(FeedCategory.ADVISORIES)
        
        assert len(news_feeds) == 1
        assert news_feeds[0].name == 'Test Feed 1'
        assert len(advisory_feeds) == 1
        assert advisory_feeds[0].name == 'Test Feed 2'
        
        temp_config_file.unlink()
    
    def test_get_enabled_feeds(self, temp_config_file):
        """Test getting only enabled feeds."""
        loader = FeedConfigLoader(temp_config_file)
        loader.load_config()
        
        enabled_feeds = loader.get_enabled_feeds()
        
        assert len(enabled_feeds) == 1
        assert enabled_feeds[0].name == 'Test Feed 1'
        assert enabled_feeds[0].enabled is True
        
        temp_config_file.unlink()
    
    def test_get_feed_by_name(self, temp_config_file):
        """Test getting feed by name."""
        loader = FeedConfigLoader(temp_config_file)
        loader.load_config()
        
        feed = loader.get_feed_by_name('Test Feed 1')
        assert feed is not None
        assert feed.name == 'Test Feed 1'
        
        nonexistent = loader.get_feed_by_name('Nonexistent Feed')
        assert nonexistent is None
        
        temp_config_file.unlink()
    
    def test_validate_all_feeds(self, temp_config_file):
        """Test validation of all feeds."""
        loader = FeedConfigLoader(temp_config_file)
        loader.load_config()
        
        issues = loader.validate_all_feeds()
        
        # Should have no issues with valid config
        assert len(issues) == 0
        
        temp_config_file.unlink()
    
    def test_validate_duplicate_names(self):
        """Test detection of duplicate feed names."""
        duplicate_config = {
            'feeds': [
                {
                    'name': 'Duplicate Feed',
                    'url': 'https://example.com/feed1.xml',
                    'category': 'News',
                    'enabled': True
                },
                {
                    'name': 'Duplicate Feed',
                    'url': 'https://example.com/feed2.xml',
                    'category': 'News',
                    'enabled': True
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(duplicate_config, f)
            temp_path = Path(f.name)
        
        loader = FeedConfigLoader(temp_path)
        loader.load_config()
        
        issues = loader.validate_all_feeds()
        
        assert 'Duplicate Feed' in issues
        assert any('Duplicate feed name' in issue for issue in issues['Duplicate Feed'])
        
        temp_path.unlink()
    
    def test_reload_config(self, temp_config_file):
        """Test reloading configuration."""
        loader = FeedConfigLoader(temp_config_file)
        
        # Load initial config
        config1 = loader.load_config()
        assert len(config1.feeds) == 2
        
        # Modify the file
        modified_config = {
            'feeds': [
                {
                    'name': 'Modified Feed',
                    'url': 'https://example.com/modified.xml',
                    'category': 'News',
                    'enabled': True
                }
            ],
            'categories': [],
            'settings': {}
        }
        
        with open(temp_config_file, 'w') as f:
            yaml.dump(modified_config, f)
        
        # Reload config
        config2 = loader.reload_config()
        assert len(config2.feeds) == 1
        assert config2.feeds[0].name == 'Modified Feed'
        
        temp_config_file.unlink()
    
    def test_url_validation_edge_cases(self):
        """Test URL validation with various edge cases."""
        loader = FeedConfigLoader()
        
        # Valid URLs
        valid_urls = [
            'https://example.com/feed.xml',
            'http://example.com/feed.rss',
            'https://subdomain.example.com/path/to/feed.xml'
        ]
        
        for url in valid_urls:
            loader._validate_url(url)  # Should not raise
        
        # Invalid URLs
        invalid_urls = [
            'not-a-url',
            'ftp://example.com/feed.xml',  # Wrong scheme
            'https://',  # No domain
            'example.com/feed.xml'  # No scheme
        ]
        
        for url in invalid_urls:
            with pytest.raises(Exception):
                loader._validate_url(url)
    
    def test_fetch_interval_validation_edge_cases(self):
        """Test fetch interval validation with various formats."""
        loader = FeedConfigLoader()
        
        # Valid intervals
        valid_intervals = ['1s', '30m', '2h', '1d', '10s', '120m']
        
        for interval in valid_intervals:
            loader._validate_fetch_interval(interval)  # Should not raise
        
        # Invalid intervals
        invalid_intervals = [
            'invalid',
            '1',
            '1x',
            '1.5h',
            '-1h',
            '0h'
        ]
        
        for interval in invalid_intervals:
            with pytest.raises(Exception):
                loader._validate_fetch_interval(interval)


class TestKeywordManager:
    """Test cases for KeywordManager."""
    
    @pytest.fixture
    def sample_keywords_config(self):
        """Sample valid keywords configuration for testing."""
        return {
            'cloud_platforms': [
                {
                    'keyword': 'Azure',
                    'variations': ['Microsoft Azure', 'Azure AD'],
                    'weight': 1.0,
                    'description': 'Microsoft Azure cloud platform'
                },
                {
                    'keyword': 'AWS',
                    'variations': ['Amazon Web Services', 'Amazon AWS'],
                    'weight': 1.0,
                    'description': 'Amazon Web Services'
                }
            ],
            'security_vendors': [
                {
                    'keyword': 'Mimecast',
                    'variations': ['Mimecast Email Security'],
                    'weight': 0.9,
                    'description': 'Email security platform'
                }
            ],
            'enterprise_tools': [],
            'enterprise_systems': [],
            'network_infrastructure': [],
            'virtualization': [],
            'specialized_platforms': [],
            'settings': {
                'min_confidence': 0.7,
                'enable_fuzzy_matching': True,
                'max_edit_distance': 2,
                'case_sensitive': False,
                'word_boundary_matching': True,
                'context_window': 10
            },
            'categories': {
                'critical': ['Azure', 'AWS'],
                'high': ['Mimecast'],
                'medium': [],
                'low': []
            }
        }
    
    @pytest.fixture
    def temp_keywords_file(self, sample_keywords_config):
        """Create a temporary keywords configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_keywords_config, f)
            return Path(f.name)
    
    def test_load_keywords_config(self, temp_keywords_file):
        """Test loading a valid keywords configuration file."""
        from src.shared.config_loader import KeywordManager
        
        manager = KeywordManager(temp_keywords_file)
        config = manager.load_config()
        
        assert len(config.cloud_platforms) == 2
        assert config.cloud_platforms[0].keyword == 'Azure'
        assert len(config.cloud_platforms[0].variations) == 2
        assert config.cloud_platforms[0].weight == 1.0
        
        assert len(config.security_vendors) == 1
        assert config.security_vendors[0].keyword == 'Mimecast'
        
        # Clean up
        temp_keywords_file.unlink()
    
    def test_get_keywords_by_category(self, temp_keywords_file):
        """Test getting keywords by category."""
        from src.shared.config_loader import KeywordManager
        
        manager = KeywordManager(temp_keywords_file)
        manager.load_config()
        
        cloud_keywords = manager.get_keywords_by_category('cloud_platforms')
        assert len(cloud_keywords) == 2
        assert cloud_keywords[0].keyword == 'Azure'
        assert cloud_keywords[1].keyword == 'AWS'
        
        security_keywords = manager.get_keywords_by_category('security_vendors')
        assert len(security_keywords) == 1
        assert security_keywords[0].keyword == 'Mimecast'
        
        empty_category = manager.get_keywords_by_category('enterprise_tools')
        assert len(empty_category) == 0
        
        temp_keywords_file.unlink()
    
    def test_get_critical_keywords(self, temp_keywords_file):
        """Test getting critical priority keywords."""
        from src.shared.config_loader import KeywordManager
        
        manager = KeywordManager(temp_keywords_file)
        manager.load_config()
        
        critical_keywords = manager.get_critical_keywords()
        assert len(critical_keywords) == 2
        
        critical_names = [kw.keyword for kw in critical_keywords]
        assert 'Azure' in critical_names
        assert 'AWS' in critical_names
        
        temp_keywords_file.unlink()
    
    def test_find_exact_matches(self, temp_keywords_file):
        """Test finding exact keyword matches in text."""
        from src.shared.config_loader import KeywordManager
        
        manager = KeywordManager(temp_keywords_file)
        manager.load_config()
        
        text = "We are using Microsoft Azure and AWS for our cloud infrastructure. Mimecast handles our email security."
        
        matches = manager.find_exact_matches(text)
        
        # Should find matches for Azure (via variation), AWS, and Mimecast
        assert len(matches) >= 3
        
        matched_keywords = [match['keyword'] for match in matches]
        assert 'Azure' in matched_keywords
        assert 'AWS' in matched_keywords
        assert 'Mimecast' in matched_keywords
        
        # Check match details
        azure_match = next(m for m in matches if m['keyword'] == 'Azure')
        assert azure_match['confidence'] == 1.0
        assert azure_match['hit_count'] == 1
        assert len(azure_match['contexts']) == 1
        
        temp_keywords_file.unlink()
    
    def test_find_fuzzy_matches(self, temp_keywords_file):
        """Test finding fuzzy keyword matches in text."""
        from src.shared.config_loader import KeywordManager
        
        manager = KeywordManager(temp_keywords_file)
        manager.load_config()
        
        # Text with slight misspellings
        text = "We use Azur and Mimcast for our infrastructure."
        
        fuzzy_matches = manager.find_fuzzy_matches(text)
        
        # Should find fuzzy matches
        assert len(fuzzy_matches) >= 2
        
        # Check that confidence is less than 1.0 for fuzzy matches
        for match in fuzzy_matches:
            assert match['confidence'] < 1.0
            assert match['confidence'] >= 0.7  # Above minimum threshold
            assert 'edit_distance' in match
        
        temp_keywords_file.unlink()
    
    def test_match_keywords_combined(self, temp_keywords_file):
        """Test combined exact and fuzzy keyword matching."""
        from src.shared.config_loader import KeywordManager
        
        manager = KeywordManager(temp_keywords_file)
        manager.load_config()
        
        # Text with both exact and fuzzy matches
        text = "Our Azure deployment and Mimcast solution work well together."
        
        matches = manager.match_keywords(text, include_fuzzy=True)
        
        # Should find both exact (Azure) and fuzzy (Mimcast -> Mimecast) matches
        assert len(matches) >= 2
        
        # Matches should be sorted by weighted confidence
        for i in range(len(matches) - 1):
            current_score = matches[i]['confidence'] * matches[i]['weight']
            next_score = matches[i + 1]['confidence'] * matches[i + 1]['weight']
            assert current_score >= next_score
        
        temp_keywords_file.unlink()
    
    def test_get_keyword_statistics(self, temp_keywords_file):
        """Test getting keyword statistics."""
        from src.shared.config_loader import KeywordManager
        
        manager = KeywordManager(temp_keywords_file)
        manager.load_config()
        
        stats = manager.get_keyword_statistics()
        
        assert stats['total_keywords'] == 3  # Azure, AWS, Mimecast
        assert stats['total_variations'] == 4  # 2 + 2 + 1 - 1 (one variation for Mimecast)
        
        assert 'cloud_platforms' in stats['categories']
        assert stats['categories']['cloud_platforms']['count'] == 2
        assert stats['categories']['cloud_platforms']['variations'] == 4
        
        assert 'security_vendors' in stats['categories']
        assert stats['categories']['security_vendors']['count'] == 1
        
        temp_keywords_file.unlink()
    
    def test_validate_keywords(self, temp_keywords_file):
        """Test keyword validation."""
        from src.shared.config_loader import KeywordManager
        
        manager = KeywordManager(temp_keywords_file)
        manager.load_config()
        
        issues = manager.validate_keywords()
        
        # Should have no issues with valid config
        assert len(issues) == 0
        
        temp_keywords_file.unlink()
    
    def test_validate_keywords_with_issues(self):
        """Test keyword validation with problematic configuration."""
        from src.shared.config_loader import KeywordManager
        
        invalid_config = {
            'cloud_platforms': [
                {
                    'keyword': 'Azure',
                    'variations': ['Microsoft Azure'],
                    'weight': 1.5,  # Invalid weight > 1.0
                    'description': 'Microsoft Azure'
                },
                {
                    'keyword': 'Azure',  # Duplicate keyword
                    'variations': ['Azure AD'],
                    'weight': 1.0,
                    'description': 'Duplicate Azure'
                }
            ],
            'security_vendors': [],
            'enterprise_tools': [],
            'enterprise_systems': [],
            'network_infrastructure': [],
            'virtualization': [],
            'specialized_platforms': [],
            'settings': {},
            'categories': {}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            temp_path = Path(f.name)
        
        manager = KeywordManager(temp_path)
        manager.load_config()
        
        issues = manager.validate_keywords()
        
        assert 'cloud_platforms' in issues
        category_issues = issues['cloud_platforms']
        
        # Should detect duplicate keyword and invalid weight
        assert any('Duplicate keyword' in issue for issue in category_issues)
        assert any('Invalid weight' in issue for issue in category_issues)
        
        temp_path.unlink()
    
    def test_levenshtein_distance(self, temp_keywords_file):
        """Test Levenshtein distance calculation."""
        from src.shared.config_loader import KeywordManager
        
        manager = KeywordManager(temp_keywords_file)
        
        # Test basic edit distance calculations
        assert manager._levenshtein_distance("azure", "azure") == 0
        assert manager._levenshtein_distance("azure", "azur") == 1
        assert manager._levenshtein_distance("azure", "azyre") == 1
        assert manager._levenshtein_distance("azure", "aws") == 5
        assert manager._levenshtein_distance("", "azure") == 5
        assert manager._levenshtein_distance("azure", "") == 5
        
        temp_keywords_file.unlink()
    
    def test_keyword_manager_nonexistent_file(self):
        """Test KeywordManager with non-existent configuration file."""
        from src.shared.config_loader import KeywordManager, ConfigurationError
        
        manager = KeywordManager('nonexistent_keywords.yaml')
        
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            manager.load_config()
    
    def test_reload_keywords_config(self, temp_keywords_file):
        """Test reloading keywords configuration."""
        from src.shared.config_loader import KeywordManager
        
        manager = KeywordManager(temp_keywords_file)
        
        # Load initial config
        config1 = manager.load_config()
        assert len(config1.cloud_platforms) == 2
        
        # Modify the file
        modified_config = {
            'cloud_platforms': [
                {
                    'keyword': 'Google Cloud',
                    'variations': ['GCP', 'Google Cloud Platform'],
                    'weight': 1.0,
                    'description': 'Google Cloud Platform'
                }
            ],
            'security_vendors': [],
            'enterprise_tools': [],
            'enterprise_systems': [],
            'network_infrastructure': [],
            'virtualization': [],
            'specialized_platforms': [],
            'settings': {},
            'categories': {}
        }
        
        with open(temp_keywords_file, 'w') as f:
            yaml.dump(modified_config, f)
        
        # Reload config
        config2 = manager.reload_config()
        assert len(config2.cloud_platforms) == 1
        assert config2.cloud_platforms[0].keyword == 'Google Cloud'
        
        temp_keywords_file.unlink()