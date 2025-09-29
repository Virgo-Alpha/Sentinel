# Lambda Module for Sentinel Infrastructure
# Creates Lambda functions with archive_file packaging and S3 upload triggers

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local values for Lambda functions
locals {
  lambda_functions = {
    feed_parser = {
      description = "Parse RSS feeds and extract articles"
      handler     = "feed_parser.lambda_handler"
      runtime     = "python3.11"
      timeout     = var.timeout
      memory_size = var.memory_size
    }
    relevancy_evaluator = {
      description = "Evaluate content relevance using LLM"
      handler     = "relevancy_evaluator.lambda_handler"
      runtime     = "python3.11"
      timeout     = var.timeout * 2 # Longer timeout for LLM calls
      memory_size = var.memory_size * 2
    }
    dedup_tool = {
      description = "Perform multi-layered deduplication"
      handler     = "dedup_tool.lambda_handler"
      runtime     = "python3.11"
      timeout     = var.timeout
      memory_size = var.memory_size
    }
    guardrail_tool = {
      description = "Comprehensive content validation"
      handler     = "guardrail_tool.lambda_handler"
      runtime     = "python3.11"
      timeout     = var.timeout
      memory_size = var.memory_size
    }
    storage_tool = {
      description = "DynamoDB and S3 operations"
      handler     = "storage_tool.lambda_handler"
      runtime     = "python3.11"
      timeout     = var.timeout
      memory_size = var.memory_size
    }
    human_escalation = {
      description = "Queue items for human review"
      handler     = "human_escalation.lambda_handler"
      runtime     = "python3.11"
      timeout     = var.timeout
      memory_size = var.memory_size
    }
    notifier = {
      description = "Send notifications via SES"
      handler     = "notifier.lambda_handler"
      runtime     = "python3.11"
      timeout     = var.timeout
      memory_size = var.memory_size
    }
    query_kb = {
      description = "Query knowledge base with natural language"
      handler     = "query_kb.lambda_handler"
      runtime     = "python3.11"
      timeout     = var.timeout * 2
      memory_size = var.memory_size
    }
    analyst_assistant = {
      description = "Interactive analyst assistant agent"
      handler     = "analyst_assistant.lambda_handler"
      runtime     = "python3.11"
      timeout     = var.timeout * 3 # Longest timeout for interactive sessions
      memory_size = var.memory_size * 2
    }
    publish_decision = {
      description = "Process human approval/rejection decisions"
      handler     = "publish_decision.lambda_handler"
      runtime     = "python3.11"
      timeout     = var.timeout
      memory_size = var.memory_size
    }
    commentary_api = {
      description = "Manage comments and discussions"
      handler     = "commentary_api.lambda_handler"
      runtime     = "python3.11"
      timeout     = var.timeout
      memory_size = var.memory_size
    }
  }
}

# Create deployment packages for each Lambda function
data "archive_file" "lambda_packages" {
  for_each = local.lambda_functions

  type        = "zip"
  output_path = "${path.module}/../../artifacts/${each.key}.zip"

  # Source from the src/lambda_tools directory
  source_dir = "${path.module}/../../../src/lambda_tools"

  # Exclude files that shouldn't be in the package
  excludes = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".pytest_cache",
    "tests",
    "*.md"
  ]
}

# Upload Lambda packages to S3
resource "aws_s3_object" "lambda_packages" {
  for_each = local.lambda_functions

  bucket = var.artifacts_bucket_name
  key    = "lambda/${each.key}/${filemd5(data.archive_file.lambda_packages[each.key].output_path)}.zip"
  source = data.archive_file.lambda_packages[each.key].output_path
  etag   = filemd5(data.archive_file.lambda_packages[each.key].output_path)

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-${each.key}-package"
    Function = each.key
  })
}

# Lambda Functions
resource "aws_lambda_function" "functions" {
  for_each = local.lambda_functions

  function_name = "${var.name_prefix}-${each.key}"
  description   = each.value.description

  # S3 deployment
  s3_bucket = var.artifacts_bucket_name
  s3_key    = aws_s3_object.lambda_packages[each.key].key

  handler     = each.value.handler
  runtime     = each.value.runtime
  timeout     = each.value.timeout
  memory_size = each.value.memory_size

  role = var.execution_role_arn

  # Environment variables
  environment {
    variables = var.environment_variables
  }

  # VPC Configuration (conditional)
  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [var.vpc_config] : []
    content {
      subnet_ids         = vpc_config.value.subnet_ids
      security_group_ids = vpc_config.value.security_group_ids
    }
  }

  # X-Ray Tracing
  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  # Lambda Layers (including X-Ray correlation layer)
  layers = compact(concat(
    var.xray_layer_arn != "" ? [var.xray_layer_arn] : [],
    var.additional_layers
  ))

  # Dead letter queue configuration
  dead_letter_config {
    target_arn = aws_sqs_queue.lambda_dlq[each.key].arn
  }

  # Reserved concurrency (optional)
  reserved_concurrent_executions = var.reserved_concurrency

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-${each.key}"
    Function = each.key
  })

  depends_on = [aws_s3_object.lambda_packages]
}

# Dead Letter Queues for Lambda functions
resource "aws_sqs_queue" "lambda_dlq" {
  for_each = local.lambda_functions

  name = "${var.name_prefix}-${each.key}-dlq"

  # Message retention
  message_retention_seconds = 1209600 # 14 days

  # Visibility timeout should be longer than Lambda timeout
  visibility_timeout_seconds = each.value.timeout + 30

  # Server-side encryption
  kms_master_key_id = var.kms_key_arn

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-${each.key}-dlq"
    Function = each.key
    Purpose  = "Dead letter queue"
  })
}

# CloudWatch Log Groups for Lambda functions
resource "aws_cloudwatch_log_group" "lambda_logs" {
  for_each = local.lambda_functions

  name              = "/aws/lambda/${var.name_prefix}-${each.key}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-${each.key}-logs"
    Function = each.key
  })
}

# Lambda Permissions for S3 trigger (artifacts bucket)
resource "aws_lambda_permission" "s3_trigger" {
  for_each = toset(["feed_parser", "storage_tool"]) # Functions that need S3 triggers

  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.functions[each.key].function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.content_bucket_arn
}

# Lambda Permissions for EventBridge
resource "aws_lambda_permission" "eventbridge_trigger" {
  for_each = toset(["feed_parser"]) # Functions triggered by EventBridge

  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.functions[each.key].function_name
  principal     = "events.amazonaws.com"
}

# Lambda Permissions for API Gateway (conditional)
resource "aws_lambda_permission" "api_gateway_trigger" {
  for_each = var.enable_api_gateway ? toset(["analyst_assistant", "query_kb", "commentary_api"]) : toset([])

  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.functions[each.key].function_name
  principal     = "apigateway.amazonaws.com"
}

# Lambda Function URLs (for direct HTTP access)
resource "aws_lambda_function_url" "function_urls" {
  for_each = toset(["analyst_assistant"]) # Only for functions that need direct HTTP access

  function_name      = aws_lambda_function.functions[each.key].function_name
  authorization_type = "AWS_IAM"

  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["GET", "POST"]
    allow_headers     = ["date", "keep-alive"]
    expose_headers    = ["date", "keep-alive"]
    max_age           = 86400
  }
}

# Lambda Aliases for versioning
resource "aws_lambda_alias" "function_aliases" {
  for_each = local.lambda_functions

  name             = "live"
  description      = "Live alias for ${each.key}"
  function_name    = aws_lambda_function.functions[each.key].function_name
  function_version = "$LATEST"
}

# CloudWatch Alarms for Lambda functions
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = local.lambda_functions

  alarm_name          = "${var.name_prefix}-${each.key}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors lambda errors for ${each.key}"
  alarm_actions       = var.alarm_topic_arn != null ? [var.alarm_topic_arn] : []

  dimensions = {
    FunctionName = aws_lambda_function.functions[each.key].function_name
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-${each.key}-error-alarm"
    Function = each.key
  })
}

# CloudWatch Alarms for Lambda duration
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  for_each = local.lambda_functions

  alarm_name          = "${var.name_prefix}-${each.key}-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = each.value.timeout * 1000 * 0.8 # 80% of timeout in milliseconds
  alarm_description   = "This metric monitors lambda duration for ${each.key}"
  alarm_actions       = var.alarm_topic_arn != null ? [var.alarm_topic_arn] : []

  dimensions = {
    FunctionName = aws_lambda_function.functions[each.key].function_name
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-${each.key}-duration-alarm"
    Function = each.key
  })
}
