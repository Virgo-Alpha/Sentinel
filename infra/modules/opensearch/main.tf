# OpenSearch Serverless Module for Sentinel Infrastructure
# Creates collections, security policies, and access policies

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# OpenSearch Serverless Encryption Policy
resource "aws_opensearchserverless_security_policy" "encryption" {
  name = "${var.name_prefix}-encryption-policy"
  type = "encryption"

  policy = jsonencode({
    Rules = [
      {
        Resource = [
          "collection/${var.name_prefix}-articles",
          "collection/${var.name_prefix}-vectors"
        ]
        ResourceType = "collection"
      }
    ]
    AWSOwnedKey = false
    KmsARN      = var.kms_key_arn
  })

  description = "Encryption policy for Sentinel OpenSearch collections"
}

# OpenSearch Serverless Network Policy
resource "aws_opensearchserverless_security_policy" "network" {
  name = "${var.name_prefix}-network-policy"
  type = "network"

  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/${var.name_prefix}-articles",
            "collection/${var.name_prefix}-vectors"
          ]
          ResourceType = "collection"
        },
        {
          Resource = [
            "collection/${var.name_prefix}-articles",
            "collection/${var.name_prefix}-vectors"
          ]
          ResourceType = "dashboard"
        }
      ]
      AllowFromPublic = var.vpc_id == null ? true : false
      SourceVPCEs = var.vpc_id != null ? [
        # VPC endpoint will be created by VPC module
        # This is a placeholder that will be updated
      ] : null
    }
  ])

  description = "Network policy for Sentinel OpenSearch collections"
}

# OpenSearch Serverless Data Access Policy
resource "aws_opensearchserverless_access_policy" "data" {
  name = "${var.name_prefix}-data-access-policy"
  type = "data"

  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/${var.name_prefix}-articles",
            "collection/${var.name_prefix}-vectors"
          ]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
          ResourceType = "collection"
        },
        {
          Resource = [
            "index/${var.name_prefix}-articles/*",
            "index/${var.name_prefix}-vectors/*"
          ]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
          ResourceType = "index"
        }
      ]
      Principal = [
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.name_prefix}-*"
      ]
    }
  ])

  description = "Data access policy for Sentinel OpenSearch collections"
}

# OpenSearch Serverless Collection for Articles (BM25 text search)
resource "aws_opensearchserverless_collection" "articles" {
  name = "${var.name_prefix}-articles"
  type = "SEARCH"

  description = "OpenSearch collection for article text search using BM25"

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-articles-collection"
    Purpose = "Article text search with BM25"
    Type    = "SEARCH"
  })

  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network,
    aws_opensearchserverless_access_policy.data
  ]
}

# OpenSearch Serverless Collection for Vectors (k-NN search)
resource "aws_opensearchserverless_collection" "vectors" {
  name = "${var.name_prefix}-vectors"
  type = "VECTORSEARCH"

  description = "OpenSearch collection for vector similarity search using k-NN"

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-vectors-collection"
    Purpose = "Vector similarity search with k-NN"
    Type    = "VECTORSEARCH"
  })

  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network,
    aws_opensearchserverless_access_policy.data
  ]
}

# CloudWatch Log Group for OpenSearch
resource "aws_cloudwatch_log_group" "opensearch" {
  name              = "/aws/opensearch/${var.name_prefix}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-opensearch-logs"
    Purpose = "OpenSearch Serverless logs"
  })
}