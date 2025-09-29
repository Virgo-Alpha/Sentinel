# Outputs for Development Environment

# Core Infrastructure
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.sentinel.vpc_id
}

output "content_bucket_name" {
  description = "Name of the content S3 bucket"
  value       = module.sentinel.content_bucket_name
}

output "articles_table_name" {
  description = "Name of the articles DynamoDB table"
  value       = module.sentinel.articles_table_name
}

# Lambda Functions
output "lambda_function_names" {
  description = "Names of Lambda functions"
  value       = module.sentinel.lambda_function_names
}

# Step Functions
output "ingestion_state_machine_arn" {
  description = "ARN of ingestion state machine"
  value       = module.sentinel.ingestion_state_machine_arn
}

# Web Application (if enabled)
output "amplify_app_url" {
  description = "Amplify application URL"
  value       = module.sentinel.amplify_app_url
}

output "api_gateway_url" {
  description = "API Gateway URL"
  value       = module.sentinel.api_gateway_url
}

# Authentication
output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = module.sentinel.cognito_user_pool_id
}

# Monitoring
output "cloudwatch_dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = module.sentinel.cloudwatch_dashboard_url
}

# Environment Configuration
output "environment_variables" {
  description = "Environment variables for applications"
  value       = module.sentinel.environment_variables
  sensitive   = false
}

# Deployment Information
output "deployment_info" {
  description = "Development environment deployment information"
  value = {
    environment     = "dev"
    region         = var.aws_region
    vpc_id         = module.sentinel.vpc_id
    amplify_url    = module.sentinel.amplify_app_url
    api_url        = module.sentinel.api_gateway_url
    dashboard_url  = module.sentinel.cloudwatch_dashboard_url
    
    # Development-specific info
    features_enabled = {
      agents              = false
      amplify            = true
      opensearch         = false
      semantic_dedup     = false
      auto_publish       = false
    }
    
    # Resource limits
    cost_limits = {
      max_daily_llm_calls  = 1000
      max_monthly_cost_usd = 200
      lambda_memory_mb     = 256
      retention_days       = 90
    }
    
    # Next steps
    setup_instructions = [
      "1. Verify SES email identities in AWS Console",
      "2. Configure RSS feeds in config/feeds.yaml",
      "3. Update keywords in config/keywords.yaml",
      "4. Test Lambda functions individually",
      "5. Run end-to-end ingestion test",
      "6. Access web app at Amplify URL",
      "7. Monitor via CloudWatch dashboard"
    ]
  }
}