# Outputs for Cognito Module

output "user_pool_id" {
  description = "ID of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.id
}

output "user_pool_arn" {
  description = "ARN of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.arn
}

output "user_pool_endpoint" {
  description = "Endpoint of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.endpoint
}

output "user_pool_client_id" {
  description = "ID of the Cognito User Pool Client"
  value       = aws_cognito_user_pool_client.main.id
}

output "user_pool_client_secret" {
  description = "Secret of the Cognito User Pool Client"
  value       = aws_cognito_user_pool_client.main.client_secret
  sensitive   = true
}

output "user_pool_domain" {
  description = "Domain of the Cognito User Pool"
  value       = aws_cognito_user_pool_domain.main.domain
}

output "user_pool_domain_cloudfront_distribution_arn" {
  description = "CloudFront distribution ARN for the User Pool domain"
  value       = aws_cognito_user_pool_domain.main.cloudfront_distribution_arn
}

output "identity_pool_id" {
  description = "ID of the Cognito Identity Pool"
  value       = aws_cognito_identity_pool.main.id
}

output "identity_pool_arn" {
  description = "ARN of the Cognito Identity Pool"
  value       = aws_cognito_identity_pool.main.arn
}

output "analyst_group_name" {
  description = "Name of the Analyst user group"
  value       = aws_cognito_user_group.analysts.name
}

output "admin_group_name" {
  description = "Name of the Admin user group"
  value       = aws_cognito_user_group.admins.name
}

output "analyst_role_arn" {
  description = "ARN of the Analyst group role"
  value       = aws_iam_role.analyst_group.arn
}

output "admin_role_arn" {
  description = "ARN of the Admin group role"
  value       = aws_iam_role.admin_group.arn
}

output "authenticated_role_arn" {
  description = "ARN of the authenticated user role"
  value       = aws_iam_role.authenticated.arn
}

# Configuration for client applications
output "auth_config" {
  description = "Authentication configuration for client applications"
  value = {
    region                = data.aws_region.current.name
    userPoolId           = aws_cognito_user_pool.main.id
    userPoolWebClientId  = aws_cognito_user_pool_client.main.id
    identityPoolId       = aws_cognito_identity_pool.main.id
    domain               = aws_cognito_user_pool_domain.main.domain
    oauth = {
      domain       = "${aws_cognito_user_pool_domain.main.domain}.auth.${data.aws_region.current.name}.amazoncognito.com"
      scope        = ["email", "openid", "profile", "aws.cognito.signin.user.admin"]
      redirectSignIn  = var.callback_urls
      redirectSignOut = var.logout_urls
      responseType = "code"
    }
  }
  sensitive = false
}

# URLs for authentication flows
output "hosted_ui_url" {
  description = "Hosted UI URL for authentication"
  value       = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${data.aws_region.current.name}.amazoncognito.com/login"
}

output "logout_url" {
  description = "Logout URL"
  value       = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${data.aws_region.current.name}.amazoncognito.com/logout"
}

# Group information
output "user_groups" {
  description = "Information about user groups"
  value = {
    analysts = {
      name        = aws_cognito_user_group.analysts.name
      description = aws_cognito_user_group.analysts.description
      precedence  = aws_cognito_user_group.analysts.precedence
      role_arn    = aws_cognito_user_group.analysts.role_arn
    }
    admins = {
      name        = aws_cognito_user_group.admins.name
      description = aws_cognito_user_group.admins.description
      precedence  = aws_cognito_user_group.admins.precedence
      role_arn    = aws_cognito_user_group.admins.role_arn
    }
  }
}