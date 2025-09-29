# Outputs for API Gateway Module

output "api_id" {
  description = "ID of the API Gateway REST API"
  value       = aws_api_gateway_rest_api.main.id
}

output "api_arn" {
  description = "ARN of the API Gateway REST API"
  value       = aws_api_gateway_rest_api.main.arn
}

output "api_execution_arn" {
  description = "Execution ARN of the API Gateway REST API"
  value       = aws_api_gateway_rest_api.main.execution_arn
}

output "api_url" {
  description = "URL of the API Gateway"
  value       = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}"
}

output "stage_name" {
  description = "Name of the API Gateway stage"
  value       = aws_api_gateway_stage.main.stage_name
}

output "stage_arn" {
  description = "ARN of the API Gateway stage"
  value       = aws_api_gateway_stage.main.arn
}

output "authorizer_id" {
  description = "ID of the Cognito authorizer"
  value       = aws_api_gateway_authorizer.cognito.id
}

output "deployment_id" {
  description = "ID of the API Gateway deployment"
  value       = aws_api_gateway_deployment.main.id
}

# Endpoint URLs for different resources
output "endpoints" {
  description = "API endpoint URLs"
  value = {
    chat     = "${aws_api_gateway_stage.main.invoke_url}/chat"
    query    = "${aws_api_gateway_stage.main.invoke_url}/query"
    articles = "${aws_api_gateway_stage.main.invoke_url}/articles"
    comments = "${aws_api_gateway_stage.main.invoke_url}/comments"
    review   = "${aws_api_gateway_stage.main.invoke_url}/review"
  }
}

output "resource_ids" {
  description = "API Gateway resource IDs"
  value = {
    chat     = aws_api_gateway_resource.chat.id
    query    = aws_api_gateway_resource.query.id
    articles = aws_api_gateway_resource.articles.id
    comments = aws_api_gateway_resource.comments.id
    review   = aws_api_gateway_resource.review.id
  }
}

output "log_group_name" {
  description = "Name of CloudWatch log group"
  value       = aws_cloudwatch_log_group.api_gateway.name
}

output "log_group_arn" {
  description = "ARN of CloudWatch log group"
  value       = aws_cloudwatch_log_group.api_gateway.arn
}

# Configuration for client applications
output "api_config" {
  description = "API configuration for client applications"
  value = {
    apiId      = aws_api_gateway_rest_api.main.id
    region     = data.aws_region.current.name
    stage      = aws_api_gateway_stage.main.stage_name
    baseUrl    = aws_api_gateway_stage.main.invoke_url
    endpoints = {
      chat     = "/chat"
      query    = "/query"
      articles = "/articles"
      comments = "/comments"
      review   = "/review"
    }
  }
  sensitive = false
}