"""
Pytest configuration and fixtures for integration tests.
"""

import os
import json
import boto3
import pytest
from moto import mock_dynamodb, mock_s3, mock_sqs, mock_lambda, mock_stepfunctions
from typing import Dict, Any, Generator
import uuid
from datetime import datetime, timezone

# Test configuration
TEST_CONFIG = {
    "aws_region": "us-east-1",
    "name_prefix": "sentinel-test",
    "dynamodb_tables": {
        "articles": "sentinel-test-articles",
        "comments": "sentinel-test-comments",
        "memory": "sentinel-test-memory"
    },
    "s3_buckets": {
        "artifacts": "sentinel-test-artifacts",
        "raw_content": "sentinel-test-raw-content",
        "normalized_content": "sentinel-test-normalized-content"
    },
    "sqs_queues": {
        "ingestion": "sentinel-test-ingestion-queue",
        "dlq": "sentinel-test-dlq"
    }
}

@pytest.fixture(scope="session")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = TEST_CONFIG["aws_region"]

@pytest.fixture(scope="function")
def mock_aws_services(aws_credentials):
    """Mock all AWS services used in integration tests."""
    with mock_dynamodb(), mock_s3(), mock_sqs(), mock_lambda(), mock_stepfunctions():
        yield

@pytest.fixture
def dynamodb_client(mock_aws_services):
    """DynamoDB client for testing."""
    return boto3.client("dynamodb", region_name=TEST_CONFIG["aws_region"])

@pytest.fixture
def dynamodb_resource(mock_aws_services):
    """DynamoDB resource for testing."""
    return boto3.resource("dynamodb", region_name=TEST_CONFIG["aws_region"])

@pytest.fixture
def s3_client(mock_aws_services):
    """S3 client for testing."""
    return boto3.client("s3", region_name=TEST_CONFIG["aws_region"])

@pytest.fixture
def sqs_client(mock_aws_services):
    """SQS client for testing."""
    return boto3.client("sqs", region_name=TEST_CONFIG["aws_region"])

@pytest.fixture
def lambda_client(mock_aws_services):
    """Lambda client for testing."""
    return boto3.client("lambda", region_name=TEST_CONFIG["aws_region"])

@pytest.fixture
def stepfunctions_client(mock_aws_services):
    """Step Functions client for testing."""
    return boto3.client("stepfunctions", region_name=TEST_CONFIG["aws_region"])

@pytest.fixture
def setup_dynamodb_tables(dynamodb_client, dynamodb_resource):
    """Set up DynamoDB tables for testing."""
    tables = {}
    
    # Articles table
    articles_table = dynamodb_resource.create_table(
        TableName=TEST_CONFIG["dynamodb_tables"]["articles"],
        KeySchema=[
            {"AttributeName": "article_id", "KeyType": "HASH"}
        ],
        AttributeDefinitions=[
            {"AttributeName": "article_id", "AttributeType": "S"},
            {"AttributeName": "state", "AttributeType": "S"},
            {"AttributeName": "published_at", "AttributeType": "S"},
            {"AttributeName": "cluster_id", "AttributeType": "S"}
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "state-published_at-index",
                "KeySchema": [
                    {"AttributeName": "state", "KeyType": "HASH"},
                    {"AttributeName": "published_at", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"},
                "BillingMode": "PAY_PER_REQUEST"
            },
            {
                "IndexName": "cluster-published_at-index",
                "KeySchema": [
                    {"AttributeName": "cluster_id", "KeyType": "HASH"},
                    {"AttributeName": "published_at", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"},
                "BillingMode": "PAY_PER_REQUEST"
            }
        ],
        BillingMode="PAY_PER_REQUEST"
    )
    tables["articles"] = articles_table
    
    # Comments table
    comments_table = dynamodb_resource.create_table(
        TableName=TEST_CONFIG["dynamodb_tables"]["comments"],
        KeySchema=[
            {"AttributeName": "comment_id", "KeyType": "HASH"}
        ],
        AttributeDefinitions=[
            {"AttributeName": "comment_id", "AttributeType": "S"},
            {"AttributeName": "article_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"}
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "article-created_at-index",
                "KeySchema": [
                    {"AttributeName": "article_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"},
                "BillingMode": "PAY_PER_REQUEST"
            }
        ],
        BillingMode="PAY_PER_REQUEST"
    )
    tables["comments"] = comments_table
    
    # Memory table
    memory_table = dynamodb_resource.create_table(
        TableName=TEST_CONFIG["dynamodb_tables"]["memory"],
        KeySchema=[
            {"AttributeName": "memory_id", "KeyType": "HASH"}
        ],
        AttributeDefinitions=[
            {"AttributeName": "memory_id", "AttributeType": "S"},
            {"AttributeName": "memory_type", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"}
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "type-created_at-index",
                "KeySchema": [
                    {"AttributeName": "memory_type", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"},
                "BillingMode": "PAY_PER_REQUEST"
            }
        ],
        BillingMode="PAY_PER_REQUEST"
    )
    tables["memory"] = memory_table
    
    return tables

@pytest.fixture
def setup_s3_buckets(s3_client):
    """Set up S3 buckets for testing."""
    buckets = {}
    
    for bucket_name, bucket_key in TEST_CONFIG["s3_buckets"].items():
        s3_client.create_bucket(Bucket=bucket_key)
        buckets[bucket_name] = bucket_key
    
    return buckets

@pytest.fixture
def setup_sqs_queues(sqs_client):
    """Set up SQS queues for testing."""
    queues = {}
    
    for queue_name, queue_key in TEST_CONFIG["sqs_queues"].items():
        response = sqs_client.create_queue(QueueName=queue_key)
        queues[queue_name] = response["QueueUrl"]
    
    return queues

@pytest.fixture
def sample_rss_feed_data():
    """Sample RSS feed data for testing."""
    return {
        "feed_url": "https://example.com/feed.xml",
        "feed_content": """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test Security Feed</title>
                <description>Test cybersecurity news feed</description>
                <item>
                    <title>Critical AWS Vulnerability Discovered</title>
                    <description>A critical vulnerability has been found in AWS Lambda affecting multiple services.</description>
                    <link>https://example.com/aws-vulnerability</link>
                    <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
                    <guid>aws-vuln-001</guid>
                </item>
                <item>
                    <title>Microsoft 365 Security Update</title>
                    <description>Microsoft releases security patches for Office 365 and Azure services.</description>
                    <link>https://example.com/microsoft-update</link>
                    <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
                    <guid>ms-update-001</guid>
                </item>
            </channel>
        </rss>"""
    }

@pytest.fixture
def sample_article_data():
    """Sample article data for testing."""
    return {
        "article_id": str(uuid.uuid4()),
        "source": "Test Security Feed",
        "feed_id": "test-feed",
        "url": "https://example.com/test-article",
        "canonical_url": "https://example.com/test-article",
        "title": "Test Cybersecurity Article",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "state": "INGESTED",
        "is_duplicate": False,
        "relevancy_score": 0.85,
        "keyword_matches": [
            {
                "keyword": "AWS",
                "hit_count": 3,
                "contexts": ["AWS Lambda vulnerability", "AWS security", "AWS services"]
            }
        ],
        "triage_action": "REVIEW",
        "summary_short": "Test article about cybersecurity",
        "entities": {
            "cves": ["CVE-2024-0001"],
            "threat_actors": [],
            "malware": [],
            "vendors": ["AWS"],
            "products": ["Lambda"],
            "sectors": ["Technology"],
            "countries": ["US"]
        },
        "tags": ["vulnerability", "aws", "lambda"],
        "confidence": 0.9,
        "guardrail_flags": [],
        "created_by_agent_version": "1.0.0"
    }

@pytest.fixture
def sample_keyword_config():
    """Sample keyword configuration for testing."""
    return {
        "cloud_platforms": ["AWS", "Azure", "Google Cloud", "Microsoft 365"],
        "security_vendors": ["Fortinet", "SentinelOne", "CrowdStrike", "Mimecast"],
        "enterprise_tools": ["Jamf Pro", "Tenable", "CyberArk", "Checkpoint"],
        "threat_intel": ["CVE", "vulnerability", "malware", "ransomware"]
    }

@pytest.fixture
def sample_feed_config():
    """Sample feed configuration for testing."""
    return [
        {
            "name": "Test CISA Feed",
            "url": "https://example.com/cisa-feed.xml",
            "category": "Advisories",
            "enabled": True,
            "fetch_interval": "1h"
        },
        {
            "name": "Test Microsoft Feed",
            "url": "https://example.com/microsoft-feed.xml",
            "category": "Vendor",
            "enabled": True,
            "fetch_interval": "2h"
        }
    ]

@pytest.fixture
def correlation_id():
    """Generate a correlation ID for testing."""
    return f"test-{uuid.uuid4()}"

@pytest.fixture
def lambda_context():
    """Mock Lambda context for testing."""
    class MockLambdaContext:
        def __init__(self):
            self.function_name = "test-function"
            self.function_version = "$LATEST"
            self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
            self.memory_limit_in_mb = 512
            self.remaining_time_in_millis = lambda: 30000
            self.aws_request_id = str(uuid.uuid4())
            self.log_group_name = "/aws/lambda/test-function"
            self.log_stream_name = "2024/01/01/[$LATEST]test-stream"
    
    return MockLambdaContext()

@pytest.fixture
def test_environment_variables():
    """Set up test environment variables."""
    env_vars = {
        "ARTICLES_TABLE_NAME": TEST_CONFIG["dynamodb_tables"]["articles"],
        "COMMENTS_TABLE_NAME": TEST_CONFIG["dynamodb_tables"]["comments"],
        "MEMORY_TABLE_NAME": TEST_CONFIG["dynamodb_tables"]["memory"],
        "ARTIFACTS_BUCKET": TEST_CONFIG["s3_buckets"]["artifacts"],
        "RAW_CONTENT_BUCKET": TEST_CONFIG["s3_buckets"]["raw_content"],
        "NORMALIZED_CONTENT_BUCKET": TEST_CONFIG["s3_buckets"]["normalized_content"],
        "INGESTION_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789012/sentinel-test-ingestion-queue",
        "DLQ_URL": "https://sqs.us-east-1.amazonaws.com/123456789012/sentinel-test-dlq",
        "AWS_REGION": TEST_CONFIG["aws_region"],
        "LOG_LEVEL": "DEBUG"
    }
    
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
    
    yield env_vars
    
    # Clean up environment variables
    for key in env_vars.keys():
        os.environ.pop(key, None)

@pytest.fixture
def integration_test_setup(
    setup_dynamodb_tables,
    setup_s3_buckets,
    setup_sqs_queues,
    test_environment_variables
):
    """Complete integration test setup with all AWS resources."""
    return {
        "dynamodb_tables": setup_dynamodb_tables,
        "s3_buckets": setup_s3_buckets,
        "sqs_queues": setup_sqs_queues,
        "environment": test_environment_variables
    }