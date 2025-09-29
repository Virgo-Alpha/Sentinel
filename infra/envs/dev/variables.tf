# =============================================================================
# DEVELOPMENT ENVIRONMENT VARIABLES
# =============================================================================
# Environment-specific variable definitions with validation rules
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

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "sentinel-dev.local"
  
  validation {
    condition     = can(regex("^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\\.[a-zA-Z]{2,}$", var.domain_name))
    error_message = "Domain name must be a valid DNS domain."
  }
}

variable "owner" {
  description = "Owner of the resources"
  type        = string
  default     = "dev-team"
  
  validation {
    condition     = length(var.owner) > 0 && length(var.owner) <= 50
    error_message = "Owner must be between 1 and 50 characters."
  }
}

variable "cost_center" {
  description = "Cost center for billing"
  type        = string
  default     = "development"
  
  validation {
    condition     = length(var.cost_center) > 0 && length(var.cost_center) <= 50
    error_message = "Cost center must be between 1 and 50 characters."
  }
}

# =============================================================================
# NOTIFICATION CONFIGURATION
# =============================================================================
variable "ses_sender_email" {
  description = "SES sender email address"
  type        = string
  default     = "noreply@sentinel-dev.local"
  
  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.ses_sender_email))
    error_message = "SES sender email must be a valid email address."
  }
}

variable "escalation_emails" {
  description = "Email addresses for escalation notifications"
  type        = list(string)
  default     = ["dev-team@company.com"]
  
  validation {
    condition     = length(var.escalation_emails) > 0 && length(var.escalation_emails) <= 10
    error_message = "Must specify between 1 and 10 escalation email addresses."
  }
}

variable "digest_emails" {
  description = "Email addresses for daily digest notifications"
  type        = list(string)
  default     = ["dev-team@company.com"]
  
  validation {
    condition     = length(var.digest_emails) > 0 && length(var.digest_emails) <= 20
    error_message = "Must specify between 1 and 20 digest email addresses."
  }
}

variable "alert_emails" {
  description = "Email addresses for alert notifications"
  type        = list(string)
  default     = ["dev-alerts@company.com"]
  
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
  default     = ""
  
  validation {
    condition = var.amplify_repository_url == "" || can(regex("^https://github\\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+(\\.git)?$", var.amplify_repository_url))
    error_message = "Amplify repository URL must be empty or a valid GitHub HTTPS URL."
  }
}

variable "amplify_callback_urls" {
  description = "Callback URLs for Cognito authentication"
  type        = list(string)
  default     = ["http://localhost:3000/callback"]
  
  validation {
    condition     = length(var.amplify_callback_urls) > 0 && length(var.amplify_callback_urls) <= 5
    error_message = "Must specify between 1 and 5 callback URLs."
  }
}

variable "amplify_logout_urls" {
  description = "Logout URLs for Cognito authentication"
  type        = list(string)
  default     = ["http://localhost:3000/logout"]
  
  validation {
    condition     = length(var.amplify_logout_urls) > 0 && length(var.amplify_logout_urls) <= 5
    error_message = "Must specify between 1 and 5 logout URLs."
  }
}