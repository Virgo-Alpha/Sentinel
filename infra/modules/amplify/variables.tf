# Variables for Amplify Module

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "repository_url" {
  description = "Git repository URL for the Amplify app"
  type        = string
  default     = ""
}

variable "user_pool_id" {
  description = "Cognito User Pool ID"
  type        = string
}

variable "user_pool_client_id" {
  description = "Cognito User Pool Client ID"
  type        = string
}

variable "identity_pool_id" {
  description = "Cognito Identity Pool ID"
  type        = string
}

variable "api_gateway_url" {
  description = "API Gateway URL"
  type        = string
}

variable "build_spec" {
  description = "Custom build specification (optional)"
  type        = string
  default     = null
}

variable "environment_variables" {
  description = "Additional environment variables"
  type        = map(string)
  default     = {}
}

variable "app_root_path" {
  description = "Root path for monorepo apps"
  type        = string
  default     = ""
}

variable "main_branch_name" {
  description = "Name of the main branch"
  type        = string
  default     = "main"
}

variable "dev_branch_name" {
  description = "Name of the development branch"
  type        = string
  default     = "develop"
}

variable "create_dev_branch" {
  description = "Create development branch"
  type        = bool
  default     = true
}

variable "enable_auto_branch_creation" {
  description = "Enable automatic branch creation"
  type        = bool
  default     = false
}

variable "auto_branch_creation_patterns" {
  description = "Patterns for automatic branch creation"
  type        = list(string)
  default     = ["feature/*", "hotfix/*"]
}

variable "enable_performance_mode" {
  description = "Enable performance mode for main branch"
  type        = bool
  default     = true
}

variable "enable_dev_basic_auth" {
  description = "Enable basic auth for development branch"
  type        = bool
  default     = true
}

variable "dev_basic_auth_username" {
  description = "Basic auth username for development branch"
  type        = string
  default     = "admin"
}

variable "dev_basic_auth_password" {
  description = "Basic auth password for development branch"
  type        = string
  default     = "changeme123!"
  sensitive   = true
}

variable "custom_domain" {
  description = "Custom domain for the Amplify app"
  type        = string
  default     = null
}

variable "main_subdomain_prefix" {
  description = "Subdomain prefix for main branch"
  type        = string
  default     = ""
}

variable "dev_subdomain_prefix" {
  description = "Subdomain prefix for development branch"
  type        = string
  default     = "dev"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "kms_key_arn" {
  description = "ARN of KMS key for encryption"
  type        = string
}

variable "alarm_topic_arn" {
  description = "SNS topic ARN for alarms"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}