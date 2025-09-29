# Outputs for OpenSearch Module

output "articles_collection_arn" {
  description = "ARN of the articles collection"
  value       = aws_opensearchserverless_collection.articles.arn
}

output "articles_collection_id" {
  description = "ID of the articles collection"
  value       = aws_opensearchserverless_collection.articles.id
}

output "articles_collection_endpoint" {
  description = "Endpoint of the articles collection"
  value       = aws_opensearchserverless_collection.articles.collection_endpoint
}

output "vectors_collection_arn" {
  description = "ARN of the vectors collection"
  value       = aws_opensearchserverless_collection.vectors.arn
}

output "vectors_collection_id" {
  description = "ID of the vectors collection"
  value       = aws_opensearchserverless_collection.vectors.id
}

output "vectors_collection_endpoint" {
  description = "Endpoint of the vectors collection"
  value       = aws_opensearchserverless_collection.vectors.collection_endpoint
}

# For backward compatibility, provide a single endpoint
output "endpoint" {
  description = "Primary OpenSearch endpoint (articles collection)"
  value       = aws_opensearchserverless_collection.articles.collection_endpoint
}

output "collection_arn" {
  description = "Primary collection ARN (articles collection)"
  value       = aws_opensearchserverless_collection.articles.arn
}

output "collection_endpoints" {
  description = "Map of all collection endpoints"
  value = {
    articles = aws_opensearchserverless_collection.articles.collection_endpoint
    vectors  = aws_opensearchserverless_collection.vectors.collection_endpoint
  }
}

output "collection_arns" {
  description = "Map of all collection ARNs"
  value = {
    articles = aws_opensearchserverless_collection.articles.arn
    vectors  = aws_opensearchserverless_collection.vectors.arn
  }
}

output "security_policy_names" {
  description = "Names of security policies"
  value = {
    encryption = aws_opensearchserverless_security_policy.encryption.name
    network    = aws_opensearchserverless_security_policy.network.name
  }
}

output "access_policy_name" {
  description = "Name of data access policy"
  value = aws_opensearchserverless_access_policy.data.name
}

output "log_group_name" {
  description = "Name of CloudWatch log group"
  value = aws_cloudwatch_log_group.opensearch.name
}