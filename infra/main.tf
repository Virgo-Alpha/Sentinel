# Main Terraform configuration for Sentinel Infrastructure

terraform {
  required_version = ">= 1.5"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}

# Configure AWS Provider
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = merge(var.common_tags, {
      Environment = var.environment
      Project     = var.project_name
    })
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Random suffix for unique resource naming
resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  # Common naming convention
  name_prefix = "${var.project_name}-${var.environment}"
  
  # Resource names with unique suffix
  resource_suffix = random_id.suffix.hex
  
  # Common tags
  common_tags = merge(var.common_tags, {
    Environment = var.environment
    Project     = var.project_name
    Terraform   = "true"
  })
  
  # Account and region info
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
}

# KMS Module for encryption
module "kms" {
  source = "./modules/kms"
  
  name_prefix = local.name_prefix
  tags        = local.common_tags
}

# VPC Module (conditional)
module "vpc" {
  count  = var.create_vpc ? 1 : 0
  source = "./modules/vpc"
  
  name_prefix        = local.name_prefix
  vpc_cidr          = var.vpc_cidr
  availability_zones = var.availability_zones
  tags              = local.common_tags
}

# S3 Module for storage
module "s3" {
  source = "./modules/s3"
  
  name_prefix       = local.name_prefix
  resource_suffix   = local.resource_suffix
  kms_key_arn      = module.kms.key_arn
  retention_days   = var.content_retention_days
  tags             = local.common_tags
}

# DynamoDB Module for data storage
module "dynamodb" {
  source = "./modules/dynamodb"
  
  name_prefix    = local.name_prefix
  billing_mode   = var.dynamodb_billing_mode
  kms_key_arn   = module.kms.key_arn
  tags          = local.common_tags
}

# OpenSearch Module (conditional)
module "opensearch" {
  count  = var.enable_opensearch ? 1 : 0
  source = "./modules/opensearch"
  
  name_prefix = local.name_prefix
  vpc_id      = var.create_vpc ? module.vpc[0].vpc_id : null
  subnet_ids  = var.create_vpc ? module.vpc[0].private_subnet_ids : null
  kms_key_arn = module.kms.key_arn
  tags        = local.common_tags
}

# IAM Module for permissions
module "iam" {
  source = "./modules/iam"
  
  name_prefix           = local.name_prefix
  account_id           = local.account_id
  region               = local.region
  content_bucket_arn   = module.s3.content_bucket_arn
  artifacts_bucket_arn = module.s3.artifacts_bucket_arn
  traces_bucket_arn    = module.s3.traces_bucket_arn
  articles_table_arn   = module.dynamodb.articles_table_arn
  comments_table_arn   = module.dynamodb.comments_table_arn
  memory_table_arn     = module.dynamodb.memory_table_arn
  kms_key_arn         = module.kms.key_arn
  opensearch_arn      = var.enable_opensearch ? module.opensearch[0].collection_arn : null
  bedrock_model_id    = var.bedrock_model_id
  tags                = local.common_tags
}

# Lambda Module for functions
module "lambda" {
  source = "./modules/lambda"
  
  name_prefix           = local.name_prefix
  execution_role_arn    = module.iam.lambda_execution_role_arn
  memory_size          = var.lambda_memory_size
  timeout              = var.lambda_timeout
  enable_xray_tracing  = var.enable_xray_tracing
  vpc_config = var.create_vpc ? {
    subnet_ids         = module.vpc[0].private_subnet_ids
    security_group_ids = [module.vpc[0].lambda_security_group_id]
  } : null
  
  # Environment variables
  environment_variables = {
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
    BEDROCK_MODEL_ID             = var.bedrock_model_id
    BEDROCK_EMBEDDING_MODEL      = var.bedrock_embedding_model
    RELEVANCE_THRESHOLD          = var.relevance_threshold
    SIMILARITY_THRESHOLD         = var.similarity_threshold
    CONFIDENCE_THRESHOLD         = var.confidence_threshold
    MAX_DAILY_LLM_CALLS         = var.max_daily_llm_calls
    ENABLE_SEMANTIC_DEDUP       = var.enable_semantic_dedup
    ENABLE_LLM_RELEVANCE        = var.enable_llm_relevance
    ENABLE_AUTO_PUBLISH         = var.enable_auto_publish
  }
  
  tags = local.common_tags
}

# SQS Module for queuing
module "sqs" {
  source = "./modules/sqs"
  
  name_prefix = local.name_prefix
  kms_key_arn = module.kms.key_arn
  tags        = local.common_tags
}

# Step Functions Module for orchestration
module "step_functions" {
  source = "./modules/step_functions"
  
  name_prefix           = local.name_prefix
  execution_role_arn    = module.iam.step_functions_role_arn
  lambda_function_arns  = module.lambda.function_arns
  enable_agents        = var.enable_agents
  tags                 = local.common_tags
}

# EventBridge Module for scheduling
module "eventbridge" {
  source = "./modules/eventbridge"
  
  name_prefix              = local.name_prefix
  state_machine_arn        = module.step_functions.ingestion_state_machine_arn
  max_concurrent_feeds     = var.max_concurrent_feeds
  tags                     = local.common_tags
}

# SES Module for notifications (conditional)
module "ses" {
  count  = var.enable_email_notifications ? 1 : 0
  source = "./modules/ses"
  
  name_prefix       = local.name_prefix
  sender_email      = var.ses_sender_email
  escalation_emails = var.escalation_emails
  digest_emails     = var.digest_emails
  alert_emails      = var.alert_emails
  tags             = local.common_tags
}

# Cognito Module for authentication (conditional)
module "cognito" {
  count  = var.enable_amplify ? 1 : 0
  source = "./modules/cognito"
  
  name_prefix = local.name_prefix
  tags        = local.common_tags
}

# API Gateway Module (conditional)
module "api_gateway" {
  count  = var.enable_amplify ? 1 : 0
  source = "./modules/api_gateway"
  
  name_prefix        = local.name_prefix
  user_pool_id       = module.cognito[0].user_pool_id
  lambda_function_arn = module.lambda.function_arns["analyst_assistant"]
  tags               = local.common_tags
}

# Amplify Module for web application (conditional)
module "amplify" {
  count  = var.enable_amplify ? 1 : 0
  source = "./modules/amplify"
  
  name_prefix           = local.name_prefix
  user_pool_id          = module.cognito[0].user_pool_id
  user_pool_client_id   = module.cognito[0].user_pool_client_id
  api_gateway_url       = module.api_gateway[0].api_url
  tags                  = local.common_tags
}

# Bedrock Agents Module (conditional)
module "bedrock_agents" {
  count  = var.enable_agents ? 1 : 0
  source = "./modules/bedrock_agents"
  
  name_prefix           = local.name_prefix
  lambda_function_arns  = module.lambda.function_arns
  execution_role_arn    = module.iam.bedrock_agent_role_arn
  tags                  = local.common_tags
}

# Monitoring Module for observability
module "monitoring" {
  source = "./modules/monitoring"
  
  name_prefix              = local.name_prefix
  lambda_function_names    = module.lambda.function_names
  state_machine_arn        = module.step_functions.ingestion_state_machine_arn
  articles_table_name      = module.dynamodb.articles_table_name
  enable_detailed_monitoring = var.enable_detailed_monitoring
  log_retention_days       = var.log_retention_days
  alert_emails            = var.alert_emails
  tags                    = local.common_tags
}