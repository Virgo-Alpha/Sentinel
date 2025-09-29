# Outputs for Production Environment

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

output "opensearch_endpoint" {
  description = "OpenSearch endpoint"
  value       = module.sentinel.opensearch_endpoint
}

# Lambda Functions
output "lambda_function_names" {
  description = "Names of Lambda functions"
  value       = module.sentinel.lambda_function_names
}

output "lambda_function_arns" {
  description = "ARNs of Lambda functions"
  value       = module.sentinel.lambda_function_arns
}

# Step Functions
output "ingestion_state_machine_arn" {
  description = "ARN of ingestion state machine"
  value       = module.sentinel.ingestion_state_machine_arn
}

# Agents (if enabled)
output "ingestor_agent_id" {
  description = "Bedrock Ingestor Agent ID"
  value       = module.sentinel.ingestor_agent_id
}

output "analyst_agent_id" {
  description = "Bedrock Analyst Assistant Agent ID"
  value       = module.sentinel.analyst_agent_id
}

# Web Application
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

output "cognito_user_pool_client_id" {
  description = "Cognito User Pool Client ID"
  value       = module.sentinel.cognito_user_pool_client_id
}

# Security
output "waf_web_acl_arn" {
  description = "WAF Web ACL ARN"
  value       = module.sentinel.waf_web_acl_arn
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

# Production Deployment Information
output "deployment_info" {
  description = "Production environment deployment information"
  value = {
    environment     = "prod"
    region         = var.aws_region
    vpc_id         = module.sentinel.vpc_id
    amplify_url    = module.sentinel.amplify_app_url
    api_url        = module.sentinel.api_gateway_url
    dashboard_url  = module.sentinel.cloudwatch_dashboard_url
    
    # Production-specific info
    features_enabled = {
      agents              = var.enable_agents
      amplify            = true
      opensearch         = true
      semantic_dedup     = true
      auto_publish       = var.enable_auto_publish
    }
    
    # Resource configuration
    resource_config = {
      lambda_memory_mb     = 1024
      retention_days       = var.log_retention_days
      max_concurrent_feeds = var.max_concurrent_feeds
      availability_zones   = 3
    }
    
    # Performance targets
    performance_targets = {
      median_latency_minutes    = 5
      duplicate_detection_rate  = 0.85
      relevance_accuracy       = 0.90
      uptime_percentage        = 99.9
    }
    
    # Operational procedures
    operational_info = [
      "1. Monitor CloudWatch dashboard for system health",
      "2. Review daily digest emails for processing summary",
      "3. Check escalation queue for items requiring review",
      "4. Validate feed health and keyword effectiveness weekly",
      "5. Review cost anomaly alerts and optimize as needed",
      "6. Update RSS feeds and keywords as threat landscape evolves",
      "7. Perform monthly security review and access audit"
    ]
  }
}

# Backup and Recovery Information
output "backup_info" {
  description = "Backup and recovery information"
  value = {
    dynamodb_point_in_time_recovery = true
    s3_versioning_enabled          = true
    log_retention_days             = var.log_retention_days
    cross_region_replication       = false  # Can be enabled if needed
    
    recovery_procedures = [
      "DynamoDB: Use point-in-time recovery for data restoration",
      "S3: Use versioning to recover deleted/modified objects",
      "Lambda: Redeploy from artifacts bucket or source control",
      "Configuration: Restore from Terraform state and source control"
    ]
  }
}

# Security and Compliance
output "security_info" {
  description = "Security and compliance information"
  value = {
    encryption_at_rest = {
      dynamodb = "KMS encrypted"
      s3       = "KMS encrypted"
      logs     = "KMS encrypted"
    }
    
    encryption_in_transit = {
      api_gateway = "TLS 1.2+"
      lambda      = "TLS 1.2+"
      vpc_endpoints = "TLS 1.2+"
    }
    
    access_control = {
      iam_roles        = "Least privilege principle"
      cognito_groups   = "Role-based access (Analyst, Admin)"
      waf_protection   = "Enabled with managed rules"
      vpc_isolation    = "Private subnets with VPC endpoints"
    }
    
    monitoring = {
      cloudtrail       = "Recommended (not managed by this module)"
      guardduty        = "Recommended (not managed by this module)"
      security_hub     = "Recommended (not managed by this module)"
      config           = "Recommended (not managed by this module)"
    }
  }
}