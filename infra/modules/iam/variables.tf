# Variables for IAM Module

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "region" {
  description = "AWS Region"
  type        = string
}

variable "content_bucket_arn" {
  description = "ARN of content S3 bucket"
  type        = string
}

variable "artifacts_bucket_arn" {
  description = "ARN of artifacts S3 bucket"
  type        = string
}

variable "traces_bucket_arn" {
  description = "ARN of traces S3 bucket"
  type        = string
}

variable "articles_table_arn" {
  description = "ARN of articles DynamoDB table"
  type        = string
}

variable "comments_table_arn" {
  description = "ARN of comments DynamoDB table"
  type        = string
}

variable "memory_table_arn" {
  description = "ARN of memory DynamoDB table"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of KMS key"
  type        = string
}

variable "opensearch_arn" {
  description = "ARN of OpenSearch collection"
  type        = string
  default     = null
}

variable "bedrock_model_id" {
  description = "Bedrock model ID"
  type        = string
}

variable "enable_vpc_access" {
  description = "Enable VPC access for Lambda"
  type        = bool
  default     = false
}

variable "enable_bedrock_agents" {
  description = "Enable Bedrock Agent roles"
  type        = bool
  default     = false
}

variable "enable_api_gateway" {
  description = "Enable API Gateway roles"
  type        = bool
  default     = false
}

variable "enable_ses" {
  description = "Enable SES roles"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}