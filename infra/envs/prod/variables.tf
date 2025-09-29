# =============================================================================
# PRODUCTION ENVIRONMENT VARIABLES
# =============================================================================
# Production-specific variable definitions with strict validation rules
# =============================================================================

# =============================================================================
# BASIC CONFIGURATION
# =============================================================================
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
  
  validation {
    condition = contains([
      "us-east-1", "us-east-2", "us-west-1", "us-west-2",
      "eu-west-1", "eu-west-2", "eu-central-1", "ap-southeast-1"
    ], var.aws_region)
    error_message = "AWS region must be a supported region for Bedrock services."
  }
}

variable "owner" {
  description = "Owner of the resources"
  type        = string
  default     = "security-team"
  
  validation {
    condition     = length(var.owner) > 0 && length(var.owner) <= 50
    error_message = "Owner must be between 1 and 50 characters."
  }
}

variable "cost_center" {
  description = "Cost center for billing"
  type        = string
  default     = "security-operations"
  
  validation {
    condition     = length(var.cost_center) > 0 && length(var.cost_center) <= 50
    error_message = "Cost center must be between 1 and 50 characters."
  }
}

# Feature Flags
variable "enable_agents" {
  description = "Enable Bedrock AgentCore integration"
  type        = bool
  default     = true
}

variable "enable_auto_publish" {
  description = "Enable automatic publishing without human review"
  type        = bool
  default     = false  # Conservative default for production
}

# Resource Configuration
variable "dynamodb_billing_mode" {
  description = "DynamoDB billing mode"
  type        = string
  default     = "PAY_PER_REQUEST"
  
  validation {
    condition     = contains(["PAY_PER_REQUEST", "PROVISIONED"], var.dynamodb_billing_mode)
    error_message = "DynamoDB billing mode must be PAY_PER_REQUEST or PROVISIONED."
  }
}

variable "max_concurrent_feeds" {
  description = "Maximum number of feeds to process concurrently"
  type        = number
  default     = 10
}

# Thresholds
variable "relevance_threshold" {
  description = "Minimum relevance score for article consideration"
  type        = number
  default     = 0.75
  
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
  default     = 50000
}

variable "max_monthly_cost_usd" {
  description = "Maximum monthly AWS costs (USD)"
  type        = number
  default     = 5000.0
}

# Bedrock Configuration
variable "bedrock_model_id" {
  description = "Bedrock model ID for LLM operations"
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v2:0"
}

# Monitoring Configuration
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 90
}

# =============================================================================
# NOTIFICATION CONFIGURATION
# =============================================================================
variable "ses_sender_email" {
  description = "SES sender email address"
  type        = string
  
  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.ses_sender_email))
    error_message = "SES sender email must be a valid email address."
  }
}

variable "escalation_emails" {
  description = "Email addresses for escalation notifications"
  type        = list(string)
  
  validation {
    condition     = length(var.escalation_emails) > 0 && length(var.escalation_emails) <= 10
    error_message = "Must specify between 1 and 10 escalation email addresses."
  }
}

variable "digest_emails" {
  description = "Email addresses for daily digest notifications"
  type        = list(string)
  
  validation {
    condition     = length(var.digest_emails) > 0 && length(var.digest_emails) <= 20
    error_message = "Must specify between 1 and 20 digest email addresses."
  }
}

variable "alert_emails" {
  description = "Email addresses for alert notifications"
  type        = list(string)
  
  validation {
    condition     = length(var.alert_emails) > 0 && length(var.alert_emails) <= 10
    error_message = "Must specify between 1 and 10 alert email addresses."
  }
}

# =============================================================================
# AMPLIFY CONFIGURATION
# =============================================================================
variable "amplify_repository_url" {
  description = "Git repository URL for Amplify app"
  type        = string
  
  validation {
    condition     = can(regex("^https://github\\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+(\\.git)?$", var.amplify_repository_url))
    error_message = "Amplify repository URL must be a valid GitHub HTTPS URL."
  }
}

variable "amplify_callback_urls" {
  description = "Callback URLs for Cognito authentication"
  type        = list(string)
  
  validation {
    condition = alltrue([
      for url in var.amplify_callback_urls : can(regex("^https://[a-zA-Z0-9.-]+/callback$", url))
    ])
    error_message = "All callback URLs must be HTTPS URLs ending with /callback."
  }
}

variable "amplify_logout_urls" {
  description = "Logout URLs for Cognito authentication"
  type        = list(string)
  
  validation {
    condition = alltrue([
      for url in var.amplify_logout_urls : can(regex("^https://[a-zA-Z0-9.-]+/logout$", url))
    ])
    error_message = "All logout URLs must be HTTPS URLs ending with /logout."
  }
}