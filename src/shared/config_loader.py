"""
Configuration loaders for RSS feeds and keywords.

This module provides classes to load and validate configuration from YAML files
for RSS feeds and target keywords used in the Sentinel cybersecurity triage system.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse

import yaml
from pydantic import ValidationError

from .models import (
    FeedCategory,
    FeedConfig,
    FeedsConfig,
    KeywordConfig,
    KeywordsConfig,
    Priority
)

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


class FeedConfigLoader:
    """
    Loads and validates RSS feed configuration from YAML files.
    
    Handles loading feed configurations, validating URLs and intervals,
    and providing access to categorized feeds.
    """
    
    def __init__(self, config_path: Union[str, Path] = "config/feeds.yaml"):
        """
        Initialize the feed configuration loader.
        
        Args:
            config_path: Path to the feeds configuration YAML file
        """
        self.config_path = Path(config_path)
        self._config: Optional[FeedsConfig] = None
        self._feeds_by_category: Dict[FeedCategory, List[FeedConfig]] = {}
        self._feeds_by_name: Dict[str, FeedConfig] = {}
        
    def load_config(self) -> FeedsConfig:
        """
        Load and validate the feeds configuration from YAML file.
        
        Returns:
            FeedsConfig: Validated configuration object
            
        Raises:
            ConfigurationError: If configuration loading or validation fails
        """
        try:
            if not self.config_path.exists():
                raise ConfigurationError(f"Configuration file not found: {self.config_path}")
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
                
            # Validate and parse configuration
            self._config = self._parse_feeds_config(raw_config)
            self._build_indexes()
            
            logger.info(f"Loaded {len(self._config.feeds)} feed configurations from {self.config_path}")
            return self._config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {self.config_path}: {e}")
        except ValidationError as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def _parse_feeds_config(self, raw_config: Dict) -> FeedsConfig:
        """Parse and validate raw configuration data."""
        if not isinstance(raw_config, dict):
            raise ConfigurationError("Configuration must be a dictionary")
            
        feeds_data = raw_config.get('feeds', [])
        if not isinstance(feeds_data, list):
            raise ConfigurationError("'feeds' must be a list")
            
        # Parse individual feed configurations
        feeds = []
        for i, feed_data in enumerate(feeds_data):
            try:
                # Validate required fields
                if not isinstance(feed_data, dict):
                    raise ValidationError(f"Feed {i} must be a dictionary")
                    
                # Validate URL format
                url = feed_data.get('url')
                if not url:
                    raise ValidationError("Feed URL is required")
                    
                self._validate_url(url)
                
                # Validate fetch interval
                fetch_interval = feed_data.get('fetch_interval', '2h')
                self._validate_fetch_interval(fetch_interval)
                
                # Validate category
                category = feed_data.get('category')
                if category and category not in [cat.value for cat in FeedCategory]:
                    raise ValidationError(f"Invalid category: {category}")
                
                feed_config = FeedConfig(**feed_data)
                feeds.append(feed_config)
                
            except (ValidationError, ValueError) as e:
                raise ConfigurationError(f"Invalid feed configuration at index {i}: {e}")
        
        # Parse categories and settings
        categories = raw_config.get('categories', [])
        settings = raw_config.get('settings', {})
        
        return FeedsConfig(
            feeds=feeds,
            categories=categories,
            settings=settings
        )
    
    def _validate_url(self, url: str) -> None:
        """Validate that URL is properly formatted and uses allowed schemes."""
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValidationError("URL must include scheme and domain")
            if parsed.scheme not in ['http', 'https']:
                raise ValidationError("URL must use http or https scheme")
        except Exception as e:
            raise ValidationError(f"Invalid URL format: {e}")
    
    def _validate_fetch_interval(self, interval: str) -> None:
        """Validate fetch interval format (e.g., '1h', '30m', '2d')."""
        pattern = r'^(\d+)([smhd])$'
        if not re.match(pattern, interval):
            raise ValidationError(
                f"Invalid fetch interval format: {interval}. "
                "Use format like '1h', '30m', '2d' (s=seconds, m=minutes, h=hours, d=days)"
            )
    
    def _build_indexes(self) -> None:
        """Build internal indexes for fast lookups."""
        if not self._config:
            return
            
        self._feeds_by_category.clear()
        self._feeds_by_name.clear()
        
        for feed in self._config.feeds:
            # Index by category
            if feed.category not in self._feeds_by_category:
                self._feeds_by_category[feed.category] = []
            self._feeds_by_category[feed.category].append(feed)
            
            # Index by name
            self._feeds_by_name[feed.name] = feed
    
    def get_feeds_by_category(self, category: FeedCategory) -> List[FeedConfig]:
        """
        Get all feeds for a specific category.
        
        Args:
            category: Feed category to filter by
            
        Returns:
            List of feed configurations for the category
        """
        if not self._config:
            self.load_config()
        return self._feeds_by_category.get(category, [])
    
    def get_enabled_feeds(self) -> List[FeedConfig]:
        """
        Get all enabled feed configurations.
        
        Returns:
            List of enabled feed configurations
        """
        if not self._config:
            self.load_config()
        return [feed for feed in self._config.feeds if feed.enabled]
    
    def get_feed_by_name(self, name: str) -> Optional[FeedConfig]:
        """
        Get feed configuration by name.
        
        Args:
            name: Feed name to look up
            
        Returns:
            Feed configuration if found, None otherwise
        """
        if not self._config:
            self.load_config()
        return self._feeds_by_name.get(name)
    
    def get_all_feeds(self) -> List[FeedConfig]:
        """
        Get all feed configurations.
        
        Returns:
            List of all feed configurations
        """
        if not self._config:
            self.load_config()
        return self._config.feeds
    
    def get_categories(self) -> List[Dict]:
        """
        Get feed category definitions.
        
        Returns:
            List of category definitions with metadata
        """
        if not self._config:
            self.load_config()
        return self._config.categories
    
    def get_settings(self) -> Dict:
        """
        Get global feed settings.
        
        Returns:
            Dictionary of global settings
        """
        if not self._config:
            self.load_config()
        return self._config.settings
    
    def validate_all_feeds(self) -> Dict[str, List[str]]:
        """
        Validate all feed configurations and return any issues.
        
        Returns:
            Dictionary mapping feed names to lists of validation issues
        """
        if not self._config:
            self.load_config()
            
        issues = {}
        
        for feed in self._config.feeds:
            feed_issues = []
            
            # Check for duplicate names
            duplicate_count = sum(1 for f in self._config.feeds if f.name == feed.name)
            if duplicate_count > 1:
                feed_issues.append(f"Duplicate feed name: {feed.name}")
            
            # Validate URL accessibility (basic format check)
            try:
                self._validate_url(str(feed.url))
            except ValidationError as e:
                feed_issues.append(f"URL validation failed: {e}")
            
            # Validate fetch interval
            try:
                self._validate_fetch_interval(feed.fetch_interval)
            except ValidationError as e:
                feed_issues.append(f"Fetch interval validation failed: {e}")
            
            if feed_issues:
                issues[feed.name] = feed_issues
        
        return issues
    
    def reload_config(self) -> FeedsConfig:
        """
        Reload configuration from file.
        
        Returns:
            Reloaded configuration object
        """
        self._config = None
        self._feeds_by_category.clear()
        self._feeds_by_name.clear()
        return self.load_config()


class KeywordManager:
    """
    Manages target keywords for relevance assessment with fuzzy matching capabilities.
    
    Handles loading keyword configurations, categorization, and provides
    fuzzy matching for keyword variations and similar terms.
    """
    
    def __init__(self, config_path: Union[str, Path] = "config/keywords.yaml"):
        """
        Initialize the keyword manager.
        
        Args:
            config_path: Path to the keywords configuration YAML file
        """
        self.config_path = Path(config_path)
        self._config: Optional[KeywordsConfig] = None
        self._keywords_by_category: Dict[str, List[KeywordConfig]] = {}
        self._all_keywords: List[KeywordConfig] = []
        self._keyword_lookup: Dict[str, KeywordConfig] = {}
        self._variation_lookup: Dict[str, KeywordConfig] = {}
        
    def load_config(self) -> KeywordsConfig:
        """
        Load and validate the keywords configuration from YAML file.
        
        Returns:
            KeywordsConfig: Validated configuration object
            
        Raises:
            ConfigurationError: If configuration loading or validation fails
        """
        try:
            if not self.config_path.exists():
                raise ConfigurationError(f"Configuration file not found: {self.config_path}")
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
                
            # Validate and parse configuration
            self._config = self._parse_keywords_config(raw_config)
            self._build_indexes()
            
            total_keywords = len(self._all_keywords)
            total_variations = sum(len(kw.variations) for kw in self._all_keywords)
            
            logger.info(
                f"Loaded {total_keywords} keywords with {total_variations} variations "
                f"from {self.config_path}"
            )
            return self._config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {self.config_path}: {e}")
        except ValidationError as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def _parse_keywords_config(self, raw_config: Dict) -> KeywordsConfig:
        """Parse and validate raw keywords configuration data."""
        if not isinstance(raw_config, dict):
            raise ConfigurationError("Configuration must be a dictionary")
        
        # Expected keyword categories
        expected_categories = [
            'cloud_platforms', 'security_vendors', 'enterprise_tools',
            'enterprise_systems', 'network_infrastructure', 'virtualization',
            'specialized_platforms'
        ]
        
        parsed_categories = {}
        
        for category in expected_categories:
            category_data = raw_config.get(category, [])
            if not isinstance(category_data, list):
                raise ConfigurationError(f"Category '{category}' must be a list")
            
            keywords = []
            for i, keyword_data in enumerate(category_data):
                try:
                    if not isinstance(keyword_data, dict):
                        raise ValidationError(f"Keyword {i} must be a dictionary")
                    
                    # Validate required fields
                    if 'keyword' not in keyword_data:
                        raise ValidationError("Keyword field is required")
                    
                    # Validate weight range
                    weight = keyword_data.get('weight', 1.0)
                    if not 0.0 <= weight <= 1.0:
                        raise ValidationError(f"Weight must be between 0.0 and 1.0, got {weight}")
                    
                    keyword_config = KeywordConfig(**keyword_data)
                    keywords.append(keyword_config)
                    
                except (ValidationError, ValueError) as e:
                    raise ConfigurationError(
                        f"Invalid keyword configuration in category '{category}' at index {i}: {e}"
                    )
            
            parsed_categories[category] = keywords
        
        # Parse settings and categories
        settings = raw_config.get('settings', {})
        categories = raw_config.get('categories', {})
        
        return KeywordsConfig(
            **parsed_categories,
            settings=settings,
            categories=categories
        )
    
    def _build_indexes(self) -> None:
        """Build internal indexes for fast keyword lookups."""
        if not self._config:
            return
        
        self._keywords_by_category.clear()
        self._all_keywords.clear()
        self._keyword_lookup.clear()
        self._variation_lookup.clear()
        
        # Build category-based index
        for category_name in [
            'cloud_platforms', 'security_vendors', 'enterprise_tools',
            'enterprise_systems', 'network_infrastructure', 'virtualization',
            'specialized_platforms'
        ]:
            category_keywords = getattr(self._config, category_name, [])
            self._keywords_by_category[category_name] = category_keywords
            self._all_keywords.extend(category_keywords)
        
        # Build lookup indexes
        for keyword_config in self._all_keywords:
            # Primary keyword lookup
            key = keyword_config.keyword.lower()
            self._keyword_lookup[key] = keyword_config
            
            # Variation lookup
            for variation in keyword_config.variations:
                var_key = variation.lower()
                self._variation_lookup[var_key] = keyword_config
    
    def get_keywords_by_category(self, category: str) -> List[KeywordConfig]:
        """
        Get all keywords for a specific category.
        
        Args:
            category: Category name (e.g., 'cloud_platforms', 'security_vendors')
            
        Returns:
            List of keyword configurations for the category
        """
        if not self._config:
            self.load_config()
        return self._keywords_by_category.get(category, [])
    
    def get_all_keywords(self) -> List[KeywordConfig]:
        """
        Get all keyword configurations.
        
        Returns:
            List of all keyword configurations
        """
        if not self._config:
            self.load_config()
        return self._all_keywords
    
    def get_critical_keywords(self) -> List[KeywordConfig]:
        """
        Get keywords marked as critical priority.
        
        Returns:
            List of critical priority keywords
        """
        if not self._config:
            self.load_config()
        
        critical_keyword_names = self._config.categories.get('critical', [])
        return [
            kw for kw in self._all_keywords
            if kw.keyword in critical_keyword_names
        ]
    
    def get_high_priority_keywords(self) -> List[KeywordConfig]:
        """
        Get keywords marked as high priority.
        
        Returns:
            List of high priority keywords
        """
        if not self._config:
            self.load_config()
        
        high_keyword_names = self._config.categories.get('high', [])
        return [
            kw for kw in self._all_keywords
            if kw.keyword in high_keyword_names
        ]
    
    def find_exact_matches(self, text: str) -> List[Dict[str, Union[str, int, float]]]:
        """
        Find exact keyword matches in text.
        
        Args:
            text: Text to search for keywords
            
        Returns:
            List of match dictionaries with keyword, hit_count, contexts, and confidence
        """
        if not self._config:
            self.load_config()
        
        matches = []
        
        # Check for case sensitivity setting
        case_sensitive = self._config.settings.get('case_sensitive', False)
        search_text = text if case_sensitive else text.lower()
        
        # Word boundary matching setting
        word_boundary = self._config.settings.get('word_boundary_matching', True)
        context_window = self._config.settings.get('context_window', 10)
        
        for keyword_config in self._all_keywords:
            # Check primary keyword and variations
            search_terms = [keyword_config.keyword]
            search_terms.extend(keyword_config.variations)
            
            for term in search_terms:
                search_term = term if case_sensitive else term.lower()
                
                if word_boundary:
                    # Use word boundary matching
                    pattern = r'\b' + re.escape(search_term) + r'\b'
                    matches_found = re.finditer(pattern, search_text, re.IGNORECASE if not case_sensitive else 0)
                    hit_positions = [m.start() for m in matches_found]
                else:
                    # Simple substring matching
                    hit_positions = []
                    start = 0
                    while True:
                        pos = search_text.find(search_term, start)
                        if pos == -1:
                            break
                        hit_positions.append(pos)
                        start = pos + 1
                
                if hit_positions:
                    # Extract contexts around matches
                    contexts = []
                    words = text.split()
                    
                    for pos in hit_positions:
                        # Find word index for context extraction
                        word_pos = len(text[:pos].split()) - 1
                        start_idx = max(0, word_pos - context_window)
                        end_idx = min(len(words), word_pos + context_window + 1)
                        context = ' '.join(words[start_idx:end_idx])
                        contexts.append(context)
                    
                    matches.append({
                        'keyword': keyword_config.keyword,
                        'matched_term': term,
                        'hit_count': len(hit_positions),
                        'contexts': contexts,
                        'confidence': 1.0,  # Exact match
                        'weight': keyword_config.weight,
                        'category': self._get_keyword_category(keyword_config)
                    })
                    break  # Found match for this keyword, don't check variations
        
        return matches
    
    def find_fuzzy_matches(self, text: str, max_distance: int = None) -> List[Dict[str, Union[str, int, float]]]:
        """
        Find fuzzy keyword matches in text using edit distance.
        
        Args:
            text: Text to search for keywords
            max_distance: Maximum edit distance for fuzzy matching
            
        Returns:
            List of match dictionaries with keyword, hit_count, contexts, and confidence
        """
        if not self._config:
            self.load_config()
        
        # Check if fuzzy matching is enabled
        if not self._config.settings.get('enable_fuzzy_matching', True):
            return []
        
        if max_distance is None:
            max_distance = self._config.settings.get('max_edit_distance', 2)
        
        min_confidence = self._config.settings.get('min_confidence', 0.7)
        
        matches = []
        words = text.lower().split()
        
        for keyword_config in self._all_keywords:
            search_terms = [keyword_config.keyword.lower()]
            search_terms.extend([v.lower() for v in keyword_config.variations])
            
            for term in search_terms:
                term_words = term.split()
                
                # For multi-word terms, look for phrase matches
                if len(term_words) > 1:
                    matches.extend(self._find_phrase_fuzzy_matches(
                        words, term_words, keyword_config, max_distance, min_confidence
                    ))
                else:
                    # Single word fuzzy matching
                    for i, word in enumerate(words):
                        distance = self._levenshtein_distance(word, term)
                        if distance <= max_distance and len(term) > 2:  # Avoid very short matches
                            confidence = 1.0 - (distance / max(len(word), len(term)))
                            
                            if confidence >= min_confidence:
                                context_start = max(0, i - 5)
                                context_end = min(len(words), i + 6)
                                context = ' '.join(words[context_start:context_end])
                                
                                matches.append({
                                    'keyword': keyword_config.keyword,
                                    'matched_term': word,
                                    'hit_count': 1,
                                    'contexts': [context],
                                    'confidence': confidence,
                                    'weight': keyword_config.weight,
                                    'category': self._get_keyword_category(keyword_config),
                                    'edit_distance': distance
                                })
        
        # Remove duplicates and sort by confidence
        unique_matches = {}
        for match in matches:
            key = (match['keyword'], match['matched_term'])
            if key not in unique_matches or match['confidence'] > unique_matches[key]['confidence']:
                unique_matches[key] = match
        
        return sorted(unique_matches.values(), key=lambda x: x['confidence'], reverse=True)
    
    def _find_phrase_fuzzy_matches(self, words: List[str], term_words: List[str], 
                                   keyword_config: KeywordConfig, max_distance: int, 
                                   min_confidence: float) -> List[Dict]:
        """Find fuzzy matches for multi-word phrases."""
        matches = []
        
        for i in range(len(words) - len(term_words) + 1):
            phrase = words[i:i + len(term_words)]
            phrase_text = ' '.join(phrase)
            term_text = ' '.join(term_words)
            
            distance = self._levenshtein_distance(phrase_text, term_text)
            max_phrase_distance = max_distance * len(term_words)  # Scale for phrase length
            
            if distance <= max_phrase_distance:
                confidence = 1.0 - (distance / max(len(phrase_text), len(term_text)))
                
                if confidence >= min_confidence:
                    context_start = max(0, i - 5)
                    context_end = min(len(words), i + len(term_words) + 5)
                    context = ' '.join(words[context_start:context_end])
                    
                    matches.append({
                        'keyword': keyword_config.keyword,
                        'matched_term': phrase_text,
                        'hit_count': 1,
                        'contexts': [context],
                        'confidence': confidence,
                        'weight': keyword_config.weight,
                        'category': self._get_keyword_category(keyword_config),
                        'edit_distance': distance
                    })
        
        return matches
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein edit distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _get_keyword_category(self, keyword_config: KeywordConfig) -> str:
        """Get the category name for a keyword configuration."""
        for category_name, keywords in self._keywords_by_category.items():
            if keyword_config in keywords:
                return category_name
        return 'unknown'
    
    def match_keywords(self, text: str, include_fuzzy: bool = True) -> List[Dict[str, Union[str, int, float]]]:
        """
        Find all keyword matches (exact and fuzzy) in text.
        
        Args:
            text: Text to search for keywords
            include_fuzzy: Whether to include fuzzy matches
            
        Returns:
            List of all matches sorted by confidence and weight
        """
        matches = []
        
        # Get exact matches
        exact_matches = self.find_exact_matches(text)
        matches.extend(exact_matches)
        
        # Get fuzzy matches if enabled
        if include_fuzzy:
            fuzzy_matches = self.find_fuzzy_matches(text)
            matches.extend(fuzzy_matches)
        
        # Remove duplicates (prefer exact matches)
        unique_matches = {}
        for match in matches:
            key = match['keyword']
            if key not in unique_matches or match['confidence'] > unique_matches[key]['confidence']:
                unique_matches[key] = match
        
        # Sort by weighted confidence score
        final_matches = list(unique_matches.values())
        final_matches.sort(
            key=lambda x: x['confidence'] * x['weight'],
            reverse=True
        )
        
        return final_matches
    
    def get_keyword_statistics(self) -> Dict[str, Union[int, Dict[str, int]]]:
        """
        Get statistics about loaded keywords.
        
        Returns:
            Dictionary with keyword statistics
        """
        if not self._config:
            self.load_config()
        
        stats = {
            'total_keywords': len(self._all_keywords),
            'total_variations': sum(len(kw.variations) for kw in self._all_keywords),
            'categories': {}
        }
        
        for category_name, keywords in self._keywords_by_category.items():
            stats['categories'][category_name] = {
                'count': len(keywords),
                'variations': sum(len(kw.variations) for kw in keywords)
            }
        
        return stats
    
    def validate_keywords(self) -> Dict[str, List[str]]:
        """
        Validate all keyword configurations and return any issues.
        
        Returns:
            Dictionary mapping categories to lists of validation issues
        """
        if not self._config:
            self.load_config()
        
        issues = {}
        
        for category_name, keywords in self._keywords_by_category.items():
            category_issues = []
            keyword_names = set()
            
            for keyword_config in keywords:
                # Check for duplicate keywords within category
                if keyword_config.keyword in keyword_names:
                    category_issues.append(f"Duplicate keyword: {keyword_config.keyword}")
                keyword_names.add(keyword_config.keyword)
                
                # Check weight range
                if not 0.0 <= keyword_config.weight <= 1.0:
                    category_issues.append(
                        f"Invalid weight for '{keyword_config.keyword}': {keyword_config.weight}"
                    )
            
            if category_issues:
                issues[category_name] = category_issues
        
        return issues
    
    def reload_config(self) -> KeywordsConfig:
        """
        Reload configuration from file.
        
        Returns:
            Reloaded configuration object
        """
        self._config = None
        self._keywords_by_category.clear()
        self._all_keywords.clear()
        self._keyword_lookup.clear()
        self._variation_lookup.clear()
        return self.load_config()
    
    def get_settings(self) -> Dict:
        """
        Get keyword matching settings.
        
        Returns:
            Dictionary of keyword matching settings
        """
        if not self._config:
            self.load_config()
        return self._config.settings