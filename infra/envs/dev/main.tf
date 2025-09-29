# Development Environment Configuration for Sentinel

terraform {
  required_version = ">= 1.5"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }

  backend "s3" {
    # Backend configuration will be provided via backend config file
    # or environment variables during terraform init
  }
}

# Configure AWS Provider
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Environment = "dev"
      Project     = "sentinel"
      ManagedBy   = "terraform"
    }
  }
}

# Call the main Sentinel module
module "sentinel" {
  source = "../../"

  # Environment Configuration
  environment = "dev"
  aws_region  = var.aws_region

  # Feature Flags - Conservative for dev
  enable_agents              = false  # Start without agents
  enable_amplify            = true   # Enable web app for testing
  enable_opensearch         = false  # Disable for cost savings
  enable_semantic_dedup     = false  # Use heuristic only
  enable_llm_relevance      = true   # Keep LLM features
  enable_auto_publish       = false  # Require human review
  enable_email_notifications = true

  # Resource Configuration - Reduced for dev
  lambda_memory_size     = 256   # Smaller memory
  lambda_timeout         = 180   # Shorter timeout
  dynamodb_billing_mode  = "PAY_PER_REQUEST"

  # VPC Configuration
  create_vpc         = true
  vpc_cidr          = "10.1.0.0/16"
  availability_zones = ["${var.aws_region}a", "${var.aws_region}b"]

  # Processing Configuration - Lower limits
  max_concurrent_feeds     = 3
  max_articles_per_fetch   = 20
  content_retention_days   = 90  # Shorter retention

  # Thresholds - More permissive for testing
  relevance_threshold  = 0.6
  similarity_threshold = 0.8
  confidence_threshold = 0.7

  # Cost Controls - Strict limits for dev
  max_daily_llm_calls   = 1000
  max_monthly_cost_usd  = 200.0

  # Bedrock Configuration
  bedrock_model_id         = "anthropic.claude-3-haiku-20240307-v1:0"  # Cheaper model
  bedrock_embedding_model  = "amazon.titan-embed-text-v1"

  # Monitoring Configuration
  enable_xray_tracing        = true
  enable_detailed_monitoring = false  # Reduce costs
  log_retention_days         = 7      # Shorter retention

  # Notification Configuration
  ses_sender_email   = var.ses_sender_email
  escalation_emails  = var.escalation_emails
  digest_emails      = var.digest_emails
  alert_emails       = var.alert_emails

  # Amplify Configuration
  amplify_repository_url = var.amplify_repository_url
  amplify_callback_urls  = [
    "http://localhost:3000/callback",
    "https://dev.${var.domain_name}/callback"
  ]
  amplify_logout_urls = [
    "http://localhost:3000/logout",
    "https://dev.${var.domain_name}/logout"
  ]

  # Common Tags
  common_tags = {
    Environment = "dev"
    Project     = "sentinel"
    ManagedBy   = "terraform"
    Owner       = var.owner
    CostCenter  = var.cost_center
  }
}