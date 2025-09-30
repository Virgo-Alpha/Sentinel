# Monitoring Module for Sentinel Infrastructure
# Creates CloudWatch dashboards, X-Ray, and alerting

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

# Main CloudWatch Dashboard with Business Metrics
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.name_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      # Business Metrics Row 1
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 6
        height = 6

        properties = {
          metrics = [
            ["Sentinel/Business", "ArticlesIngested", "Source", "RSS"],
            [".", "ArticlesProcessed", ".", "."],
            [".", "ArticlesPublished", ".", "."],
            [".", "ArticlesReviewed", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Article Processing Pipeline"
          period  = 300
          stat    = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 6
        y      = 0
        width  = 6
        height = 6

        properties = {
          metrics = [
            ["Sentinel/Business", "RelevancyRate", "Agent", "RelevancyEvaluator"],
            [".", "DeduplicationRate", "Agent", "DedupTool"],
            [".", "PublishReviewRatio", "Pipeline", "Triage"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Processing Quality Metrics"
          period  = 300
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 6
        height = 6

        properties = {
          metrics = [
            ["Sentinel/Business", "KeywordHits", "Category", "CloudPlatforms"],
            [".", "KeywordHits", "Category", "SecurityVendors"],
            [".", "KeywordHits", "Category", "EnterpriseTools"],
            [".", "TotalKeywordHits", "Pipeline", "All"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Keyword Hit Statistics"
          period  = 300
          stat    = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 18
        y      = 0
        width  = 6
        height = 6

        properties = {
          metrics = [
            ["Sentinel/Business", "FeedHealthScore", "Feed", "ANSSI"],
            [".", "FeedHealthScore", "Feed", "CISA"],
            [".", "FeedHealthScore", "Feed", "NCSC"],
            [".", "FeedHealthScore", "Feed", "Microsoft"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Feed Health Monitoring"
          period  = 300
          stat    = "Average"
        }
      },
      # Lambda Performance Row 2
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", var.lambda_function_names["feed_parser"]],
            [".", "Duration", ".", "."],
            [".", "Errors", ".", "."],
            [".", "Throttles", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Feed Parser Lambda Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", var.lambda_function_names["relevancy_evaluator"]],
            [".", "Duration", ".", "."],
            [".", "Errors", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Relevancy Evaluator Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", var.articles_table_name],
            [".", "ConsumedWriteCapacityUnits", ".", "."],
            [".", "ItemCount", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Articles Table Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 6
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["AWS/States", "ExecutionsStarted", "StateMachineArn", var.state_machine_arn],
            [".", "ExecutionsSucceeded", ".", "."],
            [".", "ExecutionsFailed", ".", "."],
            [".", "ExecutionTime", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Step Functions Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 6
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["AWS/SQS", "NumberOfMessagesSent", "QueueName", "${var.name_prefix}-ingestion-queue"],
            [".", "NumberOfMessagesReceived", ".", "."],
            [".", "ApproximateNumberOfVisibleMessages", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "SQS Queue Metrics"
          period  = 300
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 12
        width  = 24
        height = 6

        properties = {
          query   = "SOURCE '/aws/lambda/${var.name_prefix}-feed-parser' | fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20"
          region  = data.aws_region.current.name
          title   = "Recent Lambda Errors"
          view    = "table"
        }
      }
    ]
  })
}

# Business Intelligence Dashboard
resource "aws_cloudwatch_dashboard" "business_intelligence" {
  dashboard_name = "${var.name_prefix}-business-intelligence"

  dashboard_body = jsonencode({
    widgets = [
      # Ingestion Rates
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["Sentinel/Business", "IngestionRate", "Feed", "ANSSI"],
            [".", "IngestionRate", "Feed", "CISA"],
            [".", "IngestionRate", "Feed", "NCSC"],
            [".", "IngestionRate", "Feed", "Microsoft"],
            [".", "IngestionRate", "Feed", "GoogleTAG"],
            [".", "IngestionRate", "Feed", "Mandiant"]
          ]
          view    = "timeSeries"
          stacked = true
          region  = data.aws_region.current.name
          title   = "Article Ingestion Rates by Feed"
          period  = 300
          stat    = "Sum"
        }
      },
      # Relevancy and Deduplication Rates
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["Sentinel/Business", "RelevancyRate", "Agent", "RelevancyEvaluator"],
            [".", "DeduplicationRate", "Agent", "DedupTool"],
            [".", "GuardrailPassRate", "Agent", "GuardrailTool"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Processing Quality Rates"
          period  = 300
          stat    = "Average"
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },
      # Publish vs Review Ratios
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["Sentinel/Business", "ArticlesAutoPublished", "Pipeline", "Triage"],
            [".", "ArticlesForReview", "Pipeline", "Triage"],
            [".", "ArticlesDropped", "Pipeline", "Triage"]
          ]
          view    = "timeSeries"
          stacked = true
          region  = data.aws_region.current.name
          title   = "Triage Decision Distribution"
          period  = 300
          stat    = "Sum"
        }
      },
      # Keyword Hit Statistics
      {
        type   = "metric"
        x      = 8
        y      = 6
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["Sentinel/Business", "KeywordHits", "Category", "CloudPlatforms"],
            [".", "KeywordHits", "Category", "SecurityVendors"],
            [".", "KeywordHits", "Category", "EnterpriseTools"],
            [".", "KeywordHits", "Category", "ThreatIntel"]
          ]
          view    = "timeSeries"
          stacked = true
          region  = data.aws_region.current.name
          title   = "Keyword Hits by Category"
          period  = 300
          stat    = "Sum"
        }
      },
      # Processing Time Distribution
      {
        type   = "metric"
        x      = 16
        y      = 6
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["Sentinel/Business", "ProcessingLatency", "Stage", "Ingestion"],
            [".", "ProcessingLatency", "Stage", "Relevancy"],
            [".", "ProcessingLatency", "Stage", "Deduplication"],
            [".", "ProcessingLatency", "Stage", "Triage"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "End-to-End Processing Latency"
          period  = 300
          stat    = "Average"
        }
      },
      # Top Keywords Trending
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["Sentinel/Business", "KeywordTrending", "Keyword", "AWS"],
            [".", "KeywordTrending", "Keyword", "Microsoft365"],
            [".", "KeywordTrending", "Keyword", "Azure"],
            [".", "KeywordTrending", "Keyword", "Fortinet"],
            [".", "KeywordTrending", "Keyword", "SentinelOne"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Trending Keywords"
          period  = 900
          stat    = "Sum"
        }
      },
      # A/B Testing Metrics
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["Sentinel/ABTesting", "PromptPrecision", "Variant", "A"],
            [".", "PromptPrecision", "Variant", "B"],
            [".", "PromptLatency", "Variant", "A"],
            [".", "PromptLatency", "Variant", "B"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "A/B Testing: Prompt Performance"
          period  = 300
          stat    = "Average"
        }
      }
    ]
  })
}

# Cost Tracking Dashboard
resource "aws_cloudwatch_dashboard" "cost_tracking" {
  dashboard_name = "${var.name_prefix}-cost-tracking"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["Sentinel/Cost", "LambdaCost", "Service", "FeedParser"],
            [".", "LambdaCost", "Service", "RelevancyEvaluator"],
            [".", "LambdaCost", "Service", "DedupTool"],
            [".", "LambdaCost", "Service", "GuardrailTool"]
          ]
          view    = "timeSeries"
          stacked = true
          region  = data.aws_region.current.name
          title   = "Lambda Costs by Service"
          period  = 3600
          stat    = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 0
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["Sentinel/Cost", "BedrockCost", "Model", "Claude"],
            [".", "DynamoDBCost", "Table", "Articles"],
            [".", "S3Cost", "Bucket", "RawContent"],
            [".", "OpenSearchCost", "Collection", "Articles"]
          ]
          view    = "timeSeries"
          stacked = true
          region  = data.aws_region.current.name
          title   = "Infrastructure Costs"
          period  = 3600
          stat    = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 0
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["Sentinel/Cost", "CostPerArticle", "Pipeline", "Total"],
            [".", "CostPerKeywordHit", "Pipeline", "Total"],
            [".", "CostPerPublishedArticle", "Pipeline", "Total"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Cost Efficiency Metrics"
          period  = 3600
          stat    = "Average"
        }
      }
    ]
  })
}

# SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.name_prefix}-alerts"
  
  kms_master_key_id = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-alerts-topic"
    Purpose = "System alerts and notifications"
  })
}

# SNS Topic for Critical Alerts (DLQ, Security, etc.)
resource "aws_sns_topic" "critical_alerts" {
  name = "${var.name_prefix}-critical-alerts"
  
  kms_master_key_id = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-critical-alerts-topic"
    Purpose = "Critical system alerts requiring immediate attention"
  })
}

# SNS Topic Policy
resource "aws_sns_topic_policy" "alerts" {
  arn = aws_sns_topic.alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudWatchAlarmsToPublish"
        Effect = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
        Action = "sns:Publish"
        Resource = aws_sns_topic.alerts.arn
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

# SNS Topic Subscriptions for Alert Emails
resource "aws_sns_topic_subscription" "email_alerts" {
  for_each = toset(var.alert_emails)

  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = each.value
}

# SNS Topic Subscriptions for Critical Alert Emails
resource "aws_sns_topic_subscription" "critical_email_alerts" {
  for_each = toset(var.critical_alert_emails)

  topic_arn = aws_sns_topic.critical_alerts.arn
  protocol  = "email"
  endpoint  = each.value
}

# SNS Topic Subscriptions for Slack (if configured)
resource "aws_sns_topic_subscription" "slack_alerts" {
  count = var.slack_webhook_url != "" ? 1 : 0

  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "https"
  endpoint  = var.slack_webhook_url
}

# CloudWatch Alarms

# Lambda Error Rate Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_error_rate" {
  for_each = var.lambda_function_names

  alarm_name          = "${var.name_prefix}-${each.key}-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors error rate for ${each.key}"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = each.value
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-${each.key}-error-rate-alarm"
    Function = each.key
  })
}

# DynamoDB Throttle Alarm
resource "aws_cloudwatch_metric_alarm" "dynamodb_throttles" {
  alarm_name          = "${var.name_prefix}-dynamodb-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors DynamoDB throttles"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    TableName = var.articles_table_name
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-dynamodb-throttles-alarm"
  })
}

# Step Functions Failed Executions Alarm
resource "aws_cloudwatch_metric_alarm" "step_functions_failures" {
  alarm_name          = "${var.name_prefix}-step-functions-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors Step Functions failures"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    StateMachineArn = var.state_machine_arn
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-step-functions-failures-alarm"
  })
}

# High Memory Usage Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_memory_usage" {
  for_each = var.lambda_function_names

  alarm_name          = "${var.name_prefix}-${each.key}-memory-usage"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "240000"  # 4 minutes in milliseconds
  alarm_description   = "This metric monitors memory usage for ${each.key}"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = each.value
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-${each.key}-memory-usage-alarm"
    Function = each.key
  })
}

# Cost Anomaly Detection
resource "aws_ce_anomaly_detector" "main" {
  name         = "${var.name_prefix}-cost-anomaly-detector"
  monitor_type = "DIMENSIONAL"

  specification = jsonencode({
    Dimension = "SERVICE"
    MatchOptions = ["EQUALS"]
    Values = ["Amazon DynamoDB", "AWS Lambda", "Amazon Simple Storage Service"]
  })

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-cost-anomaly-detector"
    Purpose = "Cost monitoring"
  })
}

# Cost Anomaly Subscription
resource "aws_ce_anomaly_subscription" "main" {
  name      = "${var.name_prefix}-cost-anomaly-subscription"
  frequency = "DAILY"
  
  monitor_arn_list = [
    aws_ce_anomaly_detector.main.arn
  ]
  
  subscriber {
    type    = "EMAIL"
    address = length(var.alert_emails) > 0 ? var.alert_emails[0] : "admin@example.com"
  }

  threshold_expression {
    and {
      dimension {
        key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
        values        = ["100"]
        match_options = ["GREATER_THAN_OR_EQUAL"]
      }
    }
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-cost-anomaly-subscription"
    Purpose = "Cost anomaly alerts"
  })
}

# X-Ray Sampling Rules for different service tiers
resource "aws_xray_sampling_rule" "high_priority" {
  rule_name      = "${var.name_prefix}-high-priority-sampling"
  priority       = 1000
  version        = 1
  reservoir_size = 2
  fixed_rate     = 0.5
  url_path       = "*"
  host           = "*"
  http_method    = "*"
  service_type   = "*"
  service_name   = "${var.name_prefix}-*"
  resource_arn   = "*"

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-xray-high-priority-sampling"
    Purpose = "High priority X-Ray trace sampling for Sentinel services"
  })
}

resource "aws_xray_sampling_rule" "agent_tools" {
  rule_name      = "${var.name_prefix}-agent-tools-sampling"
  priority       = 2000
  version        = 1
  reservoir_size = 1
  fixed_rate     = 0.3
  url_path       = "*"
  host           = "*"
  http_method    = "*"
  service_type   = "*"
  service_name   = "*agent*"
  resource_arn   = "*"

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-xray-agent-tools-sampling"
    Purpose = "Agent tool X-Ray trace sampling"
  })
}

resource "aws_xray_sampling_rule" "default" {
  rule_name      = "${var.name_prefix}-default-sampling"
  priority       = 9000
  version        = 1
  reservoir_size = 1
  fixed_rate     = 0.1
  url_path       = "*"
  host           = "*"
  http_method    = "*"
  service_type   = "*"
  service_name   = "*"
  resource_arn   = "*"

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-xray-default-sampling"
    Purpose = "Default X-Ray trace sampling"
  })
}

# CloudWatch Log Groups for centralized logging
resource "aws_cloudwatch_log_group" "application_logs" {
  name              = "/sentinel/${var.name_prefix}/application"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-application-logs"
    Purpose = "Centralized application logging"
  })
}

# CloudWatch Log Metric Filters
resource "aws_cloudwatch_log_metric_filter" "error_count" {
  name           = "${var.name_prefix}-error-count"
  log_group_name = aws_cloudwatch_log_group.application_logs.name
  pattern        = "[timestamp, request_id, level=\"ERROR\", ...]"

  metric_transformation {
    name      = "${var.name_prefix}-ErrorCount"
    namespace = "Sentinel/Application"
    value     = "1"
  }
}

resource "aws_cloudwatch_log_metric_filter" "processing_time" {
  name           = "${var.name_prefix}-processing-time"
  log_group_name = aws_cloudwatch_log_group.application_logs.name
  pattern        = "[timestamp, request_id, level, message=\"Processing completed\", duration]"

  metric_transformation {
    name      = "${var.name_prefix}-ProcessingTime"
    namespace = "Sentinel/Application"
    value     = "$duration"
  }
}

# DLQ Alarms for each service
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  for_each = var.dlq_names

  alarm_name          = "${var.name_prefix}-${each.key}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfVisibleMessages"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Maximum"
  threshold           = "0"
  alarm_description   = "Messages in DLQ for ${each.key} - immediate attention required"
  alarm_actions       = [aws_sns_topic.alerts.arn, aws_sns_topic.critical_alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = each.value
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-${each.key}-dlq-alarm"
    Severity = "Critical"
    Service  = each.key
  })
}

# Business Logic Alarms
resource "aws_cloudwatch_metric_alarm" "articles_processed_rate" {
  alarm_name          = "${var.name_prefix}-articles-processed-rate"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "ArticlesProcessed"
  namespace           = "Sentinel/Business"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "Article processing rate has dropped below threshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "breaching"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-articles-processed-rate-alarm"
  })
}

resource "aws_cloudwatch_metric_alarm" "relevancy_rate_low" {
  alarm_name          = "${var.name_prefix}-relevancy-rate-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "RelevancyRate"
  namespace           = "Sentinel/Business"
  period              = "900"
  statistic           = "Average"
  threshold           = "60"
  alarm_description   = "Relevancy rate has dropped below 60%"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    Agent = "RelevancyEvaluator"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-relevancy-rate-low-alarm"
  })
}

resource "aws_cloudwatch_metric_alarm" "deduplication_rate_low" {
  alarm_name          = "${var.name_prefix}-deduplication-rate-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "DeduplicationRate"
  namespace           = "Sentinel/Business"
  period              = "900"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "Deduplication rate has dropped below 85%"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    Agent = "DedupTool"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-deduplication-rate-low-alarm"
  })
}

resource "aws_cloudwatch_metric_alarm" "keyword_hit_anomaly" {
  alarm_name          = "${var.name_prefix}-keyword-hit-anomaly"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  datapoints_to_alarm = "2"
  metric_name         = "TotalKeywordHits"
  namespace           = "Sentinel/Business"
  period              = "900"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Keyword hits have dropped significantly - possible feed or keyword issues"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    Pipeline = "All"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-keyword-hit-anomaly-alarm"
  })
}

resource "aws_cloudwatch_metric_alarm" "processing_latency_high" {
  alarm_name          = "${var.name_prefix}-processing-latency-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ProcessingLatency"
  namespace           = "Sentinel/Business"
  period              = "300"
  statistic           = "Average"
  threshold           = "300000"  # 5 minutes in milliseconds
  alarm_description   = "End-to-end processing latency exceeds 5 minutes"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-processing-latency-high-alarm"
  })
}

# Cost Anomaly Alarms
resource "aws_cloudwatch_metric_alarm" "cost_spike" {
  alarm_name          = "${var.name_prefix}-cost-spike"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "CostPerArticle"
  namespace           = "Sentinel/Cost"
  period              = "3600"
  statistic           = "Average"
  threshold           = "0.10"  # $0.10 per article
  alarm_description   = "Cost per article has spiked above threshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    Pipeline = "Total"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-cost-spike-alarm"
  })
}

# CloudWatch Insights Queries (saved for easy access)
resource "aws_cloudwatch_query_definition" "error_analysis" {
  name = "${var.name_prefix}-error-analysis"

  log_group_names = [
    "/aws/lambda/${var.name_prefix}-feed-parser",
    "/aws/lambda/${var.name_prefix}-relevancy-evaluator",
    "/aws/lambda/${var.name_prefix}-dedup-tool"
  ]

  query_string = <<EOF
fields @timestamp, @message, @requestId
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100
EOF
}

resource "aws_cloudwatch_query_definition" "performance_analysis" {
  name = "${var.name_prefix}-performance-analysis"

  log_group_names = [
    "/aws/lambda/${var.name_prefix}-feed-parser",
    "/aws/lambda/${var.name_prefix}-relevancy-evaluator"
  ]

  query_string = <<EOF
fields @timestamp, @duration, @billedDuration, @memorySize, @maxMemoryUsed
| filter @type = "REPORT"
| sort @timestamp desc
| limit 100
EOF
}

resource "aws_cloudwatch_query_definition" "correlation_id_tracing" {
  name = "${var.name_prefix}-correlation-id-tracing"

  log_group_names = [
    "/aws/lambda/${var.name_prefix}-feed-parser",
    "/aws/lambda/${var.name_prefix}-relevancy-evaluator",
    "/aws/lambda/${var.name_prefix}-dedup-tool",
    "/aws/lambda/${var.name_prefix}-guardrail-tool"
  ]

  query_string = <<EOF
fields @timestamp, @message, @requestId, correlation_id
| filter ispresent(correlation_id)
| sort @timestamp desc
| limit 100
EOF
}

resource "aws_cloudwatch_query_definition" "keyword_analysis" {
  name = "${var.name_prefix}-keyword-analysis"

  log_group_names = [
    aws_cloudwatch_log_group.application_logs.name
  ]

  query_string = <<EOF
fields @timestamp, keyword, hit_count, feed_source, article_id
| filter @message like /KEYWORD_HIT/
| stats sum(hit_count) as total_hits by keyword
| sort total_hits desc
| limit 50
EOF
}

resource "aws_cloudwatch_query_definition" "ab_testing_analysis" {
  name = "${var.name_prefix}-ab-testing-analysis"

  log_group_names = [
    aws_cloudwatch_log_group.application_logs.name
  ]

  query_string = <<EOF
fields @timestamp, prompt_variant, precision, latency, success_rate
| filter @message like /AB_TEST/
| stats avg(precision) as avg_precision, avg(latency) as avg_latency, avg(success_rate) as avg_success by prompt_variant
| sort avg_precision desc
EOF
}

# EventBridge Rule for Keyword Trending Analysis
resource "aws_cloudwatch_event_rule" "keyword_analysis" {
  name                = "${var.name_prefix}-keyword-analysis"
  description         = "Trigger keyword trending analysis"
  schedule_expression = "rate(1 hour)"

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-keyword-analysis-rule"
    Purpose = "Automated keyword trending analysis"
  })
}

# Lambda for Keyword Trending Analysis (placeholder - would be implemented separately)
resource "aws_lambda_permission" "allow_eventbridge_keyword_analysis" {
  count = var.keyword_analysis_lambda_arn != "" ? 1 : 0

  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = var.keyword_analysis_lambda_arn
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.keyword_analysis.arn
}

resource "aws_cloudwatch_event_target" "keyword_analysis_lambda" {
  count = var.keyword_analysis_lambda_arn != "" ? 1 : 0

  rule      = aws_cloudwatch_event_rule.keyword_analysis.name
  target_id = "KeywordAnalysisLambdaTarget"
  arn       = var.keyword_analysis_lambda_arn
}

# Custom Metric Filters for Business Logic
resource "aws_cloudwatch_log_metric_filter" "ingestion_rate" {
  name           = "${var.name_prefix}-ingestion-rate"
  log_group_name = aws_cloudwatch_log_group.application_logs.name
  pattern        = "[timestamp, request_id, level, message=\"ARTICLE_INGESTED\", feed, article_id]"

  metric_transformation {
    name      = "IngestionRate"
    namespace = "Sentinel/Business"
    value     = "1"
    default_value = "0"
    
    dimensions = {
      Feed = "$feed"
    }
  }
}

resource "aws_cloudwatch_log_metric_filter" "relevancy_rate" {
  name           = "${var.name_prefix}-relevancy-rate"
  log_group_name = aws_cloudwatch_log_group.application_logs.name
  pattern        = "[timestamp, request_id, level, message=\"RELEVANCY_ASSESSED\", score, is_relevant]"

  metric_transformation {
    name      = "RelevancyRate"
    namespace = "Sentinel/Business"
    value     = "$is_relevant"
    default_value = "0"
    
    dimensions = {
      Agent = "RelevancyEvaluator"
    }
  }
}

resource "aws_cloudwatch_log_metric_filter" "deduplication_rate" {
  name           = "${var.name_prefix}-deduplication-rate"
  log_group_name = aws_cloudwatch_log_group.application_logs.name
  pattern        = "[timestamp, request_id, level, message=\"DEDUPLICATION_COMPLETED\", is_duplicate, cluster_id]"

  metric_transformation {
    name      = "DeduplicationRate"
    namespace = "Sentinel/Business"
    value     = "$is_duplicate"
    default_value = "0"
    
    dimensions = {
      Agent = "DedupTool"
    }
  }
}

resource "aws_cloudwatch_log_metric_filter" "keyword_hits" {
  name           = "${var.name_prefix}-keyword-hits"
  log_group_name = aws_cloudwatch_log_group.application_logs.name
  pattern        = "[timestamp, request_id, level, message=\"KEYWORD_HIT\", keyword, category, hit_count]"

  metric_transformation {
    name      = "KeywordHits"
    namespace = "Sentinel/Business"
    value     = "$hit_count"
    default_value = "0"
    
    dimensions = {
      Category = "$category"
      Keyword  = "$keyword"
    }
  }
}

resource "aws_cloudwatch_log_metric_filter" "triage_decisions" {
  name           = "${var.name_prefix}-triage-decisions"
  log_group_name = aws_cloudwatch_log_group.application_logs.name
  pattern        = "[timestamp, request_id, level, message=\"TRIAGE_DECISION\", decision, article_id]"

  metric_transformation {
    name      = "TriageDecisions"
    namespace = "Sentinel/Business"
    value     = "1"
    default_value = "0"
    
    dimensions = {
      Decision = "$decision"
      Pipeline = "Triage"
    }
  }
}

resource "aws_cloudwatch_log_metric_filter" "processing_latency" {
  name           = "${var.name_prefix}-processing-latency"
  log_group_name = aws_cloudwatch_log_group.application_logs.name
  pattern        = "[timestamp, request_id, level, message=\"PROCESSING_COMPLETED\", stage, latency_ms]"

  metric_transformation {
    name      = "ProcessingLatency"
    namespace = "Sentinel/Business"
    value     = "$latency_ms"
    default_value = "0"
    
    dimensions = {
      Stage = "$stage"
    }
  }
}

resource "aws_cloudwatch_log_metric_filter" "ab_testing_metrics" {
  name           = "${var.name_prefix}-ab-testing-metrics"
  log_group_name = aws_cloudwatch_log_group.application_logs.name
  pattern        = "[timestamp, request_id, level, message=\"AB_TEST\", variant, metric_name, metric_value]"

  metric_transformation {
    name      = "ABTestingMetrics"
    namespace = "Sentinel/ABTesting"
    value     = "$metric_value"
    default_value = "0"
    
    dimensions = {
      Variant    = "$variant"
      MetricName = "$metric_name"
    }
  }
}