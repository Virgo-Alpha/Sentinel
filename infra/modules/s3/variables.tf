# Variables for S3 Module

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "resource_suffix" {
  description = "Unique suffix for resource names"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of KMS key for encryption"
  type        = string
}

variable "retention_days" {
  description = "Number of days to retain content"
  type        = number
  default     = 365
  
  validation {
    condition     = var.retention_days >= 30 && var.retention_days <= 2555
    error_message = "Retention days must be between 30 and 2555 (7 years)."
  }
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}