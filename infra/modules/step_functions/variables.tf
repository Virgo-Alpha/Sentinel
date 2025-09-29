# Variables for Step Functions Module

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "execution_role_arn" {
  description = "ARN of Step Functions execution role"
  type        = string
}

variable "lambda_function_arns" {
  description = "Map of Lambda function ARNs"
  type        = map(string)
}

variable "enable_agents" {
  description = "Enable Bedrock Agent integration"
  type        = bool
  default     = false
}

variable "ingestor_agent_id" {
  description = "Bedrock Ingestor Agent ID"
  type        = string
  default     = ""
}

variable "max_concurrent_executions" {
  description = "Maximum concurrent executions in Map state"
  type        = number
  default     = 10
}

variable "enable_xray_tracing" {
  description = "Enable X-Ray tracing"
  type        = bool
  default     = true
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

variable "execution_time_alarm_threshold" {
  description = "Threshold for execution time alarms (milliseconds)"
  type        = number
  default     = 300000  # 5 minutes
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