# Outputs for Amplify Module

output "app_id" {
  description = "ID of the Amplify app"
  value       = aws_amplify_app.main.id
}

output "app_arn" {
  description = "ARN of the Amplify app"
  value       = aws_amplify_app.main.arn
}

output "app_url" {
  description = "Default URL of the Amplify app"
  value       = "https://${aws_amplify_branch.main.branch_name}.${aws_amplify_app.main.id}.amplifyapp.com"
}

output "main_branch_url" {
  description = "URL of the main branch"
  value       = "https://${aws_amplify_branch.main.branch_name}.${aws_amplify_app.main.id}.amplifyapp.com"
}

output "dev_branch_url" {
  description = "URL of the development branch"
  value       = var.create_dev_branch ? "https://${aws_amplify_branch.development[0].branch_name}.${aws_amplify_app.main.id}.amplifyapp.com" : null
}

output "custom_domain_url" {
  description = "Custom domain URL (if configured)"
  value       = var.custom_domain != null ? "https://${var.main_subdomain_prefix != "" ? "${var.main_subdomain_prefix}." : ""}${var.custom_domain}" : null
}

output "custom_dev_domain_url" {
  description = "Custom development domain URL (if configured)"
  value       = var.custom_domain != null && var.create_dev_branch ? "https://${var.dev_subdomain_prefix}.${var.custom_domain}" : null
}

output "webhook_url" {
  description = "Webhook URL for manual deployments"
  value       = aws_amplify_webhook.main.url
  sensitive   = true
}

output "domain_association_arn" {
  description = "ARN of domain association"
  value       = var.custom_domain != null ? aws_amplify_domain_association.main[0].arn : null
}

output "certificate_verification_dns_record" {
  description = "DNS record for certificate verification"
  value       = var.custom_domain != null ? aws_amplify_domain_association.main[0].certificate_verification_dns_record : null
}

output "service_role_arn" {
  description = "ARN of Amplify service role"
  value       = aws_iam_role.amplify_service.arn
}

output "log_group_name" {
  description = "Name of CloudWatch log group"
  value       = aws_cloudwatch_log_group.amplify.name
}

output "log_group_arn" {
  description = "ARN of CloudWatch log group"
  value       = aws_cloudwatch_log_group.amplify.arn
}

# Configuration for deployment
output "deployment_config" {
  description = "Deployment configuration information"
  value = {
    app_id              = aws_amplify_app.main.id
    main_branch         = aws_amplify_branch.main.branch_name
    dev_branch          = var.create_dev_branch ? aws_amplify_branch.development[0].branch_name : null
    webhook_url         = aws_amplify_webhook.main.url
    repository_url      = var.repository_url
    custom_domain       = var.custom_domain
    main_url           = "https://${aws_amplify_branch.main.branch_name}.${aws_amplify_app.main.id}.amplifyapp.com"
    dev_url            = var.create_dev_branch ? "https://${aws_amplify_branch.development[0].branch_name}.${aws_amplify_app.main.id}.amplifyapp.com" : null
  }
  sensitive = true
}

# Environment configuration for the web app
output "web_app_config" {
  description = "Configuration for the web application"
  value = {
    aws_region                = data.aws_region.current.name
    user_pool_id             = var.user_pool_id
    user_pool_web_client_id  = var.user_pool_client_id
    identity_pool_id         = var.identity_pool_id
    api_gateway_url          = var.api_gateway_url
    project_name             = var.name_prefix
  }
  sensitive = false
}