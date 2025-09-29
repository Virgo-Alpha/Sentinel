# Outputs for EventBridge Module

output "rule_arns" {
  description = "ARNs of all EventBridge rules"
  value = merge(
    {
      for category, rule in aws_cloudwatch_event_rule.feed_ingestion : 
      "${category}_ingestion" => rule.arn
    },
    {
      manual_trigger       = aws_cloudwatch_event_rule.manual_trigger.arn
      emergency_processing = aws_cloudwatch_event_rule.emergency_processing.arn
      daily_digest        = aws_cloudwatch_event_rule.daily_digest.arn
      weekly_summary      = aws_cloudwatch_event_rule.weekly_summary.arn
    }
  )
}

output "rule_names" {
  description = "Names of all EventBridge rules"
  value = merge(
    {
      for category, rule in aws_cloudwatch_event_rule.feed_ingestion : 
      "${category}_ingestion" => rule.name
    },
    {
      manual_trigger       = aws_cloudwatch_event_rule.manual_trigger.name
      emergency_processing = aws_cloudwatch_event_rule.emergency_processing.name
      daily_digest        = aws_cloudwatch_event_rule.daily_digest.name
      weekly_summary      = aws_cloudwatch_event_rule.weekly_summary.name
    }
  )
}

output "feed_ingestion_rule_arns" {
  description = "ARNs of feed ingestion rules by category"
  value = {
    for category, rule in aws_cloudwatch_event_rule.feed_ingestion : 
    category => rule.arn
  }
}

output "feed_ingestion_rule_names" {
  description = "Names of feed ingestion rules by category"
  value = {
    for category, rule in aws_cloudwatch_event_rule.feed_ingestion : 
    category => rule.name
  }
}

output "dlq_arn" {
  description = "ARN of EventBridge dead letter queue"
  value       = aws_sqs_queue.eventbridge_dlq.arn
}

output "dlq_url" {
  description = "URL of EventBridge dead letter queue"
  value       = aws_sqs_queue.eventbridge_dlq.url
}

output "execution_role_arn" {
  description = "ARN of EventBridge execution role"
  value       = aws_iam_role.eventbridge_execution.arn
}

output "execution_role_name" {
  description = "Name of EventBridge execution role"
  value       = aws_iam_role.eventbridge_execution.name
}

# Individual rule outputs for easier reference
output "advisories_rule_arn" {
  description = "ARN of advisories ingestion rule"
  value       = aws_cloudwatch_event_rule.feed_ingestion["advisories"].arn
}

output "alerts_rule_arn" {
  description = "ARN of alerts ingestion rule"
  value       = aws_cloudwatch_event_rule.feed_ingestion["alerts"].arn
}

output "vulnerabilities_rule_arn" {
  description = "ARN of vulnerabilities ingestion rule"
  value       = aws_cloudwatch_event_rule.feed_ingestion["vulnerabilities"].arn
}

output "manual_trigger_rule_arn" {
  description = "ARN of manual trigger rule"
  value       = aws_cloudwatch_event_rule.manual_trigger.arn
}

output "emergency_processing_rule_arn" {
  description = "ARN of emergency processing rule"
  value       = aws_cloudwatch_event_rule.emergency_processing.arn
}

output "daily_digest_rule_arn" {
  description = "ARN of daily digest rule"
  value       = aws_cloudwatch_event_rule.daily_digest.arn
}

output "weekly_summary_rule_arn" {
  description = "ARN of weekly summary rule"
  value       = aws_cloudwatch_event_rule.weekly_summary.arn
}

# Schedule information
output "feed_schedules" {
  description = "Feed processing schedules by category"
  value = {
    advisories      = "rate(30 minutes)"
    alerts         = "rate(15 minutes)"
    vulnerabilities = "rate(1 hour)"
    vendor         = "rate(2 hours)"
    threat_intel   = "rate(1 hour)"
    research       = "rate(4 hours)"
    news           = "rate(6 hours)"
    data_breach    = "rate(30 minutes)"
    policy         = "rate(12 hours)"
  }
}