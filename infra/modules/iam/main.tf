# IAM Module for Sentinel Infrastructure
# Creates scoped roles for each Lambda function and service

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Lambda Execution Role
resource "aws_iam_role" "lambda_execution" {
  name = "${var.name_prefix}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-lambda-execution-role"
    Purpose = "Lambda function execution"
  })
}

# Lambda Execution Policy
resource "aws_iam_role_policy" "lambda_execution" {
  name = "${var.name_prefix}-lambda-execution-policy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.region}:${var.account_id}:log-group:/aws/lambda/${var.name_prefix}-*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          var.articles_table_arn,
          "${var.articles_table_arn}/index/*",
          var.comments_table_arn,
          "${var.comments_table_arn}/index/*",
          var.memory_table_arn,
          "${var.memory_table_arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${var.content_bucket_arn}/*",
          "${var.artifacts_bucket_arn}/*",
          "${var.traces_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          var.content_bucket_arn,
          var.artifacts_bucket_arn,
          var.traces_bucket_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:GetFoundationModel",
          "bedrock:ListFoundationModels"
        ]
        Resource = [
          "arn:aws:bedrock:${var.region}::foundation-model/${var.bedrock_model_id}",
          "arn:aws:bedrock:${var.region}::foundation-model/amazon.titan-embed-*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = var.kms_key_arn
      },
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"
      }
    ]
  })
}

# OpenSearch access policy (conditional)
resource "aws_iam_role_policy" "lambda_opensearch" {
  count = var.opensearch_arn != null ? 1 : 0
  name  = "${var.name_prefix}-lambda-opensearch-policy"
  role  = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = var.opensearch_arn
      }
    ]
  })
}

# VPC access policy for Lambda (conditional)
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  count      = var.enable_vpc_access ? 1 : 0
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Step Functions Execution Role
resource "aws_iam_role" "step_functions" {
  name = "${var.name_prefix}-step-functions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-step-functions-role"
    Purpose = "Step Functions execution"
  })
}

# Step Functions Execution Policy
resource "aws_iam_role_policy" "step_functions" {
  name = "${var.name_prefix}-step-functions-policy"
  role = aws_iam_role.step_functions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:${var.region}:${var.account_id}:function:${var.name_prefix}-*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeAgent"
        ]
        Resource = "arn:aws:bedrock:${var.region}:${var.account_id}:agent/*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.region}:${var.account_id}:log-group:/aws/stepfunctions/${var.name_prefix}-*"
      },
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets"
        ]
        Resource = "*"
      }
    ]
  })
}

# EventBridge Execution Role
resource "aws_iam_role" "eventbridge" {
  name = "${var.name_prefix}-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-eventbridge-role"
    Purpose = "EventBridge rule execution"
  })
}

# EventBridge Execution Policy
resource "aws_iam_role_policy" "eventbridge" {
  name = "${var.name_prefix}-eventbridge-policy"
  role = aws_iam_role.eventbridge.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = "arn:aws:states:${var.region}:${var.account_id}:stateMachine:${var.name_prefix}-*"
      }
    ]
  })
}

# Bedrock Agent Execution Role (conditional)
resource "aws_iam_role" "bedrock_agent" {
  count = var.enable_bedrock_agents ? 1 : 0
  name  = "${var.name_prefix}-bedrock-agent-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-bedrock-agent-role"
    Purpose = "Bedrock Agent execution"
  })
}

# Bedrock Agent Execution Policy
resource "aws_iam_role_policy" "bedrock_agent" {
  count = var.enable_bedrock_agents ? 1 : 0
  name  = "${var.name_prefix}-bedrock-agent-policy"
  role  = aws_iam_role.bedrock_agent[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:${var.region}::foundation-model/${var.bedrock_model_id}",
          "arn:aws:bedrock:${var.region}::foundation-model/amazon.titan-embed-*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:${var.region}:${var.account_id}:function:${var.name_prefix}-*"
      }
    ]
  })
}

# API Gateway Execution Role (conditional)
resource "aws_iam_role" "api_gateway" {
  count = var.enable_api_gateway ? 1 : 0
  name  = "${var.name_prefix}-api-gateway-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-api-gateway-role"
    Purpose = "API Gateway execution"
  })
}

# API Gateway Execution Policy
resource "aws_iam_role_policy" "api_gateway" {
  count = var.enable_api_gateway ? 1 : 0
  name  = "${var.name_prefix}-api-gateway-policy"
  role  = aws_iam_role.api_gateway[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:${var.region}:${var.account_id}:function:${var.name_prefix}-*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeAgent"
        ]
        Resource = "arn:aws:bedrock:${var.region}:${var.account_id}:agent/*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.region}:${var.account_id}:log-group:/aws/apigateway/${var.name_prefix}-*"
      }
    ]
  })
}

# SES Execution Role (conditional)
resource "aws_iam_role" "ses" {
  count = var.enable_ses ? 1 : 0
  name  = "${var.name_prefix}-ses-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-ses-role"
    Purpose = "SES email sending"
  })
}

# SES Execution Policy
resource "aws_iam_role_policy" "ses" {
  count = var.enable_ses ? 1 : 0
  name  = "${var.name_prefix}-ses-policy"
  role  = aws_iam_role.ses[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail",
          "ses:SendTemplatedEmail"
        ]
        Resource = "*"
      }
    ]
  })
}