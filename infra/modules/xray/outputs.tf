# Outputs for X-Ray Distributed Tracing Module

output "xray_service_map_arn" {
  description = "ARN of X-Ray service map group"
  value       = aws_xray_group.sentinel_service_map.arn
}

output "xray_groups" {
  description = "X-Ray group ARNs"
  value = {
    service_map        = aws_xray_group.sentinel_service_map.arn
    agent_tools        = aws_xray_group.agent_tools.arn
    ingestion_pipeline = aws_xray_group.ingestion_pipeline.arn
    human_workflow     = aws_xray_group.human_workflow.arn
    errors_and_failures = aws_xray_group.errors_and_failures.arn
  }
}

output "xray_sampling_rules" {
  description = "X-Ray sampling rule ARNs"
  value = {
    correlation_id_high_priority = aws_xray_sampling_rule.correlation_id_high_priority.arn
    agent_execution_tracing     = aws_xray_sampling_rule.agent_execution_tracing.arn
    error_tracing              = aws_xray_sampling_rule.error_tracing.arn
  }
}

output "xray_layer_arn" {
  description = "ARN of X-Ray correlation layer"
  value       = var.xray_layer_zip_path != "" ? aws_lambda_layer_version.xray_correlation_layer.arn : ""
}

output "xray_role_arn" {
  description = "ARN of X-Ray IAM role"
  value       = aws_iam_role.xray_role.arn
}

output "xray_encryption_config" {
  description = "X-Ray encryption configuration"
  value = {
    type   = aws_xray_encryption_config.main.type
    key_id = aws_xray_encryption_config.main.key_id
  }
}

output "xray_insights_queries" {
  description = "CloudWatch Insights query definitions for X-Ray"
  value = {
    trace_analysis         = aws_cloudwatch_query_definition.xray_trace_analysis.name
    correlation_id_flow    = aws_cloudwatch_query_definition.correlation_id_flow.name
    performance_bottlenecks = aws_cloudwatch_query_definition.performance_bottlenecks.name
  }
}

output "xray_alarms" {
  description = "X-Ray CloudWatch alarm ARNs"
  value = {
    high_latency = aws_cloudwatch_metric_alarm.xray_high_latency.arn
    error_rate   = aws_cloudwatch_metric_alarm.xray_error_rate.arn
  }
}

output "xray_configuration_summary" {
  description = "X-Ray configuration summary"
  value = {
    service_map_enabled           = true
    correlation_id_tracing       = true
    agent_execution_tracing      = true
    error_tracing               = true
    insights_notifications      = var.enable_xray_insights_notifications
    encryption_enabled          = true
    detailed_tracing_enabled    = var.enable_detailed_tracing
    trace_retention_days        = var.trace_retention_days
    correlation_id_header       = var.correlation_id_header
    sampling_rates = {
      correlation_id_requests = 1.0
      agent_executions       = 0.8
      error_conditions       = 1.0
    }
  }
}