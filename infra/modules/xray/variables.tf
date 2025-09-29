# Variables for X-Ray Distributed Tracing Module

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "alerts_topic_arn" {
  description = "ARN of SNS topic for alerts"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of KMS key for encryption"
  type        = string
}

variable "enable_xray_insights_notifications" {
  description = "Enable X-Ray Insights notifications"
  type        = bool
  default     = true
}

variable "xray_layer_zip_path" {
  description = "Path to X-Ray layer ZIP file"
  type        = string
  default     = ""
}

variable "xray_layer_source_hash" {
  description = "Source hash for X-Ray layer"
  type        = string
  default     = ""
}

variable "lambda_function_arns" {
  description = "Map of Lambda function ARNs for tracing configuration"
  type        = map(string)
  default     = {}
}

variable "enable_detailed_tracing" {
  description = "Enable detailed X-Ray tracing"
  type        = bool
  default     = true
}

variable "correlation_id_header" {
  description = "Header name for correlation ID"
  type        = string
  default     = "X-Correlation-ID"
}

variable "trace_retention_days" {
  description = "X-Ray trace retention in days"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}