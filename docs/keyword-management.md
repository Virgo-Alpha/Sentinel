# Keyword Management Guide

This guide provides comprehensive instructions for managing target keywords in the Sentinel Cybersecurity Triage System, including configuration, best practices, and troubleshooting.

## Table of Contents

1. [Overview](#overview)
2. [Keyword Configuration](#keyword-configuration)
3. [Keyword Categories](#keyword-categories)
4. [Matching Algorithms](#matching-algorithms)
5. [Best Practices](#best-practices)
6. [Examples](#examples)
7. [Testing and Validation](#testing-and-validation)
8. [Troubleshooting](#troubleshooting)
9. [Performance Optimization](#performance-optimization)

## Overview

The keyword management system is the core component that determines which cybersecurity content is relevant to your organization. It uses advanced matching algorithms including exact matching, fuzzy matching, and context analysis to identify relevant articles from RSS feeds.

### Key Features

- **Multi-tier Matching**: Exact, fuzzy, and context-aware matching
- **Weighted Scoring**: Configurable importance weights for different keywords
- **Category-based Organization**: Logical grouping of related keywords
- **Performance Optimization**: Indexed lookups and efficient algorithms
- **Real-time Updates**: Hot-reloading of keyword configurations
- **Comprehensive Validation**: Automatic validation of keyword configurations

## Keyword Configuration

Keywords are configured in the `config/keywords.yaml` file using a structured YAML format.

### Basic Structure

```yaml
# Keyword categories
cloud_platforms:
  - keyword: "Azure"
    variations: ["Microsoft Azure", "Azure AD", "Azure Active Directory"]
    weight: 1.0
    description: "Microsoft Azure cloud platform"
    context_required: false

security_vendors:
  - keyword: "Mimecast"
    variations: ["Mimecast Email Security", "Mimecast Gateway"]
    weight: 0.9
    description: "Email security platform"
    context_required: false

# Global matching settings
settings:
  min_confidence: 0.7
  enable_fuzzy_matching: true
  max_edit_distance: 2
  case_sensitive: false
  word_boundary_matching: true
  context_window: 10

# Priority classifications
categories:
  critical: ["Azure", "Microsoft 365", "Amazon Web Services"]
  high: ["Mimecast", "Fortinet", "SentinelOne"]
  medium: ["Jamf Pro", "Tenable", "Oracle HCM"]
  low: ["Moodle", "Brevo", "TextLocal"]
```

### Configuration Fields

#### Keyword Entry Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `keyword` | string | Yes | Primary keyword to match |
| `variations` | list | No | Alternative spellings and variations |
| `weight` | float | No | Importance weight (0.0-1.0, default: 1.0) |
| `description` | string | No | Human-readable description |
| `context_required` | boolean | No | Whether context validation is required |

#### Global Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `min_confidence` | float | 0.7 | Minimum confidence score for matches |
| `enable_fuzzy_matching` | boolean | true | Enable fuzzy string matching |
| `max_edit_distance` | integer | 2 | Maximum Levenshtein distance for fuzzy matching |
| `case_sensitive` | boolean | false | Whether matching is case-sensitive |
| `word_boundary_matching` | boolean | true | Require word boundaries for matches |
| `context_window` | integer | 10 | Number of words to capture around matches |

## Keyword Categories

Organize keywords into logical categories based on your technology stack and security priorities.

### Recommended Categories

#### 1. Cloud Platforms
Technologies and services your organization uses in the cloud.

```yaml
cloud_platforms:
  - keyword: "Azure"
    variations: ["Microsoft Azure", "Azure AD", "Azure Active Directory", "Entra ID"]
    weight: 1.0
    description: "Microsoft Azure cloud platform and identity services"
    
  - keyword: "Amazon Web Services"
    variations: ["AWS", "Amazon AWS", "EC2", "S3", "Lambda"]
    weight: 1.0
    description: "Amazon Web Services cloud platform"
    
  - keyword: "Google Cloud"
    variations: ["GCP", "Google Cloud Platform", "Google Workspace"]
    weight: 0.9
    description: "Google Cloud Platform and Workspace services"
```

#### 2. Security Vendors
Security tools and platforms used by your organization.

```yaml
security_vendors:
  - keyword: "Mimecast"
    variations: ["Mimecast Email Security", "Mimecast Gateway"]
    weight: 1.0
    description: "Email security and archiving platform"
    
  - keyword: "Fortinet"
    variations: ["FortiGate", "FortiOS", "FortiAnalyzer", "FortiManager"]
    weight: 0.9
    description: "Network security appliances and software"
    
  - keyword: "SentinelOne"
    variations: ["Sentinel One", "S1"]
    weight: 0.9
    description: "Endpoint detection and response platform"
```

#### 3. Enterprise Tools
Business applications and enterprise software.

```yaml
enterprise_tools:
  - keyword: "Jamf Pro"
    variations: ["Jamf", "JAMF Pro"]
    weight: 0.8
    description: "Apple device management platform"
    
  - keyword: "Tenable"
    variations: ["Tenable.io", "Nessus", "Tenable Security Center"]
    weight: 0.8
    description: "Vulnerability management platform"
    
  - keyword: "Oracle HCM"
    variations: ["Oracle Human Capital Management", "Oracle HCM Cloud"]
    weight: 0.7
    description: "Human resources management system"
```

#### 4. Network Infrastructure
Network devices and infrastructure components.

```yaml
network_infrastructure:
  - keyword: "Cisco"
    variations: ["Cisco Systems", "Cisco ASA", "Cisco IOS"]
    weight: 0.8
    description: "Network equipment and software"
    
  - keyword: "Juniper"
    variations: ["Juniper Networks", "JunOS"]
    weight: 0.7
    description: "Network infrastructure equipment"
```

#### 5. Virtualization Platforms
Virtualization and container technologies.

```yaml
virtualization:
  - keyword: "VMware"
    variations: ["VMware vSphere", "ESXi", "vCenter", "VMware Workstation"]
    weight: 0.8
    description: "Virtualization platform and tools"
    
  - keyword: "Citrix"
    variations: ["Citrix XenApp", "Citrix XenDesktop", "Citrix Virtual Apps"]
    weight: 0.7
    description: "Application virtualization and delivery"
```

## Matching Algorithms

The system uses multiple matching algorithms to identify relevant content.

### 1. Exact Matching

Direct string matching with optional case sensitivity and word boundary detection.

```python
# Example: Exact match for "Azure"
text = "Microsoft Azure vulnerability affects cloud services"
matches = ["Azure"]  # Direct match found
```

### 2. Variation Matching

Matches against predefined variations and alternative spellings.

```python
# Example: Variation matching
keyword = "Azure"
variations = ["Microsoft Azure", "Azure AD", "Azure Active Directory"]
text = "Azure Active Directory authentication bypass discovered"
matches = ["Azure Active Directory"]  # Variation match found
```

### 3. Fuzzy Matching

Uses Levenshtein distance algorithm to find similar strings within a configurable edit distance.

```python
# Example: Fuzzy matching with max_edit_distance = 2
keyword = "Fortinet"
text = "Fortnet firewall vulnerability reported"  # Missing 'i'
matches = ["Fortnet"]  # Fuzzy match found (edit distance = 1)
```

### 4. Context Analysis

Captures surrounding text to provide context for matches and improve relevance assessment.

```python
# Example: Context extraction
text = "The Azure vulnerability affects authentication services in cloud environments"
match = {
    "keyword": "Azure",
    "context": "The Azure vulnerability affects authentication services",
    "position": 4,
    "confidence": 1.0
}
```

## Best Practices

### 1. Keyword Selection

**Do:**
- Include primary product names and common abbreviations
- Add variations for different spellings and formats
- Focus on technologies actually used in your organization
- Include both vendor names and specific product names

**Don't:**
- Add overly generic terms that cause false positives
- Include keywords for technologies you don't use
- Use variations that are too similar to each other
- Add keywords without proper context consideration

### 2. Weight Assignment

**Critical Keywords (weight: 1.0)**
- Core infrastructure platforms (Azure, AWS)
- Primary security tools (main EDR, email security)
- Business-critical applications

**High Priority Keywords (weight: 0.8-0.9)**
- Secondary security tools
- Important business applications
- Network infrastructure

**Medium Priority Keywords (weight: 0.6-0.7)**
- Supporting tools and applications
- Development platforms
- Monitoring tools

**Low Priority Keywords (weight: 0.3-0.5)**
- Legacy systems
- Rarely used applications
- Generic technology terms

### 3. Variation Management

```yaml
# Good: Comprehensive variations
- keyword: "Microsoft 365"
  variations: [
    "Office 365", "O365", "M365", 
    "Microsoft Office 365", "Office365",
    "Microsoft 365 Business", "Microsoft 365 Enterprise"
  ]

# Bad: Redundant or overly specific variations
- keyword: "Microsoft 365"
  variations: [
    "Microsoft 365", "microsoft 365", "MICROSOFT 365"  # Redundant if case_sensitive: false
  ]
```

### 4. Context Requirements

Use `context_required: true` for ambiguous keywords that need additional context:

```yaml
# Ambiguous keyword that needs context
- keyword: "Teams"
  variations: ["Microsoft Teams", "MS Teams"]
  weight: 0.7
  context_required: true  # Avoids matching sports teams, etc.
  
# Specific keyword that doesn't need context
- keyword: "Azure Active Directory"
  variations: ["Azure AD", "AAD"]
  weight: 1.0
  context_required: false  # Specific enough to not need context
```

## Examples

### Example 1: Cloud-First Organization

```yaml
cloud_platforms:
  - keyword: "Azure"
    variations: ["Microsoft Azure", "Azure AD", "Azure Active Directory", "Entra ID"]
    weight: 1.0
    description: "Primary cloud platform"
    
  - keyword: "Microsoft 365"
    variations: ["Office 365", "O365", "M365"]
    weight: 1.0
    description: "Primary productivity suite"

security_vendors:
  - keyword: "Microsoft Defender"
    variations: ["Windows Defender", "Defender for Endpoint", "Defender ATP"]
    weight: 1.0
    description: "Primary endpoint protection"

settings:
  min_confidence: 0.8  # Higher threshold for cloud-focused org
  enable_fuzzy_matching: true
  max_edit_distance: 1  # Stricter fuzzy matching
```

### Example 2: Hybrid Infrastructure Organization

```yaml
cloud_platforms:
  - keyword: "Azure"
    variations: ["Microsoft Azure", "Azure AD"]
    weight: 0.9
    
  - keyword: "Amazon Web Services"
    variations: ["AWS", "EC2", "S3"]
    weight: 0.8

network_infrastructure:
  - keyword: "Cisco"
    variations: ["Cisco ASA", "Cisco IOS", "Cisco Catalyst"]
    weight: 0.9
    description: "Primary network infrastructure"
    
  - keyword: "VMware"
    variations: ["vSphere", "ESXi", "vCenter"]
    weight: 0.9
    description: "Virtualization platform"

settings:
  min_confidence: 0.7  # Balanced threshold
  enable_fuzzy_matching: true
  max_edit_distance: 2
```

### Example 3: Security-Focused Configuration

```yaml
security_vendors:
  - keyword: "CrowdStrike"
    variations: ["Falcon", "CrowdStrike Falcon"]
    weight: 1.0
    description: "Primary EDR solution"
    
  - keyword: "Splunk"
    variations: ["Splunk Enterprise", "Splunk Cloud"]
    weight: 1.0
    description: "SIEM platform"
    
  - keyword: "Palo Alto"
    variations: ["Palo Alto Networks", "PAN", "Prisma", "Cortex"]
    weight: 0.9
    description: "Network security platform"

# Security-specific categories
categories:
  critical: ["CrowdStrike", "Splunk", "Palo Alto"]
  high: ["Fortinet", "Check Point", "Symantec"]
  medium: ["Trend Micro", "McAfee", "Kaspersky"]

settings:
  min_confidence: 0.75
  context_window: 15  # Larger context for security analysis
```

## Testing and Validation

### 1. Configuration Validation

Test your keyword configuration before deployment:

```bash
# Validate configuration syntax
python3 -c "
from src.shared.config_loader import KeywordManager
manager = KeywordManager('config/keywords.yaml')
config = manager.load_config()
print(f'✓ Configuration valid: {len(manager.get_all_keywords())} keywords loaded')
"

# Test keyword matching
python3 scripts/test-keyword-matching.py -c config/keywords.yaml -t
```

### 2. Interactive Testing

Use the interactive testing tool to validate keyword matching:

```bash
# Start interactive testing
python3 scripts/test-keyword-matching.py -c config/keywords.yaml -i

# Example test inputs:
> Microsoft Azure vulnerability affects authentication
> Fortinet FortiGate firewall exploit discovered
> CrowdStrike Falcon detects new malware variant
```

### 3. Batch Testing

Create test cases for automated validation:

```python
# test_cases.py
test_cases = [
    {
        'text': 'Microsoft Azure Active Directory vulnerability CVE-2024-1234',
        'expected_keywords': ['Azure', 'Microsoft', 'Azure Active Directory'],
        'expected_categories': ['cloud_platforms']
    },
    {
        'text': 'Fortinet FortiGate SSL VPN exploit in the wild',
        'expected_keywords': ['Fortinet', 'FortiGate'],
        'expected_categories': ['security_vendors']
    }
]
```

### 4. Performance Testing

Monitor keyword matching performance:

```bash
# Performance benchmark
python3 -c "
import time
from src.shared.keyword_manager import KeywordManager

manager = KeywordManager()
text = 'Microsoft Azure vulnerability affects Office 365 and Teams applications'

start_time = time.time()
for _ in range(1000):
    matches = manager.match_keywords(text)
end_time = time.time()

print(f'Performance: {1000 / (end_time - start_time):.1f} matches/second')
"
```

## Troubleshooting

### Common Issues

#### 1. No Matches Found

**Problem**: Keywords not matching expected content.

**Solutions:**
- Check keyword spelling and variations
- Verify `case_sensitive` setting
- Review `min_confidence` threshold
- Enable fuzzy matching if disabled
- Check `word_boundary_matching` setting

```yaml
# Debug configuration
settings:
  min_confidence: 0.5  # Lower threshold temporarily
  enable_fuzzy_matching: true
  max_edit_distance: 3  # Increase for more fuzzy matches
  case_sensitive: false
  word_boundary_matching: false  # Disable for partial matches
```

#### 2. Too Many False Positives

**Problem**: Keywords matching irrelevant content.

**Solutions:**
- Increase `min_confidence` threshold
- Enable `context_required` for ambiguous keywords
- Use more specific keyword variations
- Enable `word_boundary_matching`

```yaml
# Stricter configuration
- keyword: "Teams"
  variations: ["Microsoft Teams", "MS Teams"]
  context_required: true  # Require security context
  weight: 0.8

settings:
  min_confidence: 0.8  # Higher threshold
  word_boundary_matching: true  # Exact word matches only
```

#### 3. Performance Issues

**Problem**: Slow keyword matching performance.

**Solutions:**
- Reduce number of keywords
- Optimize keyword variations
- Disable fuzzy matching for high-frequency keywords
- Increase `min_confidence` to reduce processing

```yaml
# Performance-optimized configuration
settings:
  enable_fuzzy_matching: false  # Disable for better performance
  min_confidence: 0.8  # Higher threshold reduces processing
  max_edit_distance: 1  # Lower distance for faster fuzzy matching
```

#### 4. Configuration Errors

**Problem**: YAML syntax or validation errors.

**Solutions:**
- Validate YAML syntax using online validators
- Check indentation (use spaces, not tabs)
- Verify required fields are present
- Use configuration validation tools

```bash
# Validate YAML syntax
python3 -c "
import yaml
with open('config/keywords.yaml', 'r') as f:
    config = yaml.safe_load(f)
print('✓ YAML syntax valid')
"

# Validate configuration structure
python3 -c "
from src.shared.config_loader import KeywordManager
manager = KeywordManager('config/keywords.yaml')
issues = manager.validate_config()
if issues:
    for issue in issues:
        print(f'❌ {issue}')
else:
    print('✓ Configuration valid')
"
```

### Debug Mode

Enable debug logging for detailed matching information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from src.shared.keyword_manager import KeywordManager
manager = KeywordManager()
matches = manager.match_keywords("test text", debug=True)
```

## Performance Optimization

### 1. Keyword Organization

**Optimize for Performance:**
- Group related keywords together
- Use specific keywords over generic ones
- Limit variations to essential alternatives
- Remove redundant or unused keywords

### 2. Matching Settings

**Performance vs. Accuracy Trade-offs:**

```yaml
# High Performance (lower accuracy)
settings:
  enable_fuzzy_matching: false
  min_confidence: 0.8
  word_boundary_matching: true
  context_window: 5

# High Accuracy (lower performance)
settings:
  enable_fuzzy_matching: true
  max_edit_distance: 3
  min_confidence: 0.6
  context_window: 20
```

### 3. Caching and Indexing

The system automatically optimizes performance through:
- **Keyword Indexing**: Pre-built indexes for fast lookups
- **Result Caching**: Caches frequent matches
- **Batch Processing**: Processes multiple articles efficiently

### 4. Monitoring Performance

Track keyword matching performance:

```python
# Performance metrics
from src.shared.keyword_manager import KeywordManager

manager = KeywordManager()
metrics = manager.get_performance_metrics()

print(f"Average match time: {metrics['avg_match_time_ms']:.2f}ms")
print(f"Cache hit rate: {metrics['cache_hit_rate']:.1%}")
print(f"Total keywords: {metrics['total_keywords']}")
```

## Advanced Configuration

### 1. Custom Scoring Functions

Define custom scoring logic for specific use cases:

```yaml
# Custom scoring weights
scoring:
  exact_match_bonus: 1.0
  variation_match_bonus: 0.8
  fuzzy_match_penalty: 0.3
  context_bonus: 0.2
  frequency_weight: 0.1
```

### 2. Category-Specific Settings

Apply different settings to different categories:

```yaml
category_settings:
  cloud_platforms:
    min_confidence: 0.9
    enable_fuzzy_matching: false
    
  security_vendors:
    min_confidence: 0.8
    enable_fuzzy_matching: true
    max_edit_distance: 1
    
  enterprise_tools:
    min_confidence: 0.7
    context_required: true
```

### 3. Dynamic Keyword Loading

Load keywords from external sources:

```python
# Load keywords from database or API
from src.shared.keyword_manager import KeywordManager

manager = KeywordManager()
manager.load_keywords_from_database()
manager.load_keywords_from_api("https://api.company.com/keywords")
```

## Conclusion

Effective keyword management is crucial for the success of the Sentinel system. By following the best practices and examples in this guide, you can configure keywords that accurately identify relevant cybersecurity content for your organization while maintaining good performance.

Regular review and updates of your keyword configuration will ensure the system continues to provide relevant and actionable intelligence as your technology stack and threat landscape evolve.

For additional support:
- Review the [troubleshooting section](#troubleshooting)
- Test configurations using the provided tools
- Monitor performance metrics regularly
- Update keywords based on new technologies and threats