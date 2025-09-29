# SQS Module for Sentinel Infrastructure
# Creates queues and dead letter queues for error handling

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Main processing queue for feed ingestion
resource "aws_sqs_queue" "ingestion" {
  name = "${var.name_prefix}-ingestion-queue"

  # Message settings
  message_retention_seconds = 1209600  # 14 days
  visibility_timeout_seconds = 300     # 5 minutes
  receive_wait_time_seconds = 20       # Long polling

  # Dead letter queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ingestion_dlq.arn
    maxReceiveCount     = 3
  })

  # Server-side encryption
  kms_master_key_id = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-ingestion-queue"
    Purpose = "Feed ingestion processing"
  })
}

# Dead letter queue for ingestion
resource "aws_sqs_queue" "ingestion_dlq" {
  name = "${var.name_prefix}-ingestion-dlq"

  # Longer retention for failed messages
  message_retention_seconds = 1209600  # 14 days

  # Server-side encryption
  kms_master_key_id = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-ingestion-dlq"
    Purpose = "Failed ingestion messages"
  })
}

# Human review queue
resource "aws_sqs_queue" "review" {
  name = "${var.name_prefix}-review-queue"

  # Message settings
  message_retention_seconds = 1209600  # 14 days
  visibility_timeout_seconds = 900     # 15 minutes (longer for human review)
  receive_wait_time_seconds = 20       # Long polling

  # Dead letter queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.review_dlq.arn
    maxReceiveCount     = 5  # More retries for human review
  })

  # Server-side encryption
  kms_master_key_id = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-review-queue"
    Purpose = "Human review processing"
  })
}

# Dead letter queue for review
resource "aws_sqs_queue" "review_dlq" {
  name = "${var.name_prefix}-review-dlq"

  # Longer retention for failed messages
  message_retention_seconds = 1209600  # 14 days

  # Server-side encryption
  kms_master_key_id = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-review-dlq"
    Purpose = "Failed review messages"
  })
}

# Notification queue for email alerts
resource "aws_sqs_queue" "notifications" {
  name = "${var.name_prefix}-notifications-queue"

  # Message settings
  message_retention_seconds = 604800   # 7 days (shorter for notifications)
  visibility_timeout_seconds = 60      # 1 minute (quick processing)
  receive_wait_time_seconds = 20       # Long polling

  # Dead letter queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.notifications_dlq.arn
    maxReceiveCount     = 3
  })

  # Server-side encryption
  kms_master_key_id = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-notifications-queue"
    Purpose = "Email notification processing"
  })
}

# Dead letter queue for notifications
resource "aws_sqs_queue" "notifications_dlq" {
  name = "${var.name_prefix}-notifications-dlq"

  # Standard retention for failed notifications
  message_retention_seconds = 604800  # 7 days

  # Server-side encryption
  kms_master_key_id = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-notifications-dlq"
    Purpose = "Failed notification messages"
  })
}

# High priority queue for urgent processing
resource "aws_sqs_queue" "priority" {
  name = "${var.name_prefix}-priority-queue"

  # Message settings for urgent processing
  message_retention_seconds = 604800   # 7 days
  visibility_timeout_seconds = 180     # 3 minutes
  receive_wait_time_seconds = 5        # Shorter polling for urgency

  # Dead letter queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.priority_dlq.arn
    maxReceiveCount     = 2  # Fewer retries for urgent items
  })

  # Server-side encryption
  kms_master_key_id = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-priority-queue"
    Purpose = "High priority processing"
  })
}

# Dead letter queue for priority
resource "aws_sqs_queue" "priority_dlq" {
  name = "${var.name_prefix}-priority-dlq"

  # Standard retention
  message_retention_seconds = 604800  # 7 days

  # Server-side encryption
  kms_master_key_id = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-priority-dlq"
    Purpose = "Failed priority messages"
  })
}

# FIFO queue for ordered processing (optional)
resource "aws_sqs_queue" "ordered_processing" {
  count = var.enable_fifo_queue ? 1 : 0

  name                        = "${var.name_prefix}-ordered-processing.fifo"
  fifo_queue                  = true
  content_based_deduplication = true

  # Message settings
  message_retention_seconds = 1209600  # 14 days
  visibility_timeout_seconds = 300     # 5 minutes

  # Dead letter queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ordered_processing_dlq[0].arn
    maxReceiveCount     = 3
  })

  # Server-side encryption
  kms_master_key_id = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-ordered-processing-fifo"
    Purpose = "Ordered processing with deduplication"
  })
}

# Dead letter queue for FIFO queue
resource "aws_sqs_queue" "ordered_processing_dlq" {
  count = var.enable_fifo_queue ? 1 : 0

  name       = "${var.name_prefix}-ordered-processing-dlq.fifo"
  fifo_queue = true

  # Standard retention
  message_retention_seconds = 1209600  # 14 days

  # Server-side encryption
  kms_master_key_id = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-ordered-processing-dlq-fifo"
    Purpose = "Failed ordered processing messages"
  })
}

# Queue policies for cross-service access
resource "aws_sqs_queue_policy" "ingestion_policy" {
  queue_url = aws_sqs_queue.ingestion.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEventBridgeAccess"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action = [
          "sqs:SendMessage"
        ]
        Resource = aws_sqs_queue.ingestion.arn
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      },
      {
        Sid    = "AllowLambdaAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.name_prefix}-*"
        }
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.ingestion.arn
      }
    ]
  })
}

# CloudWatch Alarms for queue monitoring
resource "aws_cloudwatch_metric_alarm" "ingestion_queue_depth" {
  alarm_name          = "${var.name_prefix}-ingestion-queue-depth"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ApproximateNumberOfVisibleMessages"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = var.queue_depth_alarm_threshold
  alarm_description   = "This metric monitors ingestion queue depth"
  alarm_actions       = var.alarm_topic_arn != null ? [var.alarm_topic_arn] : []

  dimensions = {
    QueueName = aws_sqs_queue.ingestion.name
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-ingestion-queue-depth-alarm"
  })
}

# CloudWatch Alarms for DLQ monitoring
resource "aws_cloudwatch_metric_alarm" "ingestion_dlq_messages" {
  alarm_name          = "${var.name_prefix}-ingestion-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfVisibleMessages"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors messages in ingestion DLQ"
  alarm_actions       = var.alarm_topic_arn != null ? [var.alarm_topic_arn] : []

  dimensions = {
    QueueName = aws_sqs_queue.ingestion_dlq.name
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-ingestion-dlq-messages-alarm"
  })
}

# Data sources
data "aws_caller_identity" "current" {}