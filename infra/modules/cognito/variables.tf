# Variables for Cognito Module

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "admin_create_user_only" {
  description = "Only allow admins to create users"
  type        = bool
  default     = true
}

variable "enable_mfa" {
  description = "Enable multi-factor authentication"
  type        = bool
  default     = true
}

variable "callback_urls" {
  description = "List of allowed callback URLs"
  type        = list(string)
  default     = ["http://localhost:3000/callback"]
}

variable "logout_urls" {
  description = "List of allowed logout URLs"
  type        = list(string)
  default     = ["http://localhost:3000/logout"]
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}