# EventBridge Module for Sentinel Infrastructure
# Creates scheduled rules per feed category

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

# Local values for feed categories and schedules
locals {
  feed_schedules = {
    advisories = {
      schedule    = "rate(30 minutes)"
      description = "Process security advisories every 30 minutes"
      priority    = "high"
    }
    alerts = {
      schedule    = "rate(15 minutes)"
      description = "Process security alerts every 15 minutes"
      priority    = "high"
    }
    vulnerabilities = {
      schedule    = "rate(1 hour)"
      description = "Process vulnerability reports every hour"
      priority    = "medium"
    }
    vendor = {
      schedule    = "rate(2 hours)"
      description = "Process vendor security updates every 2 hours"
      priority    = "medium"
    }
    threat_intel = {
      schedule    = "rate(1 hour)"
      description = "Process threat intelligence every hour"
      priority    = "high"
    }
    research = {
      schedule    = "rate(4 hours)"
      description = "Process security research every 4 hours"
      priority    = "low"
    }
    news = {
      schedule    = "rate(6 hours)"
      description = "Process security news every 6 hours"
      priority    = "low"
    }
    data_breach = {
      schedule    = "rate(30 minutes)"
      description = "Process data breach reports every 30 minutes"
      priority    = "high"
    }
    policy = {
      schedule    = "rate(12 hours)"
      description = "Process policy updates every 12 hours"
      priority    = "low"
    }
  }
}

# EventBridge rules for each feed category
resource "aws_cloudwatch_event_rule" "feed_ingestion" {
  for_each = local.feed_schedules

  name                = "${var.name_prefix}-${each.key}-ingestion"
  description         = each.value.description
  schedule_expression = each.value.schedule
  state              = "ENABLED"

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-${each.key}-ingestion-rule"
    Category = each.key
    Priority = each.value.priority
  })
}

# EventBridge targets for Step Functions
resource "aws_cloudwatch_event_target" "step_functions" {
  for_each = local.feed_schedules

  rule      = aws_cloudwatch_event_rule.feed_ingestion[each.key].name
  target_id = "${var.name_prefix}-${each.key}-target"
  arn       = var.state_machine_arn
  role_arn  = aws_iam_role.eventbridge_execution.arn

  input = jsonencode({
    feedCategory     = each.key
    priority        = each.value.priority
    maxConcurrentFeeds = var.max_concurrent_feeds
    batchSize       = each.value.priority == "high" ? 20 : 10
    sessionId       = "${each.key}-$${aws.events.event.ingestion-time}"
    inputText       = "Process ${each.key} feeds with priority ${each.value.priority}"
  })

  # Retry configuration
  retry_policy {
    maximum_retry_attempts       = 3
    maximum_event_age_in_seconds = 3600
  }

  # Dead letter queue configuration
  dead_letter_config {
    arn = aws_sqs_queue.eventbridge_dlq.arn
  }
}

# Manual trigger rule for on-demand processing
resource "aws_cloudwatch_event_rule" "manual_trigger" {
  name        = "${var.name_prefix}-manual-trigger"
  description = "Manual trigger for on-demand feed processing"
  state       = "ENABLED"

  event_pattern = jsonencode({
    source      = ["sentinel.manual"]
    detail-type = ["Manual Feed Processing"]
  })

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-manual-trigger-rule"
    Purpose = "Manual feed processing"
  })
}

# Manual trigger target
resource "aws_cloudwatch_event_target" "manual_target" {
  rule      = aws_cloudwatch_event_rule.manual_trigger.name
  target_id = "${var.name_prefix}-manual-target"
  arn       = var.state_machine_arn
  role_arn  = aws_iam_role.eventbridge_execution.arn

  input_transformer {
    input_paths = {
      feedCategory = "$.detail.feedCategory"
      priority     = "$.detail.priority"
      batchSize    = "$.detail.batchSize"
    }
    input_template = jsonencode({
      "feedCategory" = "<feedCategory>"
      "priority"     = "<priority>"
      "batchSize"    = "<batchSize>"
      "sessionId"    = "manual-${aws.events.event.ingestion-time}"
      "inputText"    = "Manual processing of <feedCategory> feeds"
    })
  }

  retry_policy {
    maximum_retry_attempts       = 3
    maximum_event_age_in_seconds = 3600
  }

  dead_letter_config {
    arn = aws_sqs_queue.eventbridge_dlq.arn
  }
}

# Emergency processing rule for high-priority alerts
resource "aws_cloudwatch_event_rule" "emergency_processing" {
  name        = "${var.name_prefix}-emergency-processing"
  description = "Emergency processing for critical security alerts"
  state       = "ENABLED"

  event_pattern = jsonencode({
    source      = ["sentinel.emergency"]
    detail-type = ["Emergency Security Alert"]
  })

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-emergency-processing-rule"
    Purpose = "Emergency alert processing"
  })
}

# Emergency processing target
resource "aws_cloudwatch_event_target" "emergency_target" {
  rule      = aws_cloudwatch_event_rule.emergency_processing.name
  target_id = "${var.name_prefix}-emergency-target"
  arn       = var.state_machine_arn
  role_arn  = aws_iam_role.eventbridge_execution.arn

  input = jsonencode({
    feedCategory       = "emergency"
    priority          = "critical"
    maxConcurrentFeeds = var.max_concurrent_feeds * 2
    batchSize         = 50
    sessionId         = "emergency-$${aws.events.event.ingestion-time}"
    inputText         = "Emergency processing of critical security alerts"
  })

  retry_policy {
    maximum_retry_attempts       = 5
    maximum_event_age_in_seconds = 1800  # 30 minutes
  }

  dead_letter_config {
    arn = aws_sqs_queue.eventbridge_dlq.arn
  }
}

# Daily digest rule
resource "aws_cloudwatch_event_rule" "daily_digest" {
  name                = "${var.name_prefix}-daily-digest"
  description         = "Daily digest generation and email"
  schedule_expression = "cron(0 8 * * ? *)"  # 8 AM UTC daily
  state              = "ENABLED"

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-daily-digest-rule"
    Purpose = "Daily digest generation"
  })
}

# Daily digest target (Lambda function)
resource "aws_cloudwatch_event_target" "daily_digest_target" {
  rule      = aws_cloudwatch_event_rule.daily_digest.name
  target_id = "${var.name_prefix}-daily-digest-target"
  arn       = var.notifier_lambda_arn
  
  input = jsonencode({
    notification_type = "daily_digest"
    time_range       = "24h"
  })
}

# Lambda permission for daily digest
resource "aws_lambda_permission" "daily_digest_permission" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = var.notifier_lambda_arn
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_digest.arn
}

# Weekly summary rule
resource "aws_cloudwatch_event_rule" "weekly_summary" {
  name                = "${var.name_prefix}-weekly-summary"
  description         = "Weekly summary generation and email"
  schedule_expression = "cron(0 9 ? * MON *)"  # 9 AM UTC every Monday
  state              = "ENABLED"

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-weekly-summary-rule"
    Purpose = "Weekly summary generation"
  })
}

# Weekly summary target
resource "aws_cloudwatch_event_target" "weekly_summary_target" {
  rule      = aws_cloudwatch_event_rule.weekly_summary.name
  target_id = "${var.name_prefix}-weekly-summary-target"
  arn       = var.notifier_lambda_arn
  
  input = jsonencode({
    notification_type = "weekly_summary"
    time_range       = "7d"
  })
}

# Lambda permission for weekly summary
resource "aws_lambda_permission" "weekly_summary_permission" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = var.notifier_lambda_arn
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.weekly_summary.arn
}

# Dead letter queue for EventBridge failures
resource "aws_sqs_queue" "eventbridge_dlq" {
  name = "${var.name_prefix}-eventbridge-dlq"

  message_retention_seconds = 1209600  # 14 days
  kms_master_key_id        = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-eventbridge-dlq"
    Purpose = "EventBridge failed events"
  })
}

# IAM role for EventBridge execution
resource "aws_iam_role" "eventbridge_execution" {
  name = "${var.name_prefix}-eventbridge-execution-role"

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
    Name    = "${var.name_prefix}-eventbridge-execution-role"
    Purpose = "EventBridge rule execution"
  })
}

# IAM policy for EventBridge execution
resource "aws_iam_role_policy" "eventbridge_execution" {
  name = "${var.name_prefix}-eventbridge-execution-policy"
  role = aws_iam_role.eventbridge_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = var.state_machine_arn
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = var.notifier_lambda_arn
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = aws_sqs_queue.eventbridge_dlq.arn
      }
    ]
  })
}

# CloudWatch Alarms for EventBridge monitoring
resource "aws_cloudwatch_metric_alarm" "eventbridge_failed_invocations" {
  alarm_name          = "${var.name_prefix}-eventbridge-failed-invocations"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "FailedInvocations"
  namespace           = "AWS/Events"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "This metric monitors failed EventBridge invocations"
  alarm_actions       = var.alarm_topic_arn != null ? [var.alarm_topic_arn] : []

  dimensions = {
    RuleName = aws_cloudwatch_event_rule.feed_ingestion["advisories"].name
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-eventbridge-failed-invocations-alarm"
  })
}