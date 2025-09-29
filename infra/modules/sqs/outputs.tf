# Outputs for SQS Module

output "queue_urls" {
  description = "URLs of all SQS queues"
  value = {
    ingestion     = aws_sqs_queue.ingestion.url
    review        = aws_sqs_queue.review.url
    notifications = aws_sqs_queue.notifications.url
    priority      = aws_sqs_queue.priority.url
    ordered       = var.enable_fifo_queue ? aws_sqs_queue.ordered_processing[0].url : null
  }
}

output "queue_arns" {
  description = "ARNs of all SQS queues"
  value = {
    ingestion     = aws_sqs_queue.ingestion.arn
    review        = aws_sqs_queue.review.arn
    notifications = aws_sqs_queue.notifications.arn
    priority      = aws_sqs_queue.priority.arn
    ordered       = var.enable_fifo_queue ? aws_sqs_queue.ordered_processing[0].arn : null
  }
}

output "dlq_urls" {
  description = "URLs of all dead letter queues"
  value = {
    ingestion     = aws_sqs_queue.ingestion_dlq.url
    review        = aws_sqs_queue.review_dlq.url
    notifications = aws_sqs_queue.notifications_dlq.url
    priority      = aws_sqs_queue.priority_dlq.url
    ordered       = var.enable_fifo_queue ? aws_sqs_queue.ordered_processing_dlq[0].url : null
  }
}

output "dlq_arns" {
  description = "ARNs of all dead letter queues"
  value = {
    ingestion     = aws_sqs_queue.ingestion_dlq.arn
    review        = aws_sqs_queue.review_dlq.arn
    notifications = aws_sqs_queue.notifications_dlq.arn
    priority      = aws_sqs_queue.priority_dlq.arn
    ordered       = var.enable_fifo_queue ? aws_sqs_queue.ordered_processing_dlq[0].arn : null
  }
}

# Individual queue outputs for easier reference
output "ingestion_queue_url" {
  description = "URL of ingestion queue"
  value       = aws_sqs_queue.ingestion.url
}

output "ingestion_queue_arn" {
  description = "ARN of ingestion queue"
  value       = aws_sqs_queue.ingestion.arn
}

output "review_queue_url" {
  description = "URL of review queue"
  value       = aws_sqs_queue.review.url
}

output "review_queue_arn" {
  description = "ARN of review queue"
  value       = aws_sqs_queue.review.arn
}

output "notifications_queue_url" {
  description = "URL of notifications queue"
  value       = aws_sqs_queue.notifications.url
}

output "notifications_queue_arn" {
  description = "ARN of notifications queue"
  value       = aws_sqs_queue.notifications.arn
}

output "priority_queue_url" {
  description = "URL of priority queue"
  value       = aws_sqs_queue.priority.url
}

output "priority_queue_arn" {
  description = "ARN of priority queue"
  value       = aws_sqs_queue.priority.arn
}

output "queue_names" {
  description = "Names of all queues"
  value = {
    ingestion     = aws_sqs_queue.ingestion.name
    review        = aws_sqs_queue.review.name
    notifications = aws_sqs_queue.notifications.name
    priority      = aws_sqs_queue.priority.name
    ordered       = var.enable_fifo_queue ? aws_sqs_queue.ordered_processing[0].name : null
  }
}