# Terraform Variables for Sentinel Infrastructure

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "sentinel"
}

# Feature Flags for Gradual Rollout
variable "enable_agents" {
  description = "Enable Bedrock AgentCore integration"
  type        = bool
  default     = false
}

variable "enable_amplify" {
  description = "Enable Amplify web application"
  type        = bool
  default     = false
}

variable "enable_opensearch" {
  description = "Enable OpenSearch Serverless for vector search"
  type        = bool
  default     = false
}

variable "enable_semantic_dedup" {
  description = "Enable semantic deduplication with embeddings"
  type        = bool
  default     = true
}

variable "enable_llm_relevance" {
  description = "Enable LLM-based relevance assessment"
  type        = bool
  default     = true
}

variable "enable_auto_publish" {
  description = "Enable automatic publishing without human review"
  type        = bool
  default     = false
}

variable "enable_email_notifications" {
  description = "Enable email notifications via SES"
  type        = bool
  default     = true
}

# Resource Configuration
variable "lambda_memory_size" {
  description = "Memory size for Lambda functions (MB)"
  type        = number
  default     = 512
  
  validation {
    condition     = var.lambda_memory_size >= 128 && var.lambda_memory_size <= 10240
    error_message = "Lambda memory size must be between 128 and 10240 MB."
  }
}

variable "lambda_timeout" {
  description = "Timeout for Lambda functions (seconds)"
  type        = number
  default     = 300
  
  validation {
    condition     = var.lambda_timeout >= 1 && var.lambda_timeout <= 900
    error_message = "Lambda timeout must be between 1 and 900 seconds."
  }
}

variable "dynamodb_billing_mode" {
  description = "DynamoDB billing mode"
  type        = string
  default     = "PAY_PER_REQUEST"
  
  validation {
    condition     = contains(["PAY_PER_REQUEST", "PROVISIONED"], var.dynamodb_billing_mode)
    error_message = "DynamoDB billing mode must be PAY_PER_REQUEST or PROVISIONED."
  }
}

# Notification Configuration
variable "ses_sender_email" {
  description = "SES sender email address"
  type        = string
  default     = "noreply@sentinel.local"
  
  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.ses_sender_email))
    error_message = "SES sender email must be a valid email address."
  }
}

variable "escalation_emails" {
  description = "Email addresses for escalation notifications"
  type        = list(string)
  default     = []
}

variable "digest_emails" {
  description = "Email addresses for daily digest notifications"
  type        = list(string)
  default     = []
}

variable "alert_emails" {
  description = "Email addresses for alert notifications"
  type        = list(string)
  default     = []
}

# Processing Configuration
variable "max_concurrent_feeds" {
  description = "Maximum number of feeds to process concurrently"
  type        = number
  default     = 5
  
  validation {
    condition     = var.max_concurrent_feeds >= 1 && var.max_concurrent_feeds <= 50
    error_message = "Concurrent feeds must be between 1 and 50."
  }
}

variable "max_articles_per_fetch" {
  description = "Maximum articles to fetch per feed"
  type        = number
  default     = 50
  
  validation {
    condition     = var.max_articles_per_fetch >= 5 && var.max_articles_per_fetch <= 500
    error_message = "Articles per fetch must be between 5 and 500."
  }
}

variable "content_retention_days" {
  description = "Number of days to retain content in S3"
  type        = number
  default     = 365
  
  validation {
    condition     = var.content_retention_days >= 30 && var.content_retention_days <= 2555
    error_message = "Content retention must be between 30 and 2555 days (7 years)."
  }
}

# Thresholds
variable "relevance_threshold" {
  description = "Minimum relevance score for article consideration"
  type        = number
  default     = 0.7
  
  validation {
    condition     = var.relevance_threshold >= 0.0 && var.relevance_threshold <= 1.0
    error_message = "Relevance threshold must be between 0.0 and 1.0."
  }
}

variable "similarity_threshold" {
  description = "Minimum similarity score for duplicate detection"
  type        = number
  default     = 0.85
  
  validation {
    condition     = var.similarity_threshold >= 0.0 && var.similarity_threshold <= 1.0
    error_message = "Similarity threshold must be between 0.0 and 1.0."
  }
}

variable "confidence_threshold" {
  description = "Minimum confidence score for auto-actions"
  type        = number
  default     = 0.8
  
  validation {
    condition     = var.confidence_threshold >= 0.0 && var.confidence_threshold <= 1.0
    error_message = "Confidence threshold must be between 0.0 and 1.0."
  }
}

# Cost Controls
variable "max_daily_llm_calls" {
  description = "Maximum LLM API calls per day"
  type        = number
  default     = 10000
  
  validation {
    condition     = var.max_daily_llm_calls >= 100 && var.max_daily_llm_calls <= 100000
    error_message = "Daily LLM calls must be between 100 and 100,000."
  }
}

variable "max_monthly_cost_usd" {
  description = "Maximum monthly AWS costs (USD)"
  type        = number
  default     = 1000.0
  
  validation {
    condition     = var.max_monthly_cost_usd >= 50.0 && var.max_monthly_cost_usd <= 50000.0
    error_message = "Monthly cost limit must be between $50 and $50,000."
  }
}

# Bedrock Configuration
variable "bedrock_model_id" {
  description = "Bedrock model ID for LLM operations"
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v2:0"
}

variable "bedrock_embedding_model" {
  description = "Bedrock model ID for embeddings"
  type        = string
  default     = "amazon.titan-embed-text-v1"
}

# VPC Configuration
variable "create_vpc" {
  description = "Create a new VPC for the deployment"
  type        = bool
  default     = true
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
  
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid IPv4 CIDR block."
  }
}

variable "availability_zones" {
  description = "Availability zones for subnet deployment"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
  
  validation {
    condition     = length(var.availability_zones) >= 2 && length(var.availability_zones) <= 6
    error_message = "Must specify between 2 and 6 availability zones."
  }
}

# Monitoring Configuration
variable "enable_xray_tracing" {
  description = "Enable X-Ray tracing for Lambda functions"
  type        = bool
  default     = true
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
  
  validation {
    condition = contains([
      1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653
    ], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}

# Amplify Configuration
variable "amplify_repository_url" {
  description = "Git repository URL for Amplify app"
  type        = string
  default     = ""
}

variable "amplify_callback_urls" {
  description = "Callback URLs for Cognito authentication"
  type        = list(string)
  default     = ["http://localhost:3000/callback"]
}

variable "amplify_logout_urls" {
  description = "Logout URLs for Cognito authentication"
  type        = list(string)
  default     = ["http://localhost:3000/logout"]
}

# Tags
variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "Sentinel"
    ManagedBy   = "Terraform"
    Environment = "dev"
  }
}