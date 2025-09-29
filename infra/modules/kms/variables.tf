# Variables for KMS Module

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "deletion_window_in_days" {
  description = "Number of days before KMS key deletion"
  type        = number
  default     = 7
  
  validation {
    condition     = var.deletion_window_in_days >= 7 && var.deletion_window_in_days <= 30
    error_message = "Deletion window must be between 7 and 30 days."
  }
}

variable "create_opensearch_key" {
  description = "Create separate KMS key for OpenSearch"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}