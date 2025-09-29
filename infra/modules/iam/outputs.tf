# Outputs for IAM Module

output "lambda_execution_role_arn" {
  description = "ARN of Lambda execution role"
  value       = aws_iam_role.lambda_execution.arn
}

output "lambda_execution_role_name" {
  description = "Name of Lambda execution role"
  value       = aws_iam_role.lambda_execution.name
}

output "step_functions_role_arn" {
  description = "ARN of Step Functions execution role"
  value       = aws_iam_role.step_functions.arn
}

output "step_functions_role_name" {
  description = "Name of Step Functions execution role"
  value       = aws_iam_role.step_functions.name
}

output "eventbridge_role_arn" {
  description = "ARN of EventBridge execution role"
  value       = aws_iam_role.eventbridge.arn
}

output "eventbridge_role_name" {
  description = "Name of EventBridge execution role"
  value       = aws_iam_role.eventbridge.name
}

output "bedrock_agent_role_arn" {
  description = "ARN of Bedrock Agent execution role"
  value       = var.enable_bedrock_agents ? aws_iam_role.bedrock_agent[0].arn : null
}

output "bedrock_agent_role_name" {
  description = "Name of Bedrock Agent execution role"
  value       = var.enable_bedrock_agents ? aws_iam_role.bedrock_agent[0].name : null
}

output "api_gateway_role_arn" {
  description = "ARN of API Gateway execution role"
  value       = var.enable_api_gateway ? aws_iam_role.api_gateway[0].arn : null
}

output "api_gateway_role_name" {
  description = "Name of API Gateway execution role"
  value       = var.enable_api_gateway ? aws_iam_role.api_gateway[0].name : null
}

output "ses_role_arn" {
  description = "ARN of SES execution role"
  value       = var.enable_ses ? aws_iam_role.ses[0].arn : null
}

output "ses_role_name" {
  description = "Name of SES execution role"
  value       = var.enable_ses ? aws_iam_role.ses[0].name : null
}

output "role_arns" {
  description = "Map of all role ARNs"
  value = {
    lambda_execution = aws_iam_role.lambda_execution.arn
    step_functions   = aws_iam_role.step_functions.arn
    eventbridge      = aws_iam_role.eventbridge.arn
    bedrock_agent    = var.enable_bedrock_agents ? aws_iam_role.bedrock_agent[0].arn : null
    api_gateway      = var.enable_api_gateway ? aws_iam_role.api_gateway[0].arn : null
    ses              = var.enable_ses ? aws_iam_role.ses[0].arn : null
  }
}

output "role_names" {
  description = "Map of all role names"
  value = {
    lambda_execution = aws_iam_role.lambda_execution.name
    step_functions   = aws_iam_role.step_functions.name
    eventbridge      = aws_iam_role.eventbridge.name
    bedrock_agent    = var.enable_bedrock_agents ? aws_iam_role.bedrock_agent[0].name : null
    api_gateway      = var.enable_api_gateway ? aws_iam_role.api_gateway[0].name : null
    ses              = var.enable_ses ? aws_iam_role.ses[0].name : null
  }
}