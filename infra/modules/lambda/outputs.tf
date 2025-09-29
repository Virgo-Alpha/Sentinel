# Outputs for Lambda Module

output "function_arns" {
  description = "ARNs of all Lambda functions"
  value = {
    for name, func in aws_lambda_function.functions : name => func.arn
  }
}

output "function_names" {
  description = "Names of all Lambda functions"
  value = {
    for name, func in aws_lambda_function.functions : name => func.function_name
  }
}

output "function_invoke_arns" {
  description = "Invoke ARNs of all Lambda functions"
  value = {
    for name, func in aws_lambda_function.functions : name => func.invoke_arn
  }
}

output "function_urls" {
  description = "Function URLs for direct HTTP access"
  value = {
    for name, url in aws_lambda_function_url.function_urls : name => url.function_url
  }
}

output "function_aliases" {
  description = "Function aliases"
  value = {
    for name, alias in aws_lambda_alias.function_aliases : name => alias.arn
  }
}

output "dlq_arns" {
  description = "ARNs of dead letter queues"
  value = {
    for name, queue in aws_sqs_queue.lambda_dlq : name => queue.arn
  }
}

output "dlq_urls" {
  description = "URLs of dead letter queues"
  value = {
    for name, queue in aws_sqs_queue.lambda_dlq : name => queue.url
  }
}

output "log_group_names" {
  description = "Names of CloudWatch log groups"
  value = {
    for name, log_group in aws_cloudwatch_log_group.lambda_logs : name => log_group.name
  }
}

output "log_group_arns" {
  description = "ARNs of CloudWatch log groups"
  value = {
    for name, log_group in aws_cloudwatch_log_group.lambda_logs : name => log_group.arn
  }
}

# Individual function outputs for easier reference
output "feed_parser_arn" {
  description = "ARN of feed parser function"
  value       = aws_lambda_function.functions["feed_parser"].arn
}

output "relevancy_evaluator_arn" {
  description = "ARN of relevancy evaluator function"
  value       = aws_lambda_function.functions["relevancy_evaluator"].arn
}

output "dedup_tool_arn" {
  description = "ARN of dedup tool function"
  value       = aws_lambda_function.functions["dedup_tool"].arn
}

output "guardrail_tool_arn" {
  description = "ARN of guardrail tool function"
  value       = aws_lambda_function.functions["guardrail_tool"].arn
}

output "storage_tool_arn" {
  description = "ARN of storage tool function"
  value       = aws_lambda_function.functions["storage_tool"].arn
}

output "human_escalation_arn" {
  description = "ARN of human escalation function"
  value       = aws_lambda_function.functions["human_escalation"].arn
}

output "notifier_arn" {
  description = "ARN of notifier function"
  value       = aws_lambda_function.functions["notifier"].arn
}

output "query_kb_arn" {
  description = "ARN of query KB function"
  value       = aws_lambda_function.functions["query_kb"].arn
}

output "analyst_assistant_arn" {
  description = "ARN of analyst assistant function"
  value       = aws_lambda_function.functions["analyst_assistant"].arn
}

output "publish_decision_arn" {
  description = "ARN of publish decision function"
  value       = aws_lambda_function.functions["publish_decision"].arn
}

output "commentary_api_arn" {
  description = "ARN of commentary API function"
  value       = aws_lambda_function.functions["commentary_api"].arn
}

# Package information
output "package_s3_keys" {
  description = "S3 keys of Lambda packages"
  value = {
    for name, obj in aws_s3_object.lambda_packages : name => obj.key
  }
}

output "package_etags" {
  description = "ETags of Lambda packages for change detection"
  value = {
    for name, obj in aws_s3_object.lambda_packages : name => obj.etag
  }
}