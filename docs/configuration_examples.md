# Configuration System Examples

This document provides practical examples of using the Sentinel configuration system for RSS feeds and keyword management.

## Feed Configuration Examples

### Basic Feed Setup

```python
from src.shared.config_loader import FeedConfigLoader
from src.shared.models import FeedCategory

# Initialize the feed configuration loader
feed_loader = FeedConfigLoader("config/feeds.yaml")

# Load and validate configuration
try:
    config = feed_loader.load_config()
    print(f"Loaded {len(config.feeds)} feed configurations")
except ConfigurationError as e:
    print(f"Configuration error: {e}")

# Get feeds by category
vulnerability_feeds = feed_loader.get_feeds_by_category(FeedCategory.VULNERABILITIES)
news_feeds = feed_loader.get_feeds_by_category(FeedCategory.NEWS)

print(f"Vulnerability feeds: {len(vulnerability_feeds)}")
print(f"News feeds: {len(news_feeds)}")

# Get only enabled feeds
enabled_feeds = feed_loader.get_enabled_feeds()
print(f"Enabled feeds: {len(enabled_feeds)}")

# Validate all feed configurations
issues = feed_loader.validate_all_feeds()
if issues:
    print("Configuration issues found:")
    for feed_name, feed_issues in issues.items():
        print(f"  {feed_name}: {feed_issues}")
else:
    print("All feed configurations are valid")
```

### Working with Individual Feeds

```python
# Get specific feed by name
cisa_feed = feed_loader.get_feed_by_name("CISA Known Exploited Vulnerabilities")
if cisa_feed:
    print(f"Feed: {cisa_feed.name}")
    print(f"URL: {cisa_feed.url}")
    print(f"Category: {cisa_feed.category}")
    print(f"Interval: {cisa_feed.fetch_interval}")
    print(f"Enabled: {cisa_feed.enabled}")

# Get all feeds and filter by criteria
all_feeds = feed_loader.get_all_feeds()

# Filter by fetch interval
hourly_feeds = [f for f in all_feeds if f.fetch_interval in ['1h', '60m']]
print(f"Hourly feeds: {len(hourly_feeds)}")

# Filter by category and enabled status
enabled_threat_intel = [
    f for f in all_feeds 
    if f.category == FeedCategory.THREAT_INTEL and f.enabled
]
print(f"Enabled threat intel feeds: {len(enabled_threat_intel)}")
```

## Keyword Management Examples

### Basic Keyword Matching

```python
from src.shared.config_loader import KeywordManager

# Initialize keyword manager
keyword_manager = KeywordManager("config/keywords.yaml")

# Load keyword configuration
config = keyword_manager.load_config()
print(f"Loaded keywords from {len(config.__dict__)} categories")

# Sample text for analysis
sample_text = """
Microsoft has released security updates for Azure Active Directory and Office 365 
following reports of vulnerabilities affecting Mimecast email security integration. 
The issues impact organizations using Citrix StoreFront with Azure authentication.
"""

# Find exact keyword matches
exact_matches = keyword_manager.find_exact_matches(sample_text)
print(f"\nExact matches found: {len(exact_matches)}")

for match in exact_matches:
    print(f"  Keyword: {match['keyword']}")
    print(f"  Matched term: {match['matched_term']}")
    print(f"  Hit count: {match['hit_count']}")
    print(f"  Confidence: {match['confidence']:.2f}")
    print(f"  Weight: {match['weight']}")
    print(f"  Category: {match['category']}")
    print(f"  Context: {match['contexts'][0][:100]}...")
    print()
```

### Fuzzy Matching Examples

```python
# Text with slight misspellings
fuzzy_text = """
Our company uses Azur cloud services and Mimcast for email security.
We also have Citix virtual desktop infrastructure deployed.
"""

# Find fuzzy matches
fuzzy_matches = keyword_manager.find_fuzzy_matches(fuzzy_text)
print(f"Fuzzy matches found: {len(fuzzy_matches)}")

for match in fuzzy_matches:
    print(f"  Keyword: {match['keyword']}")
    print(f"  Matched term: {match['matched_term']}")
    print(f"  Confidence: {match['confidence']:.2f}")
    print(f"  Edit distance: {match['edit_distance']}")
    print()

# Combined exact and fuzzy matching
all_matches = keyword_manager.match_keywords(fuzzy_text, include_fuzzy=True)
print(f"Total matches (exact + fuzzy): {len(all_matches)}")

# Matches are sorted by weighted confidence score
for match in all_matches[:3]:  # Top 3 matches
    weighted_score = match['confidence'] * match['weight']
    print(f"  {match['keyword']}: {weighted_score:.3f} (conf: {match['confidence']:.2f}, weight: {match['weight']})")
```

### Working with Keyword Categories

```python
# Get keywords by category
cloud_keywords = keyword_manager.get_keywords_by_category('cloud_platforms')
security_keywords = keyword_manager.get_keywords_by_category('security_vendors')

print(f"Cloud platform keywords: {len(cloud_keywords)}")
print(f"Security vendor keywords: {len(security_keywords)}")

# Get priority-based keywords
critical_keywords = keyword_manager.get_critical_keywords()
high_priority_keywords = keyword_manager.get_high_priority_keywords()

print(f"Critical keywords: {len(critical_keywords)}")
for kw in critical_keywords:
    print(f"  - {kw.keyword} (weight: {kw.weight})")

print(f"High priority keywords: {len(high_priority_keywords)}")
for kw in high_priority_keywords:
    print(f"  - {kw.keyword} (weight: {kw.weight})")

# Get all keywords across categories
all_keywords = keyword_manager.get_all_keywords()
print(f"Total keywords loaded: {len(all_keywords)}")

# Get keyword statistics
stats = keyword_manager.get_keyword_statistics()
print(f"\nKeyword Statistics:")
print(f"  Total keywords: {stats['total_keywords']}")
print(f"  Total variations: {stats['total_variations']}")
print(f"  Categories:")
for category, category_stats in stats['categories'].items():
    print(f"    {category}: {category_stats['count']} keywords, {category_stats['variations']} variations")
```

### Configuration Validation

```python
# Validate keyword configurations
keyword_issues = keyword_manager.validate_keywords()
if keyword_issues:
    print("Keyword configuration issues:")
    for category, issues in keyword_issues.items():
        print(f"  {category}:")
        for issue in issues:
            print(f"    - {issue}")
else:
    print("All keyword configurations are valid")

# Validate feed configurations
feed_issues = feed_loader.validate_all_feeds()
if feed_issues:
    print("Feed configuration issues:")
    for feed_name, issues in feed_issues.items():
        print(f"  {feed_name}:")
        for issue in issues:
            print(f"    - {issue}")
else:
    print("All feed configurations are valid")
```

## Advanced Usage Patterns

### Hot Reloading Configuration

```python
import time
from pathlib import Path

# Monitor configuration file for changes
config_file = Path("config/keywords.yaml")
last_modified = config_file.stat().st_mtime

while True:
    current_modified = config_file.stat().st_mtime
    
    if current_modified > last_modified:
        print("Configuration file changed, reloading...")
        try:
            # Reload configuration
            new_config = keyword_manager.reload_config()
            print(f"Reloaded {len(new_config.__dict__)} keyword categories")
            last_modified = current_modified
        except Exception as e:
            print(f"Failed to reload configuration: {e}")
    
    time.sleep(5)  # Check every 5 seconds
```

### Custom Keyword Analysis

```python
def analyze_article_relevance(article_text, title=""):
    """Analyze article relevance using keyword matching."""
    
    # Combine title and content for analysis
    full_text = f"{title} {article_text}"
    
    # Find all keyword matches
    matches = keyword_manager.match_keywords(full_text, include_fuzzy=True)
    
    if not matches:
        return {
            'is_relevant': False,
            'relevance_score': 0.0,
            'matched_keywords': [],
            'analysis': 'No relevant keywords found'
        }
    
    # Calculate overall relevance score
    total_score = sum(match['confidence'] * match['weight'] for match in matches)
    max_possible_score = len(matches) * 1.0  # Maximum confidence * weight
    relevance_score = min(total_score / max_possible_score, 1.0) if max_possible_score > 0 else 0.0
    
    # Extract matched keywords and their details
    matched_keywords = []
    for match in matches:
        matched_keywords.append({
            'keyword': match['keyword'],
            'category': match['category'],
            'confidence': match['confidence'],
            'hit_count': match['hit_count'],
            'contexts': match['contexts'][:2]  # First 2 contexts
        })
    
    # Determine relevance threshold
    is_relevant = relevance_score >= 0.3  # 30% threshold
    
    return {
        'is_relevant': is_relevant,
        'relevance_score': relevance_score,
        'matched_keywords': matched_keywords,
        'analysis': f"Found {len(matches)} keyword matches with {relevance_score:.1%} relevance"
    }

# Example usage
article_text = """
A critical vulnerability has been discovered in Microsoft Azure Active Directory 
that could allow attackers to bypass authentication mechanisms. The vulnerability 
affects organizations using Mimecast email security with Azure AD integration.
Microsoft has released patches and recommends immediate deployment.
"""

result = analyze_article_relevance(article_text, "Critical Azure AD Vulnerability")
print(f"Relevant: {result['is_relevant']}")
print(f"Score: {result['relevance_score']:.1%}")
print(f"Analysis: {result['analysis']}")
print(f"Keywords: {[kw['keyword'] for kw in result['matched_keywords']]}")
```

## Error Handling Best Practices

```python
from src.shared.config_loader import ConfigurationError

def safe_config_loading():
    """Demonstrate proper error handling for configuration loading."""
    
    try:
        # Attempt to load feed configuration
        feed_loader = FeedConfigLoader("config/feeds.yaml")
        feed_config = feed_loader.load_config()
        print(f"✓ Loaded {len(feed_config.feeds)} feeds")
        
    except FileNotFoundError:
        print("✗ Feed configuration file not found")
        return False
    except ConfigurationError as e:
        print(f"✗ Feed configuration error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error loading feeds: {e}")
        return False
    
    try:
        # Attempt to load keyword configuration
        keyword_manager = KeywordManager("config/keywords.yaml")
        keyword_config = keyword_manager.load_config()
        total_keywords = len(keyword_manager.get_all_keywords())
        print(f"✓ Loaded {total_keywords} keywords")
        
    except FileNotFoundError:
        print("✗ Keyword configuration file not found")
        return False
    except ConfigurationError as e:
        print(f"✗ Keyword configuration error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error loading keywords: {e}")
        return False
    
    return True

# Run safe configuration loading
if safe_config_loading():
    print("✓ All configurations loaded successfully")
else:
    print("✗ Configuration loading failed")
```

This configuration system provides a robust foundation for managing RSS feeds and keyword matching in the Sentinel cybersecurity triage system, with comprehensive validation, error handling, and performance optimization.