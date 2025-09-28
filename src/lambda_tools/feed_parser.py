"""
FeedParser Lambda tool for parsing RSS/Atom feeds.

This Lambda function handles RSS/Atom feed parsing, HTML content normalization,
metadata extraction, and S3 storage with content hashing.
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import boto3
import feedparser
import requests
from bs4 import BeautifulSoup
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# AWS clients
s3_client = boto3.client('s3')


class FeedParserError(Exception):
    """Custom exception for feed parsing errors."""
    pass


class ContentNormalizer:
    """Handles HTML content normalization and metadata extraction."""
    
    def __init__(self):
        self.html_tag_pattern = re.compile(r'<[^>]+>')
        self.whitespace_pattern = re.compile(r'\s+')
        self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    
    def normalize_html(self, html_content: str) -> Dict[str, Any]:
        """
        Normalize HTML content to clean text and extract metadata.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Dictionary with normalized content and metadata
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract metadata
            metadata = self._extract_metadata(soup)
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Extract URLs from content
            urls = self.url_pattern.findall(clean_text)
            
            return {
                'normalized_text': clean_text,
                'metadata': metadata,
                'extracted_urls': list(set(urls)),
                'word_count': len(clean_text.split()),
                'character_count': len(clean_text)
            }
            
        except Exception as e:
            logger.error(f"Error normalizing HTML content: {e}")
            raise FeedParserError(f"HTML normalization failed: {e}")
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract metadata from HTML soup."""
        metadata = {}
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata['html_title'] = title_tag.get_text().strip()
        
        # Meta tags
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            name = tag.get('name') or tag.get('property')
            content = tag.get('content')
            if name and content:
                metadata[f'meta_{name}'] = content
        
        # Links
        links = []
        for link in soup.find_all('a', href=True):
            links.append({
                'url': link['href'],
                'text': link.get_text().strip()
            })
        metadata['links'] = links[:10]  # Limit to first 10 links
        
        # Images
        images = []
        for img in soup.find_all('img', src=True):
            images.append({
                'src': img['src'],
                'alt': img.get('alt', ''),
                'title': img.get('title', '')
            })
        metadata['images'] = images[:5]  # Limit to first 5 images
        
        return metadata


class FeedParser:
    """Main feed parser class."""
    
    def __init__(self, content_bucket: str):
        self.content_bucket = content_bucket
        self.normalizer = ContentNormalizer()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Sentinel-Cybersecurity-Triage/1.0 (RSS Feed Parser)'
        })
    
    def parse_feed(self, feed_url: str, feed_id: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Parse RSS/Atom feed and return normalized articles.
        
        Args:
            feed_url: URL of the RSS/Atom feed
            feed_id: Unique identifier for the feed
            since: Optional datetime to filter articles newer than this date
            
        Returns:
            List of parsed article dictionaries
        """
        try:
            logger.info(f"Parsing feed: {feed_url}")
            
            # Fetch feed content
            response = self.session.get(feed_url, timeout=30)
            response.raise_for_status()
            
            # Parse feed
            feed = feedparser.parse(response.content)
            
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Feed parsing warning for {feed_url}: {feed.bozo_exception}")
            
            # Extract feed metadata
            feed_metadata = self._extract_feed_metadata(feed)
            
            # Process entries
            articles = []
            for entry in feed.entries:
                try:
                    article = self._process_entry(entry, feed_id, feed_metadata, since)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.error(f"Error processing entry {getattr(entry, 'id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(articles)} articles from {feed_url}")
            return articles
            
        except requests.RequestException as e:
            logger.error(f"Network error fetching feed {feed_url}: {e}")
            raise FeedParserError(f"Failed to fetch feed: {e}")
        except Exception as e:
            logger.error(f"Error parsing feed {feed_url}: {e}")
            raise FeedParserError(f"Feed parsing failed: {e}")
    
    def _extract_feed_metadata(self, feed: feedparser.FeedParserDict) -> Dict[str, Any]:
        """Extract metadata from feed."""
        metadata = {}
        
        if hasattr(feed, 'feed'):
            feed_info = feed.feed
            metadata.update({
                'title': getattr(feed_info, 'title', ''),
                'description': getattr(feed_info, 'description', ''),
                'link': getattr(feed_info, 'link', ''),
                'language': getattr(feed_info, 'language', ''),
                'updated': getattr(feed_info, 'updated', ''),
                'generator': getattr(feed_info, 'generator', ''),
                'rights': getattr(feed_info, 'rights', ''),
                'tags': [tag.term for tag in getattr(feed_info, 'tags', [])]
            })
        
        return metadata
    
    def _process_entry(self, entry: Any, feed_id: str, feed_metadata: Dict[str, Any], 
                      since: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """Process a single feed entry."""
        try:
            # Extract basic information
            title = getattr(entry, 'title', '').strip()
            link = getattr(entry, 'link', '').strip()
            
            if not title or not link:
                logger.warning("Skipping entry with missing title or link")
                return None
            
            # Parse publication date
            published_at = self._parse_date(entry)
            if since and published_at and published_at < since:
                return None  # Skip old articles
            
            # Get content
            content = self._extract_content(entry)
            if not content:
                logger.warning(f"No content found for entry: {title}")
                return None
            
            # Generate content hash
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Normalize content
            normalized = self.normalizer.normalize_html(content)
            
            # Store raw and normalized content in S3
            raw_s3_uri = self._store_content_s3(content, f"raw/{feed_id}/{content_hash}.html")
            normalized_s3_uri = self._store_content_s3(
                json.dumps(normalized, indent=2), 
                f"normalized/{feed_id}/{content_hash}.json"
            )
            
            # Extract additional metadata
            author = getattr(entry, 'author', '') or getattr(entry, 'author_detail', {}).get('name', '')
            tags = [tag.term for tag in getattr(entry, 'tags', [])]
            
            # Build canonical URL
            canonical_url = self._get_canonical_url(link, feed_metadata.get('link', ''))
            
            article = {
                'title': title,
                'url': link,
                'canonical_url': canonical_url,
                'published_at': published_at.isoformat() if published_at else None,
                'author': author,
                'content_hash': content_hash,
                'raw_s3_uri': raw_s3_uri,
                'normalized_s3_uri': normalized_s3_uri,
                'normalized_content': normalized['normalized_text'],
                'word_count': normalized['word_count'],
                'character_count': normalized['character_count'],
                'extracted_urls': normalized['extracted_urls'],
                'tags': tags,
                'feed_metadata': feed_metadata,
                'entry_id': getattr(entry, 'id', link),
                'summary': getattr(entry, 'summary', '').strip()
            }
            
            return article
            
        except Exception as e:
            logger.error(f"Error processing entry: {e}")
            raise
    
    def _parse_date(self, entry: Any) -> Optional[datetime]:
        """Parse publication date from entry."""
        # Try different date fields
        date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
        
        for field in date_fields:
            date_tuple = getattr(entry, field, None)
            if date_tuple:
                try:
                    return datetime(*date_tuple[:6], tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    continue
        
        # Try string date fields
        string_fields = ['published', 'updated', 'created']
        for field in string_fields:
            date_str = getattr(entry, field, None)
            if date_str:
                try:
                    # feedparser usually handles this, but just in case
                    parsed = feedparser._parse_date(date_str)
                    if parsed:
                        return datetime(*parsed[:6], tzinfo=timezone.utc)
                except:
                    continue
        
        return None
    
    def _extract_content(self, entry: Any) -> Optional[str]:
        """Extract content from entry."""
        # Try different content fields in order of preference
        content_fields = [
            ('content', lambda x: x[0].value if x else None),
            ('description', lambda x: x),
            ('summary', lambda x: x),
            ('title', lambda x: x)
        ]
        
        for field, extractor in content_fields:
            content = getattr(entry, field, None)
            if content:
                try:
                    extracted = extractor(content)
                    if extracted and extracted.strip():
                        return extracted.strip()
                except:
                    continue
        
        return None
    
    def _get_canonical_url(self, url: str, base_url: str) -> str:
        """Get canonical URL by resolving relative URLs."""
        try:
            if not url:
                return url
            
            parsed = urlparse(url)
            if parsed.netloc:  # Already absolute
                return url
            
            # Resolve relative URL
            if base_url:
                return urljoin(base_url, url)
            
            return url
        except:
            return url
    
    def _store_content_s3(self, content: str, key: str) -> str:
        """Store content in S3 and return URI."""
        try:
            s3_client.put_object(
                Bucket=self.content_bucket,
                Key=key,
                Body=content.encode('utf-8'),
                ContentType='text/html' if key.endswith('.html') else 'application/json',
                ServerSideEncryption='AES256'
            )
            
            return f"s3://{self.content_bucket}/{key}"
            
        except ClientError as e:
            logger.error(f"Error storing content to S3: {e}")
            raise FeedParserError(f"S3 storage failed: {e}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for feed parsing.
    
    Expected event format:
    {
        "feed_id": "string",
        "feed_url": "string", 
        "since": "ISO8601 datetime string (optional)"
    }
    """
    try:
        # Extract parameters
        feed_id = event.get('feed_id')
        feed_url = event.get('feed_url')
        since_str = event.get('since')
        
        if not feed_id or not feed_url:
            raise ValueError("feed_id and feed_url are required")
        
        # Parse since parameter
        since = None
        if since_str:
            try:
                since = datetime.fromisoformat(since_str.replace('Z', '+00:00'))
            except ValueError as e:
                logger.warning(f"Invalid since parameter: {since_str}, ignoring: {e}")
        
        # Get S3 bucket from environment
        import os
        content_bucket = os.environ.get('CONTENT_BUCKET')
        if not content_bucket:
            raise ValueError("CONTENT_BUCKET environment variable is required")
        
        # Initialize parser and parse feed
        parser = FeedParser(content_bucket)
        articles = parser.parse_feed(feed_url, feed_id, since)
        
        return {
            'statusCode': 200,
            'body': {
                'success': True,
                'feed_id': feed_id,
                'feed_url': feed_url,
                'articles_count': len(articles),
                'articles': articles
            }
        }
        
    except Exception as e:
        logger.error(f"Feed parsing failed: {e}")
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
        "feed_id": "test-feed",
        "feed_url": "https://feeds.feedburner.com/oreilly/radar",
        "since": "2024-01-01T00:00:00Z"
    }
    
    import os
    os.environ['CONTENT_BUCKET'] = 'test-bucket'
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))