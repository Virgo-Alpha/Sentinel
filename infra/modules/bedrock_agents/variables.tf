# Variables for Bedrock Agents Module

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "lambda_function_arns" {
  description = "Map of Lambda function ARNs for agent tools"
  type        = map(string)
}

variable "execution_role_arn" {
  description = "IAM role ARN for Bedrock Agent execution"
  type        = string
}

variable "foundation_model" {
  description = "Bedrock foundation model ID for agents"
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v2:0"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}