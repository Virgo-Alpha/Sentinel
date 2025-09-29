# Outputs for VPC Module

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

output "nat_gateway_ids" {
  description = "IDs of the NAT Gateways"
  value       = aws_nat_gateway.main[*].id
}

output "lambda_security_group_id" {
  description = "ID of the Lambda security group"
  value       = aws_security_group.lambda.id
}

output "vpc_endpoints_security_group_id" {
  description = "ID of the VPC endpoints security group"
  value       = aws_security_group.vpc_endpoints.id
}

output "bedrock_vpc_endpoint_id" {
  description = "ID of the Bedrock VPC endpoint"
  value       = aws_vpc_endpoint.bedrock.id
}

output "bedrock_agent_vpc_endpoint_id" {
  description = "ID of the Bedrock Agent VPC endpoint"
  value       = aws_vpc_endpoint.bedrock_agent.id
}

output "opensearch_vpc_endpoint_id" {
  description = "ID of the OpenSearch VPC endpoint"
  value       = var.enable_opensearch ? aws_vpc_endpoint.opensearch[0].id : null
}

output "s3_vpc_endpoint_id" {
  description = "ID of the S3 VPC endpoint"
  value       = aws_vpc_endpoint.s3.id
}

output "dynamodb_vpc_endpoint_id" {
  description = "ID of the DynamoDB VPC endpoint"
  value       = aws_vpc_endpoint.dynamodb.id
}