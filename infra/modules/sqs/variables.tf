# Variables for SQS Module

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of KMS key for encryption"
  type        = string
}

variable "enable_fifo_queue" {
  description = "Enable FIFO queue for ordered processing"
  type        = bool
  default     = false
}

variable "queue_depth_alarm_threshold" {
  description = "Threshold for queue depth alarms"
  type        = number
  default     = 100
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