# Variables for API Gateway Module

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "user_pool_arn" {
  description = "ARN of Cognito User Pool"
  type        = string
}

variable "analyst_assistant_lambda_arn" {
  description = "ARN of Analyst Assistant Lambda function"
  type        = string
}

variable "analyst_assistant_lambda_invoke_arn" {
  description = "Invoke ARN of Analyst Assistant Lambda function"
  type        = string
}

variable "query_kb_lambda_arn" {
  description = "ARN of Query KB Lambda function"
  type        = string
}

variable "query_kb_lambda_invoke_arn" {
  description = "Invoke ARN of Query KB Lambda function"
  type        = string
}

variable "storage_tool_lambda_arn" {
  description = "ARN of Storage Tool Lambda function"
  type        = string
}

variable "storage_tool_lambda_invoke_arn" {
  description = "Invoke ARN of Storage Tool Lambda function"
  type        = string
}

variable "commentary_api_lambda_arn" {
  description = "ARN of Commentary API Lambda function"
  type        = string
}

variable "commentary_api_lambda_invoke_arn" {
  description = "Invoke ARN of Commentary API Lambda function"
  type        = string
}

variable "publish_decision_lambda_arn" {
  description = "ARN of Publish Decision Lambda function"
  type        = string
}

variable "publish_decision_lambda_invoke_arn" {
  description = "Invoke ARN of Publish Decision Lambda function"
  type        = string
}

variable "stage_name" {
  description = "API Gateway stage name"
  type        = string
  default     = "v1"
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

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}