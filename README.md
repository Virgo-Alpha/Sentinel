# Sentinel Cybersecurity Triage System

Sentinel is an AWS-native, multi-agent cybersecurity news triage and publishing system that autonomously ingests, processes, and publishes cybersecurity intelligence from RSS feeds and news sources. The system reduces analyst workload by automatically deduplicating content, extracting relevant entities, and intelligently routing items for human review or auto-publication.

## 🏗️ Architecture Overview

```mermaid
graph TB
    subgraph "External Sources"
        RSS[RSS Feeds<br/>21+ Configured Sources]
    end
    
    subgraph "AWS Infrastructure"
        subgraph "Orchestration"
            EB[EventBridge<br/>Scheduled Triggers]
            SF[Step Functions<br/>Workflow Orchestration]
        end
        
        subgraph "Agent Layer"
            IA[Ingestor Agent<br/>Strands → Bedrock AgentCore]
            AA[Analyst Assistant<br/>Strands → Bedrock AgentCore]
        end
        
        subgraph "Storage"
            DDB[(DynamoDB<br/>Articles, Comments, Memory)]
            OS[(OpenSearch<br/>Vector Search)]
            S3[(S3<br/>Raw Content, Artifacts)]
        end
        
        subgraph "Interface"
            AMP[Amplify Web App]
            API[API Gateway]
        end
    end
    
    RSS --> EB
    EB --> SF
    SF --> IA
    AA --> API
    AMP --> API
```

## 🚀 Key Features

### ✅ Implemented Core Components
- **Advanced Configuration Management**: Validated YAML configuration with hot-reloading and comprehensive error checking
- **Smart Keyword Matching**: Exact and fuzzy matching with confidence scoring and context extraction using Levenshtein distance
- **RSS Feed Parser**: Complete Lambda tool for parsing RSS/Atom feeds with HTML normalization and S3 storage
- **Relevance Evaluator**: LLM-powered analysis using AWS Bedrock for content assessment and entity extraction
- **Comprehensive Testing**: Full unit test coverage for configuration, keyword matching, feed parsing, and relevance evaluation

### 🚧 In Development
- **Advanced Deduplication**: Multi-layered approach combining heuristic and semantic methods
- **Human-in-the-Loop Workflow**: Smart escalation with review queues and approval workflows
- **Infrastructure Deployment**: Terraform modules for complete AWS infrastructure
- **Multi-Agent Architecture**: Strands integration with AWS Bedrock AgentCore

### 📋 Planned Features
- **Natural Language Queries**: Chat interface for analysts to query the intelligence database
- **Comprehensive Reporting**: XLSX export with keyword analysis and hit counts
- **Web Application**: Amplify-based dashboard for article review and management

## 📋 Prerequisites

- **AWS Account** with appropriate permissions
- **Python 3.9+** for local development
- **Terraform 1.5+** for infrastructure deployment
- **Node.js 18+** (for Amplify web application)
- **AWS CLI** configured with credentials

## 🛠️ Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd sentinel-cybersecurity-triage

# Set up Python virtual environment
./scripts/setup_venv.sh
source venv/bin/activate

# Copy environment configuration
cp .env.example .env
# Edit .env with your AWS account details
```

### 2. Bootstrap Terraform State

```bash
cd infra/bootstrap
terraform init
terraform apply

# Note the outputs for backend configuration
```

### 3. Configure Backend

```bash
cd ../
# Configure backend with outputs from bootstrap
terraform init -backend-config="bucket=<state-bucket-name>" \
               -backend-config="dynamodb_table=<locks-table-name>"
```

### 4. Deploy Infrastructure

```bash
# Development environment
cd envs/dev
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"

# Production environment (when ready)
cd ../prod
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

### 5. Configure RSS Feeds and Keywords

Update the configuration files with your specific requirements:

- `config/feeds.yaml` - RSS feed sources and categories
- `config/keywords.yaml` - Target keywords for your technology stack
- `config/feature_flags.yaml` - Feature toggles for gradual rollout

**Test Configuration Loading:**

```bash
# Test the configuration system
python3 -c "
from src.shared.config_loader import FeedConfigLoader, KeywordManager

# Test feed configuration
feed_loader = FeedConfigLoader()
config = feed_loader.load_config()
print(f'✓ Loaded {len(config.feeds)} RSS feeds')

# Test keyword configuration  
keyword_manager = KeywordManager()
keyword_config = keyword_manager.load_config()
keywords = keyword_manager.get_all_keywords()
print(f'✓ Loaded {len(keywords)} keywords with fuzzy matching')

# Test keyword matching
sample_text = 'Microsoft Azure vulnerability affects Office 365 users'
matches = keyword_manager.match_keywords(sample_text)
print(f'✓ Found {len(matches)} keyword matches in sample text')
"
```

**Test Lambda Tools:**

```bash
# Test feed parser
python3 -c "
from src.lambda_tools.feed_parser import FeedParser, ContentNormalizer
import os
os.environ['CONTENT_BUCKET'] = 'test-bucket'

# Test content normalization
normalizer = ContentNormalizer()
html = '<h1>Security Alert</h1><p>Critical vulnerability discovered</p>'
result = normalizer.normalize_html(html)
print(f'✓ Normalized content: {len(result[\"normalized_text\"])} characters')
"

# Test relevancy evaluator (requires AWS credentials)
python3 -c "
from src.lambda_tools.relevancy_evaluator import KeywordMatcher
matcher = KeywordMatcher()
content = 'Microsoft Exchange Server vulnerability CVE-2024-1234'
keywords = ['Microsoft', 'Exchange Server', 'CVE', 'vulnerability']
matches = matcher.find_keyword_matches(content, keywords)
print(f'✓ Found {len(matches)} keyword matches with contexts')
"
```

## 📁 Project Structure

```
sentinel-cybersecurity-triage/
├── infra/                          # Terraform infrastructure (planned)
│   ├── modules/                    # Reusable Terraform modules
│   ├── envs/                       # Environment-specific configurations
│   │   ├── dev/                    # Development environment
│   │   └── prod/                   # Production environment
│   ├── bootstrap/                  # Terraform state backend setup
│   └── *.tf                        # Main Terraform configuration
├── src/                            # Source code ✅ IMPLEMENTED
│   ├── lambda_tools/               # Lambda function implementations ✅
│   │   ├── feed_parser.py          # RSS/Atom feed parsing with S3 storage ✅
│   │   └── relevancy_evaluator.py  # Bedrock-powered relevance assessment ✅
│   └── shared/                     # Shared utilities and data models ✅
│       ├── __init__.py             # Package initialization ✅
│       ├── models.py               # Pydantic data models and schemas ✅
│       ├── config.py               # Configuration constants and settings ✅
│       ├── config_loader.py        # Configuration loaders with validation ✅
│       └── keyword_manager.py      # Keyword matching and management ✅
├── config/                         # Configuration files ✅
│   ├── feeds.yaml                  # RSS feed configuration ✅
│   ├── keywords.yaml               # Target keywords configuration ✅
│   └── feature_flags.yaml          # Feature flags for rollout ✅
├── tests/                          # Test files ✅ COMPREHENSIVE COVERAGE
│   ├── test_config_loader.py       # Configuration system tests ✅
│   ├── test_feed_parser.py         # Feed parser and normalizer tests ✅
│   └── test_relevancy_evaluator.py # Relevance evaluation tests ✅
├── scripts/                        # Deployment and utility scripts ✅
├── docs/                           # Documentation ✅
└── requirements.txt                # Python dependencies ✅
```

**Implementation Status:**
- ✅ **Core Configuration System**: Complete with validation and fuzzy matching
- ✅ **Lambda Tools**: FeedParser and RelevancyEvaluator fully implemented
- ✅ **Comprehensive Testing**: 25+ test classes with 100+ test methods
- ✅ **Data Models**: Complete Pydantic schemas for all entities
- 🚧 **Infrastructure**: Terraform modules in development
- 📋 **Web Application**: Amplify frontend planned

## 🔧 Configuration

The system uses a comprehensive configuration management system with validation and hot-reloading capabilities.

### RSS Feeds Configuration

The system monitors 21+ RSS feeds from government agencies, security vendors, and news sources. Feed configuration is managed through `config/feeds.yaml` with full validation and categorization.

**Supported Feed Categories:**
- **Advisories**: Official security advisories from government agencies
- **Alerts**: Urgent security alerts and warnings  
- **Vulnerabilities**: CVE disclosures and vulnerability information
- **Vendor**: Security updates from technology vendors
- **Threat Intel**: Threat intelligence and analysis reports
- **Research**: Security research and technical analysis
- **News**: General cybersecurity news and updates
- **Data Breach**: Data breach notifications and reports
- **Policy**: Cybersecurity policy and regulatory updates

**Example Feed Configuration:**

```yaml
feeds:
  - name: "CISA Known Exploited Vulnerabilities"
    url: "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.xml"
    category: "Vulnerabilities"
    enabled: true
    fetch_interval: "30m"
    description: "CISA KEV catalog feed"

  - name: "Microsoft Security Response Center"
    url: "https://msrc.microsoft.com/blog/feed"
    category: "Vendor"
    enabled: true
    fetch_interval: "2h"
    description: "Microsoft security updates and advisories"
```

**Feed Management Features:**
- URL format validation (HTTP/HTTPS only)
- Fetch interval validation (supports s/m/h/d units)
- Category validation against predefined enums
- Duplicate feed name detection
- Enable/disable individual feeds
- Automatic configuration reloading

### Target Keywords Configuration

The keyword management system provides intelligent relevance assessment with exact and fuzzy matching capabilities. Configure your technology stack keywords in `config/keywords.yaml`.

**Keyword Categories:**
- `cloud_platforms`: Azure, AWS, Google Cloud, etc.
- `security_vendors`: Mimecast, Fortinet, CrowdStrike, etc.
- `enterprise_tools`: Jamf Pro, Tenable, CyberArk, etc.
- `enterprise_systems`: Oracle HCM, FlexCUBE, etc.
- `network_infrastructure`: Cisco devices, switches, etc.
- `virtualization`: Citrix, VMware products, etc.
- `specialized_platforms`: Custom business applications

**Example Keyword Configuration:**

```yaml
cloud_platforms:
  - keyword: "Azure"
    variations: ["Microsoft Azure", "Azure AD", "Azure Active Directory"]
    weight: 1.0
    description: "Microsoft Azure cloud platform"

security_vendors:
  - keyword: "Mimecast"
    variations: ["Mimecast Email Security"]
    weight: 1.0
    description: "Email security platform"

# Keyword matching settings
settings:
  min_confidence: 0.7
  enable_fuzzy_matching: true
  max_edit_distance: 2
  case_sensitive: false
  word_boundary_matching: true
  context_window: 10

# Priority categories for reporting
categories:
  critical: ["Azure", "Microsoft 365", "Amazon Web Services"]
  high: ["Mimecast", "Fortinet", "SentinelOne"]
  medium: ["Jamf Pro", "Tenable", "Oracle HCM"]
  low: ["Moodle", "Brevo", "TextLocal"]
```

**Keyword Matching Features:**
- **Exact Matching**: Direct keyword and variation matching
- **Fuzzy Matching**: Levenshtein distance-based similarity matching
- **Context Extraction**: Captures surrounding text for analysis
- **Confidence Scoring**: Weighted relevance scoring
- **Priority Classification**: Critical/High/Medium/Low categorization
- **Performance Optimization**: Indexed lookups for fast matching

### Configuration Management API

The system provides programmatic access to configuration through dedicated loader classes:

```python
from src.shared.config_loader import FeedConfigLoader, KeywordManager

# Load and validate feed configuration
feed_loader = FeedConfigLoader("config/feeds.yaml")
config = feed_loader.load_config()

# Get feeds by category
news_feeds = feed_loader.get_feeds_by_category(FeedCategory.NEWS)
enabled_feeds = feed_loader.get_enabled_feeds()

# Validate configuration
issues = feed_loader.validate_all_feeds()

# Load keyword configuration with fuzzy matching
keyword_manager = KeywordManager("config/keywords.yaml")
keyword_config = keyword_manager.load_config()

# Find keyword matches in text
text = "Microsoft Azure vulnerability affects Office 365 users"
matches = keyword_manager.match_keywords(text, include_fuzzy=True)

# Get keywords by priority
critical_keywords = keyword_manager.get_critical_keywords()
```

### Feature Flags

Control system capabilities with feature flags in `config/feature_flags.yaml`:

```yaml
enable_agents: false              # Start with direct Lambda orchestration
enable_amplify: false            # Enable web app when ready
enable_opensearch: false         # Enable vector search when ready
enable_auto_publish: false       # Require human review initially
```

## 🎯 Gradual Rollout Strategy

Sentinel is designed for gradual rollout with feature flags:

1. **Phase 1**: Direct Lambda orchestration (`enable_agents: false`)
2. **Phase 2**: Enable Bedrock AgentCore integration (`enable_agents: true`)
3. **Phase 3**: Enable web application (`enable_amplify: true`)
4. **Phase 4**: Enable vector search (`enable_opensearch: true`)
5. **Phase 5**: Enable auto-publishing (`enable_auto_publish: true`)

## 📊 Monitoring and Observability

- **CloudWatch Dashboards**: System metrics, ingestion rates, relevancy rates
- **X-Ray Tracing**: End-to-end request tracing with correlation IDs
- **Cost Tracking**: Daily and monthly cost monitoring with alerts
- **Performance Metrics**: Processing latency, deduplication accuracy
- **Quality Metrics**: Keyword hit rates, human review ratios

## 🔐 Security Features

- **Encryption at Rest**: KMS encryption for S3, DynamoDB, and OpenSearch
- **VPC Endpoints**: Private communication with AWS services
- **IAM Least Privilege**: Scoped permissions for each component
- **PII Detection**: Automatic detection and redaction of sensitive data
- **Audit Trails**: Complete decision traces with tool calls and rationales

## 🧪 Testing

The project includes comprehensive unit tests for all implemented components:

```bash
# Run all tests
pytest tests/

# Run specific test modules
pytest tests/test_config_loader.py -v          # Configuration system tests
pytest tests/test_feed_parser.py -v            # RSS feed parser tests  
pytest tests/test_relevancy_evaluator.py -v    # Relevance evaluation tests

# Run tests with coverage reporting
pytest --cov=src --cov-report=html tests/

# Run specific test classes
pytest tests/test_config_loader.py::TestFeedConfigLoader -v
pytest tests/test_config_loader.py::TestKeywordManager -v
pytest tests/test_feed_parser.py::TestContentNormalizer -v
pytest tests/test_relevancy_evaluator.py::TestBedrockEntityExtractor -v

# Lint and format code
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

**Current Test Coverage (25 test classes, 100+ test methods):**

### Configuration System Tests
- **FeedConfigLoader**: YAML loading, URL validation, interval parsing, category filtering
- **KeywordManager**: Exact matching, fuzzy matching with Levenshtein distance, confidence scoring

### Lambda Tools Tests  
- **FeedParser**: RSS/Atom parsing, HTML normalization, S3 storage, error handling
- **ContentNormalizer**: HTML cleaning, metadata extraction, URL extraction
- **RelevancyEvaluator**: Bedrock integration, keyword matching, entity extraction
- **KeywordMatcher**: Context extraction, hit counting, confidence calculation
- **BedrockEntityExtractor**: CVE extraction, threat actor identification, vendor detection
- **BedrockRelevanceAssessor**: Relevance scoring, rationale generation

### Integration Tests
- **Lambda Handlers**: Event processing, error handling, response formatting
- **Error Scenarios**: Network failures, malformed feeds, API errors, invalid configurations

**Test Quality Features:**
- Mock AWS services (Bedrock, S3) for isolated testing
- Edge case coverage (empty inputs, malformed data, network errors)
- Performance validation (Levenshtein distance, indexed lookups)
- Configuration validation (duplicate detection, format checking)
- Comprehensive error handling and logging verification

## 📚 Documentation

- [Requirements Document](.kiro/specs/sentinel-cybersecurity-triage/requirements.md)
- [Design Document](.kiro/specs/sentinel-cybersecurity-triage/design.md)
- [Implementation Tasks](.kiro/specs/sentinel-cybersecurity-triage/tasks.md)
- [Configuration Examples](docs/configuration_examples.md) - Comprehensive examples of using the configuration system
- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Operations Runbook](docs/operations.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:

- Create an issue in the repository
- Contact the security team at security-team@company.com
- Check the [troubleshooting guide](docs/troubleshooting.md)

## 🏷️ Version

Current version: 0.1.0

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.