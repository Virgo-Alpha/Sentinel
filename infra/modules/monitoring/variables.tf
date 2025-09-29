# Variables for Monitoring Module

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "lambda_function_names" {
  description = "Map of Lambda function names"
  type        = map(string)
}

variable "state_machine_arn" {
  description = "ARN of Step Functions state machine"
  type        = string
}

variable "articles_table_name" {
  description = "Name of articles DynamoDB table"
  type        = string
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

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "dlq_names" {
  description = "Map of DLQ names for monitoring"
  type        = map(string)
  default     = {}
}

variable "critical_alert_emails" {
  description = "Email addresses for critical alert notifications"
  type        = list(string)
  default     = []
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for notifications"
  type        = string
  default     = ""
  sensitive   = true
}

variable "keyword_analysis_lambda_arn" {
  description = "ARN of Lambda function for keyword analysis"
  type        = string
  default     = ""
}

variable "enable_ab_testing" {
  description = "Enable A/B testing metrics and dashboards"
  type        = bool
  default     = true
}

variable "cost_threshold_per_article" {
  description = "Cost threshold per article for alerting (in USD)"
  type        = number
  default     = 0.10
}

variable "relevancy_threshold" {
  description = "Minimum relevancy rate threshold (percentage)"
  type        = number
  default     = 60
}

variable "deduplication_threshold" {
  description = "Minimum deduplication rate threshold (percentage)"
  type        = number
  default     = 85
}

variable "processing_latency_threshold" {
  description = "Maximum processing latency threshold (milliseconds)"
  type        = number
  default     = 300000
}