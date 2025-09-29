# Production Environment Configuration for Sentinel

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
      Environment = "prod"
      Project     = "sentinel"
      ManagedBy   = "terraform"
    }
  }
}

# Call the main Sentinel module
module "sentinel" {
  source = "../../"

  # Environment Configuration
  environment = "prod"
  aws_region  = var.aws_region

  # Feature Flags - Full production features
  enable_agents              = var.enable_agents
  enable_amplify            = true
  enable_opensearch         = true   # Full search capabilities
  enable_semantic_dedup     = true   # Advanced deduplication
  enable_llm_relevance      = true
  enable_auto_publish       = var.enable_auto_publish
  enable_email_notifications = true

  # Resource Configuration - Production sizing
  lambda_memory_size     = 1024  # Higher memory for performance
  lambda_timeout         = 300   # Full timeout
  dynamodb_billing_mode  = var.dynamodb_billing_mode

  # VPC Configuration
  create_vpc         = true
  vpc_cidr          = "10.0.0.0/16"
  availability_zones = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]

  # Processing Configuration - Production scale
  max_concurrent_feeds     = var.max_concurrent_feeds
  max_articles_per_fetch   = 100
  content_retention_days   = 365  # Full year retention

  # Thresholds - Production quality
  relevance_threshold  = var.relevance_threshold
  similarity_threshold = var.similarity_threshold
  confidence_threshold = var.confidence_threshold

  # Cost Controls - Production limits
  max_daily_llm_calls   = var.max_daily_llm_calls
  max_monthly_cost_usd  = var.max_monthly_cost_usd

  # Bedrock Configuration - Production models
  bedrock_model_id         = var.bedrock_model_id
  bedrock_embedding_model  = "amazon.titan-embed-text-v1"

  # Monitoring Configuration - Full observability
  enable_xray_tracing        = true
  enable_detailed_monitoring = true
  log_retention_days         = var.log_retention_days

  # Notification Configuration
  ses_sender_email   = var.ses_sender_email
  escalation_emails  = var.escalation_emails
  digest_emails      = var.digest_emails
  alert_emails       = var.alert_emails

  # Amplify Configuration
  amplify_repository_url = var.amplify_repository_url
  amplify_callback_urls  = var.amplify_callback_urls
  amplify_logout_urls    = var.amplify_logout_urls

  # Common Tags
  common_tags = {
    Environment = "prod"
    Project     = "sentinel"
    ManagedBy   = "terraform"
    Owner       = var.owner
    CostCenter  = var.cost_center
    Compliance  = "required"
    Backup      = "required"
  }
}