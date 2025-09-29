# Variables for WAF Module

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "rate_limit" {
  description = "Rate limit for requests per 5-minute period"
  type        = number
  default     = 2000
}

variable "enable_geo_blocking" {
  description = "Enable geographic blocking"
  type        = bool
  default     = false
}

variable "allowed_countries" {
  description = "List of allowed country codes (ISO 3166-1 alpha-2)"
  type        = list(string)
  default     = ["US", "CA", "GB", "AU", "DE", "FR", "JP"]
}

variable "allowed_ips" {
  description = "List of allowed IP addresses/CIDR blocks"
  type        = list(string)
  default     = []
}

variable "blocked_ips" {
  description = "List of blocked IP addresses/CIDR blocks"
  type        = list(string)
  default     = []
}

variable "excluded_common_rules" {
  description = "List of common rules to exclude"
  type        = list(string)
  default     = []
}

variable "blocked_requests_threshold" {
  description = "Threshold for blocked requests alarm"
  type        = number
  default     = 100
}

variable "rate_limit_threshold" {
  description = "Threshold for rate limit alarm"
  type        = number
  default     = 50
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