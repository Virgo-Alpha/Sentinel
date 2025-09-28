# Production Environment Configuration

# Basic Configuration
aws_region   = "us-east-1"
environment  = "prod"
project_name = "sentinel"

# Feature Flags - Full production capabilities
enable_agents              = true   # Enable Bedrock AgentCore integration
enable_amplify            = true   # Enable web application
enable_opensearch         = true   # Enable vector search
enable_semantic_dedup     = true   # Enable semantic deduplication
enable_llm_relevance      = true   # Enable LLM relevance assessment
enable_auto_publish       = false  # Keep human review for safety
enable_email_notifications = true   # Enable notifications

# Resource Configuration - Production sizing
lambda_memory_size    = 1024  # MB - Higher memory for production
lambda_timeout        = 600   # seconds - Longer timeout for complex processing
dynamodb_billing_mode = "PAY_PER_REQUEST"

# Processing Configuration - Full capacity
max_concurrent_feeds    = 10   # Higher concurrency for production
max_articles_per_fetch  = 100  # More articles per fetch
content_retention_days  = 365  # Full year retention

# Thresholds - Production quality settings
relevance_threshold  = 0.7   # Standard threshold
similarity_threshold = 0.85  # High precision for duplicates
confidence_threshold = 0.8   # High confidence required

# Cost Controls - Production limits
max_daily_llm_calls  = 50000  # Higher limit for production
max_monthly_cost_usd = 2000.0 # Higher cost allowance

# Bedrock Models
bedrock_model_id        = "anthropic.claude-3-5-sonnet-20241022-v2:0"
bedrock_embedding_model = "amazon.titan-embed-text-v1"

# VPC Configuration
create_vpc         = true
vpc_cidr          = "10.1.0.0/16"  # Different CIDR for prod
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]  # More AZs

# Monitoring Configuration
enable_xray_tracing       = true
enable_detailed_monitoring = true
log_retention_days        = 90  # Longer retention for production

# Notification Configuration (update with your production email addresses)
ses_sender_email = "noreply@sentinel.company.com"
escalation_emails = [
  "security-lead@company.com",
  "senior-analyst@company.com"
]
digest_emails = [
  "security-team@company.com",
  "analysts@company.com",
  "management@company.com"
]
alert_emails = [
  "soc@company.com",
  "security-alerts@company.com",
  "on-call@company.com"
]

# Common Tags
common_tags = {
  Project     = "Sentinel"
  Environment = "prod"
  ManagedBy   = "Terraform"
  Owner       = "SecurityTeam"
  CostCenter  = "Security"
  Compliance  = "Required"
  Backup      = "Required"
}