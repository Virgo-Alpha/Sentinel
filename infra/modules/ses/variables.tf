# Variables for SES Module

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "sender_email" {
  description = "SES sender email address"
  type        = string
}

variable "domain" {
  description = "Domain for SES (optional)"
  type        = string
  default     = null
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

variable "kms_key_arn" {
  description = "ARN of KMS key for encryption"
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "bounce_rate_threshold" {
  description = "Threshold for bounce rate alarms (percentage)"
  type        = number
  default     = 5.0
}

variable "complaint_rate_threshold" {
  description = "Threshold for complaint rate alarms (percentage)"
  type        = number
  default     = 0.1
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