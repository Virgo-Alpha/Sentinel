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

# Additional Dashboard URLs
output "business_intelligence_dashboard_url" {
  description = "URL of Business Intelligence CloudWatch dashboard"
  value       = "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.business_intelligence.dashboard_name}"
}

output "cost_tracking_dashboard_url" {
  description = "URL of Cost Tracking CloudWatch dashboard"
  value       = "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.cost_tracking.dashboard_name}"
}

output "critical_alerts_topic_arn" {
  description = "ARN of SNS critical alerts topic"
  value       = aws_sns_topic.critical_alerts.arn
}

output "xray_sampling_rules" {
  description = "X-Ray sampling rule ARNs"
  value = {
    high_priority = aws_xray_sampling_rule.high_priority.arn
    agent_tools   = aws_xray_sampling_rule.agent_tools.arn
    default       = aws_xray_sampling_rule.default.arn
  }
}

# Enhanced Alarm ARNs
output "business_alarm_arns" {
  description = "ARNs of business logic CloudWatch alarms"
  value = {
    articles_processed_rate = aws_cloudwatch_metric_alarm.articles_processed_rate.arn
    relevancy_rate_low     = aws_cloudwatch_metric_alarm.relevancy_rate_low.arn
    deduplication_rate_low = aws_cloudwatch_metric_alarm.deduplication_rate_low.arn
    keyword_hit_anomaly    = aws_cloudwatch_metric_alarm.keyword_hit_anomaly.arn
    processing_latency_high = aws_cloudwatch_metric_alarm.processing_latency_high.arn
    cost_spike             = aws_cloudwatch_metric_alarm.cost_spike.arn
  }
}

output "dlq_alarm_arns" {
  description = "ARNs of DLQ CloudWatch alarms"
  value = {
    for name, alarm in aws_cloudwatch_metric_alarm.dlq_messages :
    name => alarm.arn
  }
}

# Enhanced Query definitions
output "enhanced_query_definitions" {
  description = "Enhanced CloudWatch Insights query definitions"
  value = {
    error_analysis         = aws_cloudwatch_query_definition.error_analysis.name
    performance_analysis   = aws_cloudwatch_query_definition.performance_analysis.name
    correlation_id_tracing = aws_cloudwatch_query_definition.correlation_id_tracing.name
    keyword_analysis       = aws_cloudwatch_query_definition.keyword_analysis.name
    ab_testing_analysis    = aws_cloudwatch_query_definition.ab_testing_analysis.name
  }
}

# Monitoring configuration summary
output "monitoring_config" {
  description = "Enhanced monitoring configuration summary"
  value = {
    main_dashboard_name              = aws_cloudwatch_dashboard.main.dashboard_name
    business_intelligence_dashboard  = aws_cloudwatch_dashboard.business_intelligence.dashboard_name
    cost_tracking_dashboard         = aws_cloudwatch_dashboard.cost_tracking.dashboard_name
    alerts_topic_arn               = aws_sns_topic.alerts.arn
    critical_alerts_topic_arn      = aws_sns_topic.critical_alerts.arn
    log_retention_days             = var.log_retention_days
    detailed_monitoring            = var.enable_detailed_monitoring
    alert_email_count              = length(var.alert_emails)
    critical_alert_email_count     = length(var.critical_alert_emails)
    xray_sampling_rates = {
      high_priority = 0.5
      agent_tools   = 0.3
      default       = 0.1
    }
    cost_monitoring_enabled        = true
    ab_testing_enabled            = var.enable_ab_testing
    dlq_monitoring_enabled        = length(var.dlq_names) > 0
    slack_integration_enabled     = var.slack_webhook_url != ""
    business_metrics_enabled      = true
    keyword_analysis_enabled      = var.keyword_analysis_lambda_arn != ""
  }
  sensitive = false
}