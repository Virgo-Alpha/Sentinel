# Terraform Outputs for Sentinel Infrastructure

# S3 Buckets
output "content_bucket_name" {
  description = "Name of the S3 bucket for content storage"
  value       = module.s3.content_bucket_name
}

output "artifacts_bucket_name" {
  description = "Name of the S3 bucket for artifacts"
  value       = module.s3.artifacts_bucket_name
}

output "traces_bucket_name" {
  description = "Name of the S3 bucket for traces"
  value       = module.s3.traces_bucket_name
}

# DynamoDB Tables
output "articles_table_name" {
  description = "Name of the DynamoDB articles table"
  value       = module.dynamodb.articles_table_name
}

output "comments_table_name" {
  description = "Name of the DynamoDB comments table"
  value       = module.dynamodb.comments_table_name
}

output "memory_table_name" {
  description = "Name of the DynamoDB memory table"
  value       = module.dynamodb.memory_table_name
}

# OpenSearch (conditional)
output "opensearch_endpoint" {
  description = "OpenSearch Serverless endpoint"
  value       = var.enable_opensearch ? module.opensearch[0].endpoint : null
}

output "opensearch_collection_arn" {
  description = "OpenSearch Serverless collection ARN"
  value       = var.enable_opensearch ? module.opensearch[0].collection_arn : null
}

# Lambda Functions
output "lambda_function_arns" {
  description = "ARNs of all Lambda functions"
  value       = module.lambda.function_arns
}

output "lambda_function_names" {
  description = "Names of all Lambda functions"
  value       = module.lambda.function_names
}

# Step Functions
output "ingestion_state_machine_arn" {
  description = "ARN of the ingestion Step Functions state machine"
  value       = module.step_functions.ingestion_state_machine_arn
}

# API Gateway (conditional)
output "api_gateway_url" {
  description = "API Gateway URL for Analyst Assistant"
  value       = var.enable_amplify ? module.api_gateway[0].api_url : null
}

# Cognito (conditional)
output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = var.enable_amplify ? module.cognito[0].user_pool_id : null
}

output "cognito_user_pool_client_id" {
  description = "Cognito User Pool Client ID"
  value       = var.enable_amplify ? module.cognito[0].user_pool_client_id : null
}

# Amplify (conditional)
output "amplify_app_url" {
  description = "Amplify application URL"
  value       = var.enable_amplify ? module.amplify[0].app_url : null
}

# SES Configuration
output "ses_sender_email" {
  description = "Verified SES sender email"
  value       = var.enable_email_notifications ? module.ses[0].sender_email : null
}

# EventBridge
output "eventbridge_rule_arns" {
  description = "ARNs of EventBridge rules"
  value       = module.eventbridge.rule_arns
}

# SQS Queues
output "sqs_queue_urls" {
  description = "URLs of SQS queues"
  value       = module.sqs.queue_urls
}

output "sqs_dlq_urls" {
  description = "URLs of SQS dead letter queues"
  value       = module.sqs.dlq_urls
}

# IAM Roles
output "lambda_execution_role_arn" {
  description = "ARN of Lambda execution role"
  value       = module.iam.lambda_execution_role_arn
}

output "step_functions_role_arn" {
  description = "ARN of Step Functions execution role"
  value       = module.iam.step_functions_role_arn
}

# Agent Configuration (conditional)
output "ingestor_agent_id" {
  description = "Bedrock Ingestor Agent ID"
  value       = var.enable_agents ? module.bedrock_agents[0].ingestor_agent_id : null
}

output "analyst_agent_id" {
  description = "Bedrock Analyst Assistant Agent ID"
  value       = var.enable_agents ? module.bedrock_agents[0].analyst_agent_id : null
}

# KMS Keys
output "kms_key_arn" {
  description = "ARN of KMS key for encryption"
  value       = module.kms.key_arn
}

output "kms_key_id" {
  description = "ID of KMS key for encryption"
  value       = module.kms.key_id
}

# VPC Information
output "vpc_id" {
  description = "ID of the VPC"
  value       = var.create_vpc ? module.vpc[0].vpc_id : null
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = var.create_vpc ? module.vpc[0].private_subnet_ids : null
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = var.create_vpc ? module.vpc[0].public_subnet_ids : null
}

# CloudWatch Dashboard
output "cloudwatch_dashboard_url" {
  description = "URL of CloudWatch dashboard"
  value       = module.monitoring.dashboard_url
}

# Configuration for Environment Variables
output "environment_variables" {
  description = "Environment variables for Lambda functions and applications"
  value = {
    AWS_REGION                    = var.aws_region
    ENVIRONMENT                   = var.environment
    PROJECT_NAME                  = var.project_name
    ARTICLES_TABLE               = module.dynamodb.articles_table_name
    COMMENTS_TABLE               = module.dynamodb.comments_table_name
    MEMORY_TABLE                 = module.dynamodb.memory_table_name
    CONTENT_BUCKET               = module.s3.content_bucket_name
    ARTIFACTS_BUCKET             = module.s3.artifacts_bucket_name
    TRACES_BUCKET                = module.s3.traces_bucket_name
    OPENSEARCH_ENDPOINT          = var.enable_opensearch ? module.opensearch[0].endpoint : ""
    OPENSEARCH_INDEX_ARTICLES    = "sentinel-articles"
    OPENSEARCH_INDEX_VECTORS     = "sentinel-vectors"
    BEDROCK_MODEL_ID             = var.bedrock_model_id
    BEDROCK_EMBEDDING_MODEL      = var.bedrock_embedding_model
    INGESTOR_AGENT_ID           = var.enable_agents ? module.bedrock_agents[0].ingestor_agent_id : ""
    ANALYST_AGENT_ID            = var.enable_agents ? module.bedrock_agents[0].analyst_agent_id : ""
    INGESTION_STATE_MACHINE_ARN = module.step_functions.ingestion_state_machine_arn
    API_GATEWAY_URL             = var.enable_amplify ? module.api_gateway[0].api_url : ""
    SES_SENDER_EMAIL            = var.ses_sender_email
    MAX_CONCURRENT_FEEDS        = var.max_concurrent_feeds
    MAX_ARTICLES_PER_FETCH      = var.max_articles_per_fetch
    RELEVANCE_THRESHOLD         = var.relevance_threshold
    SIMILARITY_THRESHOLD        = var.similarity_threshold
    CONFIDENCE_THRESHOLD        = var.confidence_threshold
    MAX_DAILY_LLM_CALLS        = var.max_daily_llm_calls
    MAX_MONTHLY_COST_USD       = var.max_monthly_cost_usd
    ENABLE_AGENTS              = var.enable_agents
    ENABLE_AMPLIFY             = var.enable_amplify
    ENABLE_OPENSEARCH          = var.enable_opensearch
    ENABLE_SEMANTIC_DEDUP      = var.enable_semantic_dedup
    ENABLE_LLM_RELEVANCE       = var.enable_llm_relevance
    ENABLE_AUTO_PUBLISH        = var.enable_auto_publish
    ENABLE_EMAIL_NOTIFICATIONS = var.enable_email_notifications
    ENABLE_XRAY_TRACING        = var.enable_xray_tracing
  }
  sensitive = false
}

# Deployment Information
output "deployment_info" {
  description = "Deployment information and next steps"
  value = {
    environment           = var.environment
    region               = var.aws_region
    agents_enabled       = var.enable_agents
    amplify_enabled      = var.enable_amplify
    opensearch_enabled   = var.enable_opensearch
    next_steps = [
      "1. Configure RSS feeds in config/feeds.yaml",
      "2. Update keywords in config/keywords.yaml", 
      "3. Set up SES email identities for notifications",
      var.enable_agents ? "4. Deploy Strands agents to Bedrock AgentCore" : "4. Enable agents when ready with enable_agents=true",
      var.enable_amplify ? "5. Configure Amplify app deployment" : "5. Enable Amplify when ready with enable_amplify=true",
      "6. Test end-to-end ingestion pipeline",
      "7. Monitor CloudWatch dashboards and logs"
    ]
  }
}