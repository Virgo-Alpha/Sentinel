# Outputs for DynamoDB Module

output "articles_table_name" {
  description = "Name of the articles table"
  value       = aws_dynamodb_table.articles.name
}

output "articles_table_arn" {
  description = "ARN of the articles table"
  value       = aws_dynamodb_table.articles.arn
}

output "articles_table_id" {
  description = "ID of the articles table"
  value       = aws_dynamodb_table.articles.id
}

output "comments_table_name" {
  description = "Name of the comments table"
  value       = aws_dynamodb_table.comments.name
}

output "comments_table_arn" {
  description = "ARN of the comments table"
  value       = aws_dynamodb_table.comments.arn
}

output "comments_table_id" {
  description = "ID of the comments table"
  value       = aws_dynamodb_table.comments.id
}

output "memory_table_name" {
  description = "Name of the memory table"
  value       = aws_dynamodb_table.memory.name
}

output "memory_table_arn" {
  description = "ARN of the memory table"
  value       = aws_dynamodb_table.memory.arn
}

output "memory_table_id" {
  description = "ID of the memory table"
  value       = aws_dynamodb_table.memory.id
}

output "table_names" {
  description = "Map of all table names"
  value = {
    articles = aws_dynamodb_table.articles.name
    comments = aws_dynamodb_table.comments.name
    memory   = aws_dynamodb_table.memory.name
  }
}

output "table_arns" {
  description = "Map of all table ARNs"
  value = {
    articles = aws_dynamodb_table.articles.arn
    comments = aws_dynamodb_table.comments.arn
    memory   = aws_dynamodb_table.memory.arn
  }
}

# GSI Information
output "articles_gsi_names" {
  description = "Names of Articles table GSIs"
  value = [
    "state-published_at-index",
    "cluster-published_at-index",
    "source-ingested_at-index"
  ]
}

output "comments_gsi_names" {
  description = "Names of Comments table GSIs"
  value = [
    "article-created_at-index",
    "parent-created_at-index"
  ]
}

output "memory_gsi_names" {
  description = "Names of Memory table GSIs"
  value = [
    "session-created_at-index",
    "type-created_at-index"
  ]
}