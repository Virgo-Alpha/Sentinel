# Development Environment Configuration for Sentinel

# Environment settings
environment = "dev"
project_name = "sentinel"

# AWS Configuration
aws_region = "us-east-1"
availability_zones = ["us-east-1a", "us-east-1b"]

# Network Configuration
vpc_cidr = "10.0.0.0/16"
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
public_subnet_cidrs = ["10.0.101.0/24", "10.0.102.0/24"]

# Feature Flags
enable_agents = false          # Start with direct Lambda orchestration
enable_amplify = true          # Enable web application
enable_opensearch = true       # Enable semantic deduplication

# DynamoDB Configuration
dynamodb_billing_mode = "PAY_PER_REQUEST"  # Cost-effective for dev
dynamodb_point_in_time_recovery = false    # Disable for dev to save costs

# Lambda Configuration
lambda_memory_size = 256       # Smaller memory for dev
lambda_timeout = 300           # 5 minutes
lambda_reserved_concurrency = 10  # Limit concurrency for dev

# S3 Configuration
s3_versioning_enabled = false  # Disable versioning for dev
s3_lifecycle_enabled = true    # Enable lifecycle for cost management
s3_transition_days = 30        # Transition to IA after 30 days
s3_expiration_days = 90        # Delete after 90 days

# OpenSearch Serverless Configuration
opensearch_capacity_units = 2  # Minimum for dev

# EventBridge Configuration
eventbridge_schedule_enabled = true
feed_processing_schedule = "rate(30 minutes)"  # Process feeds every 30 minutes

# SQS Configuration
sqs_visibility_timeout = 300   # 5 minutes
sqs_message_retention = 1209600  # 14 days
sqs_max_receive_count = 3      # DLQ after 3 failures

# SNS Configuration
sns_email_notifications = ["dev-team@example.com"]

# Cognito Configuration
cognito_password_policy = {
  minimum_length = 8
  require_lowercase = true
  require_numbers = true
  require_symbols = false
  require_uppercase = true
}

# API Gateway Configuration
api_gateway_throttle_rate_limit = 1000
api_gateway_throttle_burst_limit = 2000

# CloudWatch Configuration
cloudwatch_log_retention_days = 7  # Short retention for dev
cloudwatch_detailed_monitoring = false

# X-Ray Configuration
xray_tracing_enabled = true
xray_sampling_rate = 0.1  # 10% sampling for dev

# Auto Scaling Configuration
auto_scaling_enabled = false  # Disable auto-scaling for dev

# Backup Configuration
backup_enabled = false  # Disable backups for dev

# Cost Optimization
cost_optimization_enabled = true
unused_resource_cleanup = true

# Security Configuration
encryption_at_rest = true
encryption_in_transit = true
enable_waf = false  # Disable WAF for dev to save costs

# Monitoring and Alerting
monitoring_enabled = true
alerting_enabled = false  # Disable alerting for dev

# Tags
common_tags = {
  Environment = "dev"
  Project = "sentinel"
  Owner = "dev-team"
  CostCenter = "engineering"
  ManagedBy = "terraform"
  Purpose = "cybersecurity-triage"
}

# RSS Feed Configuration
rss_feeds = [
  {
    name = "CISA"
    url = "https://www.cisa.gov/cybersecurity-advisories/rss.xml"
    category = "advisories"
    enabled = true
    fetch_interval = 1800  # 30 minutes
  },
  {
    name = "NCSC"
    url = "https://www.ncsc.gov.uk/api/1/services/v1/all-rss-feed.xml"
    category = "advisories"
    enabled = true
    fetch_interval = 1800
  },
  {
    name = "Microsoft Security"
    url = "https://msrc.microsoft.com/blog/feed"
    category = "updates"
    enabled = true
    fetch_interval = 3600  # 1 hour
  }
]

# Keyword Configuration
target_keywords = {
  cloud_platforms = [
    "AWS", "Amazon Web Services", "Azure", "Microsoft 365", "Office 365",
    "Google Cloud", "GCP", "Google Workspace"
  ]
  security_vendors = [
    "Fortinet", "SentinelOne", "CrowdStrike", "Palo Alto", "Cisco",
    "Symantec", "McAfee", "Trend Micro", "Check Point"
  ]
  threat_intel = [
    "vulnerability", "CVE", "exploit", "malware", "ransomware",
    "phishing", "zero-day", "threat actor", "APT"
  ]
  enterprise_tools = [
    "Active Directory", "Exchange", "SharePoint", "Teams", "Outlook",
    "VMware", "Citrix", "Oracle", "SAP"
  ]
}

# Performance Configuration
performance_config = {
  max_processing_time_minutes = 5
  deduplication_threshold = 0.85
  relevancy_threshold = 0.6
  batch_size = 25
  max_concurrent_executions = 10
}

# Development-specific settings
dev_settings = {
  debug_logging = true
  mock_external_apis = false
  skip_email_notifications = true
  enable_test_endpoints = true
  cors_allow_all_origins = true
}