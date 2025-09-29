# Variables for EventBridge Module

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "state_machine_arn" {
  description = "ARN of Step Functions state machine"
  type        = string
}

variable "notifier_lambda_arn" {
  description = "ARN of notifier Lambda function"
  type        = string
}

variable "max_concurrent_feeds" {
  description = "Maximum number of feeds to process concurrently"
  type        = number
  default     = 5
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