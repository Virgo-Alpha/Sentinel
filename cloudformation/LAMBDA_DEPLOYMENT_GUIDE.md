# Lambda Functions Deployment Guide

This guide covers deploying Lambda functions with standalone agent implementations for the Sentinel cybersecurity platform.

## Overview

The Sentinel platform includes 11 Lambda functions that implement standalone agent capabilities:

### Core Processing Functions
1. **Feed Parser** - RSS feed parsing and article extraction
2. **Relevancy Evaluator** - AI-powered relevance assessment
3. **Dedup Tool** - Semantic deduplication using embeddings
4. **Guardrail Tool** - Content policy enforcement
5. **Storage Tool** - Article storage and retrieval
6. **Human Escalation** - Review workflow management
7. **Notifier** - Email and alert notifications

### API Functions
8. **Analyst Assistant** - AI chat interface for analysts
9. **Query Knowledge Base** - RAG-powered knowledge queries
10. **Commentary API** - Article comments and annotations
11. **Publish Decision** - Human review decision processing

## Prerequisites

### 1. Source Code Structure
Create the following directory structure in your project:

```
src/
├── common/                          # Shared utilities
│   ├── __init__.py
│   ├── aws_clients.py              # AWS service clients
│   ├── bedrock_utils.py            # Bedrock model utilities
│   ├── dynamodb_utils.py           # DynamoDB helpers
│   ├── s3_utils.py                 # S3 operations
│   └── logging_utils.py            # Logging configuration
├── lambda_tools/
│   ├── feed_parser/
│   │   ├── lambda_function.py      # Main handler
│   │   ├── feed_processor.py       # RSS processing logic
│   │   └── requirements.txt        # Dependencies
│   ├── relevancy_evaluator/
│   │   ├── lambda_function.py
│   │   ├── relevancy_agent.py      # AI relevance assessment
│   │   └── requirements.txt
│   ├── dedup_tool/
│   │   ├── lambda_function.py
│   │   ├── dedup_agent.py          # Semantic deduplication
│   │   └── requirements.txt
│   ├── guardrail_tool/
│   │   ├── lambda_function.py
│   │   ├── guardrail_agent.py      # Policy enforcement
│   │   └── requirements.txt
│   ├── storage_tool/
│   │   ├── lambda_function.py
│   │   ├── storage_manager.py      # Storage operations
│   │   └── requirements.txt
│   ├── human_escalation/
│   │   ├── lambda_function.py
│   │   ├── escalation_handler.py   # Review workflow
│   │   └── requirements.txt
│   ├── notifier/
│   │   ├── lambda_function.py
│   │   ├── notification_service.py # Email/alert service
│   │   └── requirements.txt
│   ├── analyst_assistant/
│   │   ├── lambda_function.py
│   │   ├── chat_agent.py           # AI chat interface
│   │   └── requirements.txt
│   ├── query_kb/
│   │   ├── lambda_function.py
│   │   ├── rag_service.py          # Knowledge base queries
│   │   └── requirements.txt
│   ├── commentary_api/
│   │   ├── lambda_function.py
│   │   ├── comment_manager.py      # Comment operations
│   │   └── requirements.txt
│   └── publish_decision/
│       ├── lambda_function.py
│       ├── decision_processor.py   # Review decisions
│       └── requirements.txt
```

### 2. Required Dependencies

Each Lambda function should have a `requirements.txt` file with necessary dependencies:

```txt
# Common dependencies for most functions
boto3>=1.34.0
botocore>=1.34.0
requests>=2.31.0
python-dateutil>=2.8.2

# For AI/ML functions (relevancy, dedup, guardrail, analyst-assistant)
numpy>=1.24.0
scikit-learn>=1.3.0

# For feed parsing
feedparser>=6.0.10
beautifulsoup4>=4.12.0
lxml>=4.9.0

# For email notifications
email-validator>=2.0.0
jinja2>=3.1.0
```

## Deployment Steps

### Step 1: Prepare Source Code

1. **Create Lambda Function Templates**

   Example `lambda_function.py` for Feed Parser:

   ```python
   import json
   import logging
   import os
   from typing import Dict, Any
   
   # Import common utilities
   from aws_clients import get_bedrock_client, get_dynamodb_client
   from logging_utils import setup_logging
   from feed_processor import FeedProcessor
   
   # Setup logging
   logger = setup_logging(__name__)
   
   def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
       """
       Feed Parser Lambda Handler
       Processes RSS feeds and extracts articles for cybersecurity triage
       """
       try:
           logger.info(f"Processing feed parser request: {json.dumps(event)}")
           
           # Initialize processor
           processor = FeedProcessor(
               bedrock_client=get_bedrock_client(),
               dynamodb_client=get_dynamodb_client(),
               articles_table=os.environ['ARTICLES_TABLE'],
               content_bucket=os.environ['CONTENT_BUCKET']
           )
           
           # Process feeds
           result = processor.process_feeds(
               feed_configs=event.get('feedConfigs', []),
               batch_size=event.get('batchSize', 10)
           )
           
           logger.info(f"Feed processing completed: {result['summary']}")
           
           return {
               'statusCode': 200,
               'body': json.dumps(result)
           }
           
       except Exception as e:
           logger.error(f"Feed parser error: {str(e)}", exc_info=True)
           return {
               'statusCode': 500,
               'body': json.dumps({
                   'error': str(e),
                   'type': 'FeedParserError'
               })
           }
   ```

2. **Create Agent Implementation Classes**

   Example `feed_processor.py`:

   ```python
   import feedparser
   import requests
   from datetime import datetime
   from typing import List, Dict, Any
   import logging
   
   logger = logging.getLogger(__name__)
   
   class FeedProcessor:
       """Standalone agent implementation for RSS feed processing"""
       
       def __init__(self, bedrock_client, dynamodb_client, articles_table, content_bucket):
           self.bedrock_client = bedrock_client
           self.dynamodb_client = dynamodb_client
           self.articles_table = articles_table
           self.content_bucket = content_bucket
       
       def process_feeds(self, feed_configs: List[Dict], batch_size: int = 10) -> Dict[str, Any]:
           """Process multiple RSS feeds and extract articles"""
           
           all_articles = []
           processing_summary = {
               'feeds_processed': 0,
               'articles_extracted': 0,
               'errors': []
           }
           
           for feed_config in feed_configs[:batch_size]:
               try:
                   articles = self._process_single_feed(feed_config)
                   all_articles.extend(articles)
                   processing_summary['feeds_processed'] += 1
                   processing_summary['articles_extracted'] += len(articles)
                   
               except Exception as e:
                   logger.error(f"Error processing feed {feed_config.get('url')}: {str(e)}")
                   processing_summary['errors'].append({
                       'feed_url': feed_config.get('url'),
                       'error': str(e)
                   })
           
           return {
               'articles': all_articles,
               'summary': processing_summary
           }
       
       def _process_single_feed(self, feed_config: Dict) -> List[Dict]:
           """Process a single RSS feed"""
           
           feed_url = feed_config['url']
           feed_source = feed_config.get('source', 'unknown')
           
           logger.info(f"Processing feed: {feed_url}")
           
           # Parse RSS feed
           feed = feedparser.parse(feed_url)
           
           if feed.bozo:
               logger.warning(f"Feed parsing warning for {feed_url}: {feed.bozo_exception}")
           
           articles = []
           
           for entry in feed.entries:
               try:
                   article = self._extract_article_data(entry, feed_source)
                   if self._is_cybersecurity_relevant(article):
                       articles.append(article)
                       
               except Exception as e:
                   logger.error(f"Error extracting article from {feed_url}: {str(e)}")
           
           logger.info(f"Extracted {len(articles)} articles from {feed_url}")
           return articles
       
       def _extract_article_data(self, entry, source: str) -> Dict[str, Any]:
           """Extract structured data from RSS entry"""
           
           return {
               'article_id': self._generate_article_id(entry.link),
               'title': entry.get('title', ''),
               'summary': entry.get('summary', ''),
               'content': entry.get('content', [{}])[0].get('value', ''),
               'link': entry.get('link', ''),
               'published': entry.get('published', ''),
               'source': source,
               'tags': [tag.term for tag in entry.get('tags', [])],
               'extracted_at': datetime.utcnow().isoformat(),
               'state': 'extracted'
           }
       
       def _is_cybersecurity_relevant(self, article: Dict) -> bool:
           """Basic cybersecurity relevance check"""
           
           cybersec_keywords = [
               'cybersecurity', 'security', 'vulnerability', 'malware',
               'ransomware', 'phishing', 'breach', 'attack', 'threat',
               'exploit', 'patch', 'zero-day', 'incident', 'forensics'
           ]
           
           text = f"{article['title']} {article['summary']}".lower()
           
           return any(keyword in text for keyword in cybersec_keywords)
       
       def _generate_article_id(self, url: str) -> str:
           """Generate unique article ID from URL"""
           import hashlib
           return hashlib.md5(url.encode()).hexdigest()
   ```

### Step 2: Deploy Infrastructure

1. **Deploy CloudFormation Stack**
   ```bash
   # Deploy the updated CloudFormation template
   ./deploy.sh -e prod -a update
   
   # Get the artifacts bucket name from outputs
   ARTIFACTS_BUCKET=$(aws cloudformation describe-stacks \
     --stack-name sentinel-prod-complete \
     --query 'Stacks[0].Outputs[?OutputKey==`ArtifactsBucketName`].OutputValue' \
     --output text)
   
   echo "Artifacts bucket: $ARTIFACTS_BUCKET"
   ```

### Step 3: Build and Deploy Lambda Packages

1. **Use the Deployment Script**
   ```bash
   # Deploy all Lambda functions
   ./deploy-lambda-packages.sh -e prod -b $ARTIFACTS_BUCKET
   
   # Deploy specific function
   ./deploy-lambda-packages.sh -e prod -b $ARTIFACTS_BUCKET -f feed-parser
   
   # Clean deployment (removes build artifacts)
   ./deploy-lambda-packages.sh -e prod -b $ARTIFACTS_BUCKET -c
   ```

2. **Manual Deployment (Alternative)**
   ```bash
   # Build packages manually
   cd src/lambda_tools/feed_parser
   zip -r ../../../cloudformation/lambda-builds/feed-parser.zip . -x "*.pyc" "__pycache__/*"
   
   # Upload to S3
   aws s3 cp ../../../cloudformation/lambda-builds/feed-parser.zip \
     s3://$ARTIFACTS_BUCKET/lambda-packages/feed-parser.zip
   
   # Update Lambda function
   aws lambda update-function-code \
     --function-name sentinel-prod-feed-parser \
     --s3-bucket $ARTIFACTS_BUCKET \
     --s3-key lambda-packages/feed-parser.zip
   ```

### Step 4: Configure Environment Variables

The CloudFormation template automatically sets environment variables, but you can update them:

```bash
# Update environment variables for a function
aws lambda update-function-configuration \
  --function-name sentinel-prod-feed-parser \
  --environment Variables='{
    "ENVIRONMENT":"prod",
    "PROJECT_NAME":"sentinel",
    "ARTICLES_TABLE":"sentinel-prod-articles",
    "CONTENT_BUCKET":"sentinel-prod-content-abc123",
    "BEDROCK_MODEL_ID":"anthropic.claude-3-5-sonnet-20241022-v2:0",
    "MAX_CONCURRENT_FEEDS":"15",
    "LOG_LEVEL":"INFO"
  }'
```

### Step 5: Test Lambda Functions

1. **Test Individual Functions**
   ```bash
   # Test feed parser
   aws lambda invoke \
     --function-name sentinel-prod-feed-parser \
     --payload '{
       "feedConfigs": [
         {
           "url": "https://feeds.feedburner.com/eset/blog",
           "source": "ESET"
         }
       ],
       "batchSize": 5
     }' \
     response.json
   
   cat response.json
   ```

2. **Test Step Functions Workflow**
   ```bash
   # Get state machine ARN
   STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
     --stack-name sentinel-prod-complete \
     --query 'Stacks[0].Outputs[?OutputKey==`IngestionStateMachineArn`].OutputValue' \
     --output text)
   
   # Start execution
   aws stepfunctions start-execution \
     --state-machine-arn $STATE_MACHINE_ARN \
     --name "test-execution-$(date +%s)" \
     --input '{
       "feedConfigs": [
         {
           "url": "https://feeds.feedburner.com/eset/blog",
           "source": "ESET"
         }
       ],
       "batchSize": 3
     }'
   ```

## Function-Specific Implementation Details

### 1. Feed Parser Function
- **Purpose**: Parse RSS feeds and extract cybersecurity articles
- **Key Features**:
  - Multi-feed processing
  - Content extraction and normalization
  - Basic relevance filtering
  - Error handling and retry logic

### 2. Relevancy Evaluator Function
- **Purpose**: AI-powered relevance assessment using Bedrock
- **Key Features**:
  - Claude model integration
  - Cybersecurity context understanding
  - Confidence scoring
  - Batch processing support

### 3. Dedup Tool Function
- **Purpose**: Semantic deduplication using embeddings
- **Key Features**:
  - Titan embedding model integration
  - Vector similarity comparison
  - OpenSearch integration (if enabled)
  - Clustering similar articles

### 4. Guardrail Tool Function
- **Purpose**: Content policy enforcement and safety checks
- **Key Features**:
  - Policy violation detection
  - Content classification
  - Automated triage decisions
  - Escalation triggers

### 5. Storage Tool Function
- **Purpose**: Article storage, retrieval, and state management
- **Key Features**:
  - DynamoDB operations
  - S3 content storage
  - State transitions
  - Batch result compilation

### 6. Human Escalation Function
- **Purpose**: Manage human review workflows
- **Key Features**:
  - SES email notifications
  - Review queue management
  - Escalation routing
  - Audit trail creation

### 7. Notifier Function
- **Purpose**: Send notifications for published articles and alerts
- **Key Features**:
  - Multi-channel notifications
  - Template-based messaging
  - Delivery tracking
  - Rate limiting

### 8. Analyst Assistant Function
- **Purpose**: AI chat interface for security analysts
- **Key Features**:
  - Conversational AI with Claude
  - Context-aware responses
  - Knowledge base integration
  - Session management

### 9. Query Knowledge Base Function
- **Purpose**: RAG-powered knowledge queries
- **Key Features**:
  - Bedrock Knowledge Base integration
  - Semantic search
  - Context retrieval
  - Answer generation

### 10. Commentary API Function
- **Purpose**: Manage article comments and annotations
- **Key Features**:
  - CRUD operations for comments
  - User attribution
  - Threaded discussions
  - Moderation support

### 11. Publish Decision Function
- **Purpose**: Process human review decisions
- **Key Features**:
  - Decision validation
  - State transitions
  - Audit logging
  - Workflow completion

## Monitoring and Troubleshooting

### CloudWatch Logs
```bash
# View function logs
aws logs tail /aws/lambda/sentinel-prod-feed-parser --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/sentinel-prod-feed-parser \
  --filter-pattern "ERROR"
```

### X-Ray Tracing
```bash
# Get trace summaries
aws xray get-trace-summaries \
  --time-range-type TimeRangeByStartTime \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z
```

### Performance Monitoring
- Monitor Lambda duration and memory usage
- Track error rates and throttling
- Set up CloudWatch alarms for critical metrics
- Use Step Functions execution history for workflow debugging

## Security Considerations

1. **IAM Permissions**: Functions use least-privilege access
2. **Encryption**: All data encrypted at rest and in transit
3. **VPC Configuration**: Optional VPC deployment for network isolation
4. **Secrets Management**: Use AWS Secrets Manager for sensitive data
5. **Input Validation**: Validate all inputs and sanitize content

## Cost Optimization

1. **Right-sizing**: Monitor memory usage and adjust allocation
2. **Provisioned Concurrency**: Use for predictable workloads
3. **Reserved Capacity**: Consider for DynamoDB if usage is consistent
4. **S3 Lifecycle**: Implement intelligent tiering for content storage
5. **Monitoring**: Set up cost alerts and budgets

This deployment guide provides comprehensive instructions for deploying Lambda functions with standalone agent implementations for the Sentinel cybersecurity platform.