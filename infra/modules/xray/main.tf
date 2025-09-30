# X-Ray Distributed Tracing Module for Sentinel
# Provides comprehensive tracing across all Lambda functions and agent executions

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

# X-Ray Service Map for Sentinel Architecture
resource "aws_xray_group" "sentinel_service_map" {
  group_name        = "${var.name_prefix}-service-map"
  filter_expression = "service(\"${var.name_prefix}-*\")"

  insights_configuration {
    insights_enabled      = true
    notifications_enabled = var.enable_xray_insights_notifications
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-xray-service-map"
    Purpose = "Sentinel service map visualization"
  })
}

# X-Ray Groups for different service tiers
resource "aws_xray_group" "agent_tools" {
  group_name        = "${var.name_prefix}-agent-tools"
  filter_expression = "service(\"${var.name_prefix}-*-agent\") OR service(\"${var.name_prefix}-*-tool\")"

  insights_configuration {
    insights_enabled      = true
    notifications_enabled = var.enable_xray_insights_notifications
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-xray-agent-tools"
    Purpose = "Agent tools tracing group"
  })
}

resource "aws_xray_group" "ingestion_pipeline" {
  group_name        = "${var.name_prefix}-ingestion-pipeline"
  filter_expression = "service(\"${var.name_prefix}-feed-parser\") OR service(\"${var.name_prefix}-relevancy-evaluator\") OR service(\"${var.name_prefix}-dedup-tool\")"

  insights_configuration {
    insights_enabled      = true
    notifications_enabled = var.enable_xray_insights_notifications
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-xray-ingestion-pipeline"
    Purpose = "Ingestion pipeline tracing group"
  })
}

resource "aws_xray_group" "human_workflow" {
  group_name        = "${var.name_prefix}-human-workflow"
  filter_expression = "service(\"${var.name_prefix}-human-escalation\") OR service(\"${var.name_prefix}-publish-decision\") OR service(\"${var.name_prefix}-commentary-api\")"

  insights_configuration {
    insights_enabled      = true
    notifications_enabled = var.enable_xray_insights_notifications
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-xray-human-workflow"
    Purpose = "Human workflow tracing group"
  })
}

resource "aws_xray_group" "errors_and_failures" {
  group_name        = "${var.name_prefix}-errors"
  filter_expression = "error = true OR fault = true OR responsetime > 30"

  insights_configuration {
    insights_enabled      = true
    notifications_enabled = true
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-xray-errors"
    Purpose = "Error and failure tracing group"
  })
}

# X-Ray Sampling Rules with correlation ID support
resource "aws_xray_sampling_rule" "correlation_id_high_priority" {
  rule_name      = "${var.name_prefix}-correlation-id-high-priority"
  priority       = 500
  version        = 1
  reservoir_size = 5
  fixed_rate     = 1.0
  url_path       = "*"
  host           = "*"
  http_method    = "*"
  service_type   = "*"
  service_name   = "${var.name_prefix}-*"
  resource_arn   = "*"

  # Sample all requests with correlation IDs for complete tracing
  attributes = {
    correlation_id = "*"
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-xray-correlation-id-sampling"
    Purpose = "High priority sampling for requests with correlation IDs"
  })
}

resource "aws_xray_sampling_rule" "agent_execution_tracing" {
  rule_name      = "${var.name_prefix}-agent-execution"
  priority       = 1000
  version        = 1
  reservoir_size = 3
  fixed_rate     = 0.8
  url_path       = "*"
  host           = "*"
  http_method    = "*"
  service_type   = "*"
  service_name   = "*agent*"
  resource_arn   = "*"

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-xray-agent-execution-sampling"
    Purpose = "Agent execution tracing"
  })
}

resource "aws_xray_sampling_rule" "error_tracing" {
  rule_name      = "${var.name_prefix}-error-tracing"
  priority       = 100
  version        = 1
  reservoir_size = 10
  fixed_rate     = 1.0
  url_path       = "*"
  host           = "*"
  http_method    = "*"
  service_type   = "*"
  service_name   = "*"
  resource_arn   = "*"

  # Sample all error conditions
  attributes = {
    error = "true"
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-xray-error-sampling"
    Purpose = "Complete tracing for error conditions"
  })
}

# CloudWatch Alarms for X-Ray Metrics
resource "aws_cloudwatch_metric_alarm" "xray_high_latency" {
  alarm_name          = "${var.name_prefix}-xray-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ResponseTime"
  namespace           = "AWS/X-Ray"
  period              = "300"
  statistic           = "Average"
  threshold           = "30"
  alarm_description   = "High latency detected in X-Ray traces"
  alarm_actions       = [var.alerts_topic_arn]

  dimensions = {
    ServiceName = "${var.name_prefix}-*"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-xray-high-latency-alarm"
  })
}

resource "aws_cloudwatch_metric_alarm" "xray_error_rate" {
  alarm_name          = "${var.name_prefix}-xray-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ErrorRate"
  namespace           = "AWS/X-Ray"
  period              = "300"
  statistic           = "Average"
  threshold           = "5"
  alarm_description   = "High error rate detected in X-Ray traces"
  alarm_actions       = [var.alerts_topic_arn]

  dimensions = {
    ServiceName = "${var.name_prefix}-*"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-xray-error-rate-alarm"
  })
}

# Lambda Layer for X-Ray SDK and correlation ID utilities
resource "aws_lambda_layer_version" "xray_correlation_layer" {
  filename         = var.xray_layer_zip_path
  layer_name       = "${var.name_prefix}-xray-correlation-layer"
  description      = "X-Ray SDK with correlation ID utilities for Sentinel"
  source_code_hash = var.xray_layer_source_hash

  compatible_runtimes = ["python3.11", "python3.12"]

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-xray-correlation-layer"
    Purpose = "X-Ray tracing utilities"
  })
}

# IAM Role for X-Ray access
resource "aws_iam_role" "xray_role" {
  name = "${var.name_prefix}-xray-role"

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
    Name    = "${var.name_prefix}-xray-role"
    Purpose = "X-Ray tracing permissions"
  })
}

resource "aws_iam_role_policy" "xray_policy" {
  name = "${var.name_prefix}-xray-policy"
  role = aws_iam_role.xray_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets",
          "xray:GetSamplingStatisticSummaries"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
      }
    ]
  })
}

# CloudWatch Insights Queries for X-Ray Analysis
resource "aws_cloudwatch_query_definition" "xray_trace_analysis" {
  name = "${var.name_prefix}-xray-trace-analysis"

  log_group_names = [
    "/aws/lambda/${var.name_prefix}-feed-parser",
    "/aws/lambda/${var.name_prefix}-relevancy-evaluator",
    "/aws/lambda/${var.name_prefix}-dedup-tool"
  ]

  query_string = <<EOF
fields @timestamp, @message, @xrayTraceId, correlation_id
| filter ispresent(@xrayTraceId)
| sort @timestamp desc
| limit 100
EOF
}

resource "aws_cloudwatch_query_definition" "correlation_id_flow" {
  name = "${var.name_prefix}-correlation-id-flow"

  log_group_names = [
    "/aws/lambda/${var.name_prefix}-feed-parser",
    "/aws/lambda/${var.name_prefix}-relevancy-evaluator",
    "/aws/lambda/${var.name_prefix}-dedup-tool",
    "/aws/lambda/${var.name_prefix}-guardrail-tool",
    "/aws/lambda/${var.name_prefix}-storage-tool"
  ]

  query_string = <<EOF
fields @timestamp, @message, correlation_id, service_name, operation
| filter ispresent(correlation_id)
| sort @timestamp asc
| stats count() by correlation_id, service_name
EOF
}

resource "aws_cloudwatch_query_definition" "performance_bottlenecks" {
  name = "${var.name_prefix}-performance-bottlenecks"

  log_group_names = [
    "/aws/lambda/${var.name_prefix}-feed-parser",
    "/aws/lambda/${var.name_prefix}-relevancy-evaluator",
    "/aws/lambda/${var.name_prefix}-dedup-tool"
  ]

  query_string = <<EOF
fields @timestamp, @duration, @billedDuration, @memorySize, @maxMemoryUsed, correlation_id
| filter @type = "REPORT" and @duration > 10000
| sort @duration desc
| limit 50
EOF
}

# EventBridge Rule for X-Ray Insights Notifications
resource "aws_cloudwatch_event_rule" "xray_insights" {
  count = var.enable_xray_insights_notifications ? 1 : 0

  name        = "${var.name_prefix}-xray-insights"
  description = "X-Ray Insights notifications"

  event_pattern = jsonencode({
    source      = ["aws.xray"]
    detail-type = ["X-Ray Insight"]
    detail = {
      state = ["ACTIVE"]
    }
  })

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-xray-insights-rule"
    Purpose = "X-Ray insights notifications"
  })
}

resource "aws_cloudwatch_event_target" "xray_insights_sns" {
  count = var.enable_xray_insights_notifications ? 1 : 0

  rule      = aws_cloudwatch_event_rule.xray_insights[0].name
  target_id = "XRayInsightsSNSTarget"
  arn       = var.alerts_topic_arn
}

# X-Ray Encryption Configuration
resource "aws_xray_encryption_config" "main" {
  type   = "KMS"
  key_id = var.kms_key_arn

  depends_on = [
    aws_xray_sampling_rule.correlation_id_high_priority,
    aws_xray_sampling_rule.agent_execution_tracing,
    aws_xray_sampling_rule.error_tracing
  ]
}