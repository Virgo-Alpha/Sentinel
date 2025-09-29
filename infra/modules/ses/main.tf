# SES Module for Sentinel Infrastructure
# Creates verified identities and email templates

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

# SES Domain Identity (if domain is provided)
resource "aws_ses_domain_identity" "main" {
  count = var.domain != null ? 1 : 0
  
  domain = var.domain
}

# SES Domain DKIM
resource "aws_ses_domain_dkim" "main" {
  count = var.domain != null ? 1 : 0
  
  domain = aws_ses_domain_identity.main[0].domain
}

# SES Email Identity for sender
resource "aws_ses_email_identity" "sender" {
  email = var.sender_email
}

# SES Email Identities for escalation recipients
resource "aws_ses_email_identity" "escalation_recipients" {
  for_each = toset(var.escalation_emails)
  
  email = each.value
}

# SES Email Identities for digest recipients
resource "aws_ses_email_identity" "digest_recipients" {
  for_each = toset(var.digest_emails)
  
  email = each.value
}

# SES Email Identities for alert recipients
resource "aws_ses_email_identity" "alert_recipients" {
  for_each = toset(var.alert_emails)
  
  email = each.value
}

# SES Configuration Set
resource "aws_ses_configuration_set" "main" {
  name = "${var.name_prefix}-configuration-set"

  delivery_options {
    tls_policy = "Require"
  }

  reputation_metrics_enabled = true
}

# SES Event Destination for CloudWatch
resource "aws_ses_event_destination" "cloudwatch" {
  name                   = "${var.name_prefix}-cloudwatch-destination"
  configuration_set_name = aws_ses_configuration_set.main.name
  enabled                = true
  matching_types         = ["send", "reject", "bounce", "complaint", "delivery"]

  cloudwatch_destination {
    default_value  = "default"
    dimension_name = "MessageTag"
    value_source   = "messageTag"
  }
}

# Email Templates
resource "aws_ses_template" "escalation_notification" {
  name    = "${var.name_prefix}-escalation-notification"
  subject = "Sentinel: Article Requires Review - {{article_title}}"
  
  html = templatefile("${path.module}/templates/escalation_notification.html", {
    project_name = var.name_prefix
  })
  
  text = templatefile("${path.module}/templates/escalation_notification.txt", {
    project_name = var.name_prefix
  })
}

resource "aws_ses_template" "publication_notification" {
  name    = "${var.name_prefix}-publication-notification"
  subject = "Sentinel: New Article Published - {{article_title}}"
  
  html = templatefile("${path.module}/templates/publication_notification.html", {
    project_name = var.name_prefix
  })
  
  text = templatefile("${path.module}/templates/publication_notification.txt", {
    project_name = var.name_prefix
  })
}

resource "aws_ses_template" "daily_digest" {
  name    = "${var.name_prefix}-daily-digest"
  subject = "Sentinel Daily Digest - {{date}}"
  
  html = templatefile("${path.module}/templates/daily_digest.html", {
    project_name = var.name_prefix
  })
  
  text = templatefile("${path.module}/templates/daily_digest.txt", {
    project_name = var.name_prefix
  })
}

resource "aws_ses_template" "weekly_summary" {
  name    = "${var.name_prefix}-weekly-summary"
  subject = "Sentinel Weekly Summary - Week of {{week_start}}"
  
  html = templatefile("${path.module}/templates/weekly_summary.html", {
    project_name = var.name_prefix
  })
  
  text = templatefile("${path.module}/templates/weekly_summary.txt", {
    project_name = var.name_prefix
  })
}

resource "aws_ses_template" "alert_notification" {
  name    = "${var.name_prefix}-alert-notification"
  subject = "Sentinel Alert: {{alert_type}} - {{article_title}}"
  
  html = templatefile("${path.module}/templates/alert_notification.html", {
    project_name = var.name_prefix
  })
  
  text = templatefile("${path.module}/templates/alert_notification.txt", {
    project_name = var.name_prefix
  })
}

# SNS Topic for SES bounce/complaint handling
resource "aws_sns_topic" "ses_notifications" {
  name = "${var.name_prefix}-ses-notifications"
  
  kms_master_key_id = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-ses-notifications"
    Purpose = "SES bounce and complaint notifications"
  })
}

# SNS Topic Policy
resource "aws_sns_topic_policy" "ses_notifications" {
  arn = aws_sns_topic.ses_notifications.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowSESPublish"
        Effect = "Allow"
        Principal = {
          Service = "ses.amazonaws.com"
        }
        Action = "sns:Publish"
        Resource = aws_sns_topic.ses_notifications.arn
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

# SES Identity Notification Topic (for bounces and complaints)
resource "aws_ses_identity_notification_topic" "sender_bounces" {
  topic_arn                = aws_sns_topic.ses_notifications.arn
  notification_type        = "Bounce"
  identity                = aws_ses_email_identity.sender.email
  include_original_headers = true
}

resource "aws_ses_identity_notification_topic" "sender_complaints" {
  topic_arn                = aws_sns_topic.ses_notifications.arn
  notification_type        = "Complaint"
  identity                = aws_ses_email_identity.sender.email
  include_original_headers = true
}

# CloudWatch Log Group for SES
resource "aws_cloudwatch_log_group" "ses" {
  name              = "/aws/ses/${var.name_prefix}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-ses-logs"
    Purpose = "SES email logs"
  })
}

# CloudWatch Alarms for SES monitoring
resource "aws_cloudwatch_metric_alarm" "ses_bounce_rate" {
  alarm_name          = "${var.name_prefix}-ses-bounce-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Bounce"
  namespace           = "AWS/SES"
  period              = "300"
  statistic           = "Average"
  threshold           = var.bounce_rate_threshold
  alarm_description   = "This metric monitors SES bounce rate"
  alarm_actions       = var.alarm_topic_arn != null ? [var.alarm_topic_arn] : []

  dimensions = {
    ConfigurationSet = aws_ses_configuration_set.main.name
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-ses-bounce-rate-alarm"
  })
}

resource "aws_cloudwatch_metric_alarm" "ses_complaint_rate" {
  alarm_name          = "${var.name_prefix}-ses-complaint-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Complaint"
  namespace           = "AWS/SES"
  period              = "300"
  statistic           = "Average"
  threshold           = var.complaint_rate_threshold
  alarm_description   = "This metric monitors SES complaint rate"
  alarm_actions       = var.alarm_topic_arn != null ? [var.alarm_topic_arn] : []

  dimensions = {
    ConfigurationSet = aws_ses_configuration_set.main.name
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-ses-complaint-rate-alarm"
  })
}