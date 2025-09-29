# Variables for Lambda Module

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "execution_role_arn" {
  description = "ARN of Lambda execution role"
  type        = string
}

variable "memory_size" {
  description = "Memory size for Lambda functions (MB)"
  type        = number
  default     = 512
  
  validation {
    condition     = var.memory_size >= 128 && var.memory_size <= 10240
    error_message = "Memory size must be between 128 and 10240 MB."
  }
}

variable "timeout" {
  description = "Timeout for Lambda functions (seconds)"
  type        = number
  default     = 300
  
  validation {
    condition     = var.timeout >= 1 && var.timeout <= 900
    error_message = "Timeout must be between 1 and 900 seconds."
  }
}

variable "enable_xray_tracing" {
  description = "Enable X-Ray tracing"
  type        = bool
  default     = true
}

variable "vpc_config" {
  description = "VPC configuration for Lambda functions"
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  default = null
}

variable "environment_variables" {
  description = "Environment variables for Lambda functions"
  type        = map(string)
  default     = {}
}

variable "artifacts_bucket_name" {
  description = "Name of S3 bucket for Lambda artifacts"
  type        = string
}

variable "content_bucket_arn" {
  description = "ARN of content S3 bucket"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of KMS key for encryption"
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "reserved_concurrency" {
  description = "Reserved concurrency for Lambda functions"
  type        = number
  default     = null
}

variable "enable_api_gateway" {
  description = "Enable API Gateway permissions"
  type        = bool
  default     = false
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