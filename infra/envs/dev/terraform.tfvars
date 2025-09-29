# =============================================================================
# SENTINEL DEVELOPMENT ENVIRONMENT CONFIGURATION
# =============================================================================
# This file contains environment-specific configuration for the development
# environment. Values are optimized for cost savings and testing flexibility.
# =============================================================================

# =============================================================================
# BASIC CONFIGURATION
# =============================================================================
aws_region   = "us-east-1"
environment  = "dev"
project_name = "sentinel"

# =============================================================================
# FEATURE FLAGS - CONSERVATIVE SETTINGS FOR DEVELOPMENT
# =============================================================================
# Start with minimal features enabled to reduce costs and complexity
enable_agents              = false  # Start with direct Lambda orchestration
enable_amplify            = false  # Enable when web app is ready for testing
enable_opensearch         = false  # Disable vector search to save costs
enable_semantic_dedup     = false  # Use heuristic dedup only in dev
enable_llm_relevance      = true   # Keep LLM features for testing
enable_auto_publish       = false  # Always require human review in dev
enable_email_notifications = true   # Enable notifications for testing

# =============================================================================
# RESOURCE CONFIGURATION - REDUCED SIZES FOR DEVELOPMENT
# =============================================================================
# Smaller resource allocations to minimize costs while maintaining functionality
lambda_memory_size    = 256   # MB - Minimal memory for cost savings
lambda_timeout        = 180   # seconds - Shorter timeout for faster feedback
dynamodb_billing_mode = "PAY_PER_REQUEST"  # Pay-per-use for variable dev workloads

# =============================================================================
# PROCESSING CONFIGURATION - LOWER LIMITS FOR DEVELOPMENT
# =============================================================================
# Reduced processing limits to prevent runaway costs during development
max_concurrent_feeds    = 2    # Process fewer feeds simultaneously
max_articles_per_fetch  = 10   # Fetch fewer articles per run
content_retention_days  = 30   # Shorter retention to save storage costs

# =============================================================================
# AI/ML THRESHOLDS - MORE PERMISSIVE FOR TESTING
# =============================================================================
# Lower thresholds to generate more test data and edge cases
relevance_threshold  = 0.5   # Lower threshold to capture more articles
similarity_threshold = 0.75  # Lower threshold to test dedup logic
confidence_threshold = 0.6   # Lower threshold to test review workflows

# =============================================================================
# COST CONTROLS - STRICT LIMITS FOR DEVELOPMENT
# =============================================================================
# Aggressive cost controls to prevent unexpected charges
max_daily_llm_calls  = 500    # Strict limit for development testing
max_monthly_cost_usd = 50.0   # Very low cost limit for dev environment

# =============================================================================
# BEDROCK MODEL CONFIGURATION
# =============================================================================
# Use cost-effective models for development
bedrock_model_id        = "anthropic.claude-3-haiku-20240307-v1:0"  # Cheaper model
bedrock_embedding_model = "amazon.titan-embed-text-v1"

# =============================================================================
# VPC CONFIGURATION
# =============================================================================
# Separate VPC CIDR from production to avoid conflicts
create_vpc         = true
vpc_cidr          = "10.1.0.0/16"  # Different from prod (10.0.0.0/16)
availability_zones = ["us-east-1a", "us-east-1b"]  # Minimal AZ coverage

# =============================================================================
# MONITORING CONFIGURATION
# =============================================================================
# Reduced monitoring to save costs while maintaining observability
enable_xray_tracing       = true   # Keep tracing for debugging
enable_detailed_monitoring = false  # Disable detailed monitoring for cost savings
log_retention_days        = 7      # Minimal log retention

# =============================================================================
# NOTIFICATION CONFIGURATION
# =============================================================================
# Update these email addresses with your actual development team emails
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

# =============================================================================
# AMPLIFY CONFIGURATION
# =============================================================================
# Development-specific Amplify settings
amplify_repository_url = ""  # Set this to your Git repository URL
amplify_callback_urls = [
  "http://localhost:3000/callback",
  "https://dev-sentinel.company.com/callback"
]
amplify_logout_urls = [
  "http://localhost:3000/logout", 
  "https://dev-sentinel.company.com/logout"
]

# =============================================================================
# RESOURCE TAGGING
# =============================================================================
# Comprehensive tagging for cost tracking and resource management
common_tags = {
  Project      = "Sentinel"
  Environment  = "dev"
  ManagedBy    = "Terraform"
  Owner        = "DevTeam"
  CostCenter   = "Engineering"
  Purpose      = "Development"
  AutoShutdown = "true"  # Flag for automated cost controls
}