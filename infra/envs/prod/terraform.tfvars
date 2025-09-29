# =============================================================================
# SENTINEL PRODUCTION ENVIRONMENT CONFIGURATION
# =============================================================================
# This file contains environment-specific configuration for the production
# environment. Values are optimized for performance, reliability, and security.
# =============================================================================

# =============================================================================
# BASIC CONFIGURATION
# =============================================================================
aws_region   = "us-east-1"
environment  = "prod"
project_name = "sentinel"

# =============================================================================
# FEATURE FLAGS - FULL PRODUCTION CAPABILITIES
# =============================================================================
# All features enabled for production deployment
enable_agents              = true   # Enable Bedrock AgentCore integration
enable_amplify            = true   # Enable web application
enable_opensearch         = true   # Enable vector search capabilities
enable_semantic_dedup     = true   # Enable advanced semantic deduplication
enable_llm_relevance      = true   # Enable LLM-based relevance assessment
enable_auto_publish       = false  # Keep human review for safety (can be enabled later)
enable_email_notifications = true   # Enable all notification channels

# =============================================================================
# RESOURCE CONFIGURATION - PRODUCTION SIZING
# =============================================================================
# Optimized resource allocation for production workloads
lambda_memory_size    = 1024  # MB - Higher memory for better performance
lambda_timeout        = 600   # seconds - Full timeout for complex processing
dynamodb_billing_mode = "PAY_PER_REQUEST"  # Flexible billing for variable loads

# =============================================================================
# PROCESSING CONFIGURATION - FULL CAPACITY
# =============================================================================
# Production-scale processing limits
max_concurrent_feeds    = 10   # Process multiple feeds simultaneously
max_articles_per_fetch  = 100  # Fetch full batches for efficiency
content_retention_days  = 365  # Full year retention for compliance

# =============================================================================
# AI/ML THRESHOLDS - PRODUCTION QUALITY SETTINGS
# =============================================================================
# Tuned thresholds for high-quality production results
relevance_threshold  = 0.75  # Higher threshold for quality
similarity_threshold = 0.85  # High precision for duplicate detection
confidence_threshold = 0.8   # High confidence required for auto-actions

# =============================================================================
# COST CONTROLS - PRODUCTION LIMITS
# =============================================================================
# Production-appropriate cost controls with monitoring
max_daily_llm_calls  = 25000   # Reasonable limit with headroom
max_monthly_cost_usd = 1500.0  # Production budget with monitoring

# =============================================================================
# BEDROCK MODEL CONFIGURATION
# =============================================================================
# Production-grade models for optimal performance
bedrock_model_id        = "anthropic.claude-3-5-sonnet-20241022-v2:0"  # Latest model
bedrock_embedding_model = "amazon.titan-embed-text-v1"

# =============================================================================
# VPC CONFIGURATION
# =============================================================================
# Production VPC with high availability
create_vpc         = true
vpc_cidr          = "10.0.0.0/16"  # Production VPC CIDR
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]  # Multi-AZ for HA

# =============================================================================
# MONITORING CONFIGURATION
# =============================================================================
# Full observability for production environment
enable_xray_tracing       = true   # Complete request tracing
enable_detailed_monitoring = true   # Detailed CloudWatch metrics
log_retention_days        = 90     # Extended retention for compliance

# =============================================================================
# NOTIFICATION CONFIGURATION
# =============================================================================
# Production notification channels - UPDATE WITH YOUR ACTUAL EMAIL ADDRESSES
ses_sender_email = "noreply@sentinel.company.com"
escalation_emails = [
  "security-lead@company.com",
  "senior-analyst@company.com",
  "security-manager@company.com"
]
digest_emails = [
  "security-team@company.com",
  "analysts@company.com", 
  "management@company.com",
  "stakeholders@company.com"
]
alert_emails = [
  "soc@company.com",
  "security-alerts@company.com",
  "on-call@company.com",
  "incident-response@company.com"
]

# =============================================================================
# AMPLIFY CONFIGURATION
# =============================================================================
# Production web application settings
amplify_repository_url = ""  # Set this to your production Git repository URL
amplify_callback_urls = [
  "https://sentinel.company.com/callback",
  "https://app.sentinel.company.com/callback"
]
amplify_logout_urls = [
  "https://sentinel.company.com/logout",
  "https://app.sentinel.company.com/logout"
]

# =============================================================================
# RESOURCE TAGGING
# =============================================================================
# Comprehensive production tagging for governance and compliance
common_tags = {
  Project      = "Sentinel"
  Environment  = "prod"
  ManagedBy    = "Terraform"
  Owner        = "SecurityTeam"
  CostCenter   = "Security"
  Compliance   = "Required"
  Backup       = "Required"
  DataClass    = "Confidential"
  Monitoring   = "Required"
  Support      = "24x7"
}