# DynamoDB Module for Sentinel Infrastructure
# Creates Articles, Comments, Memory tables and GSIs

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Articles Table - Main table for storing article data
resource "aws_dynamodb_table" "articles" {
  name           = "${var.name_prefix}-articles"
  billing_mode   = var.billing_mode
  hash_key       = "article_id"

  # Provisioned throughput (only used if billing_mode is PROVISIONED)
  read_capacity  = var.billing_mode == "PROVISIONED" ? var.read_capacity : null
  write_capacity = var.billing_mode == "PROVISIONED" ? var.write_capacity : null

  attribute {
    name = "article_id"
    type = "S"
  }

  attribute {
    name = "state"
    type = "S"
  }

  attribute {
    name = "published_at"
    type = "S"
  }

  attribute {
    name = "cluster_id"
    type = "S"
  }

  attribute {
    name = "source"
    type = "S"
  }

  attribute {
    name = "ingested_at"
    type = "S"
  }

  # GSI for querying by state and published date
  global_secondary_index {
    name            = "state-published_at-index"
    hash_key        = "state"
    range_key       = "published_at"
    projection_type = "ALL"

    read_capacity  = var.billing_mode == "PROVISIONED" ? var.gsi_read_capacity : null
    write_capacity = var.billing_mode == "PROVISIONED" ? var.gsi_write_capacity : null
  }

  # GSI for querying by cluster
  global_secondary_index {
    name            = "cluster-published_at-index"
    hash_key        = "cluster_id"
    range_key       = "published_at"
    projection_type = "ALL"

    read_capacity  = var.billing_mode == "PROVISIONED" ? var.gsi_read_capacity : null
    write_capacity = var.billing_mode == "PROVISIONED" ? var.gsi_write_capacity : null
  }

  # GSI for querying by source and ingestion date
  global_secondary_index {
    name            = "source-ingested_at-index"
    hash_key        = "source"
    range_key       = "ingested_at"
    projection_type = "ALL"

    read_capacity  = var.billing_mode == "PROVISIONED" ? var.gsi_read_capacity : null
    write_capacity = var.billing_mode == "PROVISIONED" ? var.gsi_write_capacity : null
  }

  # Enable point-in-time recovery
  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  # Server-side encryption
  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  # TTL configuration for automatic cleanup
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-articles-table"
    Purpose = "Article storage and metadata"
  })
}

# Comments Table - Stores user comments and discussions
resource "aws_dynamodb_table" "comments" {
  name           = "${var.name_prefix}-comments"
  billing_mode   = var.billing_mode
  hash_key       = "comment_id"

  # Provisioned throughput (only used if billing_mode is PROVISIONED)
  read_capacity  = var.billing_mode == "PROVISIONED" ? var.read_capacity : null
  write_capacity = var.billing_mode == "PROVISIONED" ? var.write_capacity : null

  attribute {
    name = "comment_id"
    type = "S"
  }

  attribute {
    name = "article_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  attribute {
    name = "parent_comment_id"
    type = "S"
  }

  # GSI for querying comments by article
  global_secondary_index {
    name            = "article-created_at-index"
    hash_key        = "article_id"
    range_key       = "created_at"
    projection_type = "ALL"

    read_capacity  = var.billing_mode == "PROVISIONED" ? var.gsi_read_capacity : null
    write_capacity = var.billing_mode == "PROVISIONED" ? var.gsi_write_capacity : null
  }

  # GSI for threaded comments
  global_secondary_index {
    name            = "parent-created_at-index"
    hash_key        = "parent_comment_id"
    range_key       = "created_at"
    projection_type = "ALL"

    read_capacity  = var.billing_mode == "PROVISIONED" ? var.gsi_read_capacity : null
    write_capacity = var.billing_mode == "PROVISIONED" ? var.gsi_write_capacity : null
  }

  # Enable point-in-time recovery
  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  # Server-side encryption
  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  # TTL configuration
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-comments-table"
    Purpose = "User comments and discussions"
  })
}

# Memory Table - Stores agent memory and conversation context
resource "aws_dynamodb_table" "memory" {
  name           = "${var.name_prefix}-memory"
  billing_mode   = var.billing_mode
  hash_key       = "memory_id"

  # Provisioned throughput (only used if billing_mode is PROVISIONED)
  read_capacity  = var.billing_mode == "PROVISIONED" ? var.read_capacity : null
  write_capacity = var.billing_mode == "PROVISIONED" ? var.write_capacity : null

  attribute {
    name = "memory_id"
    type = "S"
  }

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  attribute {
    name = "memory_type"
    type = "S"
  }

  # GSI for querying by session
  global_secondary_index {
    name            = "session-created_at-index"
    hash_key        = "session_id"
    range_key       = "created_at"
    projection_type = "ALL"

    read_capacity  = var.billing_mode == "PROVISIONED" ? var.gsi_read_capacity : null
    write_capacity = var.billing_mode == "PROVISIONED" ? var.gsi_write_capacity : null
  }

  # GSI for querying by memory type
  global_secondary_index {
    name            = "type-created_at-index"
    hash_key        = "memory_type"
    range_key       = "created_at"
    projection_type = "ALL"

    read_capacity  = var.billing_mode == "PROVISIONED" ? var.gsi_read_capacity : null
    write_capacity = var.billing_mode == "PROVISIONED" ? var.gsi_write_capacity : null
  }

  # Enable point-in-time recovery
  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  # Server-side encryption
  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  # TTL configuration for automatic cleanup of old memory
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-memory-table"
    Purpose = "Agent memory and conversation context"
  })
}

# Auto Scaling for Articles Table (if using provisioned billing)
resource "aws_appautoscaling_target" "articles_read" {
  count = var.billing_mode == "PROVISIONED" && var.enable_autoscaling ? 1 : 0

  max_capacity       = var.max_read_capacity
  min_capacity       = var.min_read_capacity
  resource_id        = "table/${aws_dynamodb_table.articles.name}"
  scalable_dimension = "dynamodb:table:ReadCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_target" "articles_write" {
  count = var.billing_mode == "PROVISIONED" && var.enable_autoscaling ? 1 : 0

  max_capacity       = var.max_write_capacity
  min_capacity       = var.min_write_capacity
  resource_id        = "table/${aws_dynamodb_table.articles.name}"
  scalable_dimension = "dynamodb:table:WriteCapacityUnits"
  service_namespace  = "dynamodb"
}

# Auto Scaling Policies
resource "aws_appautoscaling_policy" "articles_read_policy" {
  count = var.billing_mode == "PROVISIONED" && var.enable_autoscaling ? 1 : 0

  name               = "${var.name_prefix}-articles-read-scaling-policy"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.articles_read[0].resource_id
  scalable_dimension = aws_appautoscaling_target.articles_read[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.articles_read[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }
    target_value = 70.0
  }
}

resource "aws_appautoscaling_policy" "articles_write_policy" {
  count = var.billing_mode == "PROVISIONED" && var.enable_autoscaling ? 1 : 0

  name               = "${var.name_prefix}-articles-write-scaling-policy"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.articles_write[0].resource_id
  scalable_dimension = aws_appautoscaling_target.articles_write[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.articles_write[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBWriteCapacityUtilization"
    }
    target_value = 70.0
  }
}