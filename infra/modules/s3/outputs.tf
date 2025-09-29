# Outputs for S3 Module

output "content_bucket_name" {
  description = "Name of the content bucket"
  value       = aws_s3_bucket.content.bucket
}

output "content_bucket_arn" {
  description = "ARN of the content bucket"
  value       = aws_s3_bucket.content.arn
}

output "content_bucket_domain_name" {
  description = "Domain name of the content bucket"
  value       = aws_s3_bucket.content.bucket_domain_name
}

output "artifacts_bucket_name" {
  description = "Name of the artifacts bucket"
  value       = aws_s3_bucket.artifacts.bucket
}

output "artifacts_bucket_arn" {
  description = "ARN of the artifacts bucket"
  value       = aws_s3_bucket.artifacts.arn
}

output "artifacts_bucket_domain_name" {
  description = "Domain name of the artifacts bucket"
  value       = aws_s3_bucket.artifacts.bucket_domain_name
}

output "traces_bucket_name" {
  description = "Name of the traces bucket"
  value       = aws_s3_bucket.traces.bucket
}

output "traces_bucket_arn" {
  description = "ARN of the traces bucket"
  value       = aws_s3_bucket.traces.arn
}

output "traces_bucket_domain_name" {
  description = "Domain name of the traces bucket"
  value       = aws_s3_bucket.traces.bucket_domain_name
}

output "bucket_names" {
  description = "Map of all bucket names"
  value = {
    content   = aws_s3_bucket.content.bucket
    artifacts = aws_s3_bucket.artifacts.bucket
    traces    = aws_s3_bucket.traces.bucket
  }
}

output "bucket_arns" {
  description = "Map of all bucket ARNs"
  value = {
    content   = aws_s3_bucket.content.arn
    artifacts = aws_s3_bucket.artifacts.arn
    traces    = aws_s3_bucket.traces.arn
  }
}