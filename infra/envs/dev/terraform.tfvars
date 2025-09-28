# Development Environment Configuration

# Basic Configuration
aws_region   = "us-east-1"
environment  = "dev"
project_name = "sentinel"

# Feature Flags - Conservative settings for development
enable_agents              = false  # Start with direct Lambda orchestration
enable_amplify            = false  # Enable when web app is ready
enable_opensearch         = false  # Enable when vector search is needed
enable_semantic_dedup     = true   # Enable semantic deduplication
enable_llm_relevance      = true   # Enable LLM relevance assessment
enable_auto_publish       = false  # Require human review in dev
enable_email_notifications = true   # Enable notifications

# Resource Configuration - Smaller sizes for development
lambda_memory_size    = 512   # MB
lambda_timeout        = 300   # seconds
dynamodb_billing_mode = "PAY_PER_REQUEST"

# Processing Configuration - Lower limits for development
max_concurrent_feeds    = 3    # Reduced for dev environment
max_articles_per_fetch  = 25   # Reduced for dev environment
content_retention_days  = 90   # Shorter retention in dev

# Thresholds - More permissive for testing
relevance_threshold  = 0.6   # Lower threshold for more results
similarity_threshold = 0.8   # Lower threshold for more duplicates
confidence_threshold = 0.7   # Lower threshold for testing

# Cost Controls - Lower limits for development
max_daily_llm_calls  = 1000   # Reduced for dev
max_monthly_cost_usd = 100.0  # Lower cost limit

# Bedrock Models
bedrock_model_id        = "anthropic.claude-3-5-sonnet-20241022-v2:0"
bedrock_embedding_model = "amazon.titan-embed-text-v1"

# VPC Configuration
create_vpc         = true
vpc_cidr          = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b"]

# Monitoring Configuration
enable_xray_tracing       = true
enable_detailed_monitoring = true
log_retention_days        = 14  # Shorter retention for dev

# Notification Configuration (update with your email addresses)
ses_sender_email = "noreply@sentinel-dev.local"
escalation_emails = [
  "dev-team@company.com"
]
digest_emails = [
  "dev-team@company.com"
]
alert_emails = [
  "dev-alerts@company.com"
]

# Common Tags
common_tags = {
  Project     = "Sentinel"
  Environment = "dev"
  ManagedBy   = "Terraform"
  Owner       = "DevTeam"
  CostCenter  = "Engineering"
}