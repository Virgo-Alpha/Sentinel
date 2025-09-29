# Outputs for Monitoring Module

output "dashboard_url" {
  description = "URL of CloudWatch dashboard"
  value       = "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

output "dashboard_name" {
  description = "Name of CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}

output "dashboard_arn" {
  description = "ARN of CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_arn
}

output "alerts_topic_arn" {
  description = "ARN of SNS alerts topic"
  value       = aws_sns_topic.alerts.arn
}

output "alerts_topic_name" {
  description = "Name of SNS alerts topic"
  value       = aws_sns_topic.alerts.name
}

output "cost_anomaly_detector_arn" {
  description = "ARN of cost anomaly detector"
  value       = aws_ce_anomaly_detector.main.arn
}

output "xray_sampling_rule_arn" {
  description = "ARN of X-Ray sampling rule"
  value       = aws_xray_sampling_rule.main.arn
}

output "application_log_group_name" {
  description = "Name of application log group"
  value       = aws_cloudwatch_log_group.application_logs.name
}

output "application_log_group_arn" {
  description = "ARN of application log group"
  value       = aws_cloudwatch_log_group.application_logs.arn
}

# Alarm ARNs for reference
output "alarm_arns" {
  description = "ARNs of all CloudWatch alarms"
  value = merge(
    {
      for name, alarm in aws_cloudwatch_metric_alarm.lambda_error_rate :
      "${name}_error_rate" => alarm.arn
    },
    {
      for name, alarm in aws_cloudwatch_metric_alarm.lambda_memory_usage :
      "${name}_memory_usage" => alarm.arn
    },
    {
      dynamodb_throttles      = aws_cloudwatch_metric_alarm.dynamodb_throttles.arn
      step_functions_failures = aws_cloudwatch_metric_alarm.step_functions_failures.arn
      articles_processed_rate = aws_cloudwatch_metric_alarm.articles_processed_rate.arn
    }
  )
}

# Query definitions for CloudWatch Insights
output "query_definitions" {
  description = "CloudWatch Insights query definitions"
  value = {
    error_analysis       = aws_cloudwatch_query_definition.error_analysis.name
    performance_analysis = aws_cloudwatch_query_definition.performance_analysis.name
  }
}

# Monitoring configuration summary
output "monitoring_config" {
  description = "Monitoring configuration summary"
  value = {
    dashboard_name          = aws_cloudwatch_dashboard.main.dashboard_name
    alerts_topic_arn       = aws_sns_topic.alerts.arn
    log_retention_days     = var.log_retention_days
    detailed_monitoring    = var.enable_detailed_monitoring
    alert_email_count      = length(var.alert_emails)
    xray_sampling_rate     = 0.1
    cost_monitoring_enabled = true
  }
  sensitive = false
}