# Outputs for KMS Module

output "key_arn" {
  description = "ARN of the KMS key"
  value       = aws_kms_key.sentinel.arn
}

output "key_id" {
  description = "ID of the KMS key"
  value       = aws_kms_key.sentinel.key_id
}

output "key_alias" {
  description = "Alias of the KMS key"
  value       = aws_kms_alias.sentinel.name
}

output "opensearch_key_arn" {
  description = "ARN of the OpenSearch KMS key"
  value       = var.create_opensearch_key ? aws_kms_key.opensearch[0].arn : null
}

output "opensearch_key_id" {
  description = "ID of the OpenSearch KMS key"
  value       = var.create_opensearch_key ? aws_kms_key.opensearch[0].key_id : null
}

output "opensearch_key_alias" {
  description = "Alias of the OpenSearch KMS key"
  value       = var.create_opensearch_key ? aws_kms_alias.opensearch[0].name : null
}