# Outputs for SES Module

output "sender_email" {
  description = "Verified SES sender email"
  value       = aws_ses_email_identity.sender.email
}

output "domain_identity_arn" {
  description = "ARN of SES domain identity"
  value       = var.domain != null ? aws_ses_domain_identity.main[0].arn : null
}

output "domain_verification_token" {
  description = "Domain verification token"
  value       = var.domain != null ? aws_ses_domain_identity.main[0].verification_token : null
}

output "dkim_tokens" {
  description = "DKIM tokens for domain verification"
  value       = var.domain != null ? aws_ses_domain_dkim.main[0].dkim_tokens : []
}

output "configuration_set_name" {
  description = "Name of SES configuration set"
  value       = aws_ses_configuration_set.main.name
}

output "configuration_set_arn" {
  description = "ARN of SES configuration set"
  value       = aws_ses_configuration_set.main.arn
}

output "template_names" {
  description = "Names of all SES templates"
  value = {
    escalation_notification = aws_ses_template.escalation_notification.name
    publication_notification = aws_ses_template.publication_notification.name
    daily_digest           = aws_ses_template.daily_digest.name
    weekly_summary         = aws_ses_template.weekly_summary.name
    alert_notification     = aws_ses_template.alert_notification.name
  }
}

output "sns_topic_arn" {
  description = "ARN of SNS topic for SES notifications"
  value       = aws_sns_topic.ses_notifications.arn
}

output "verified_emails" {
  description = "List of all verified email identities"
  value = concat(
    [aws_ses_email_identity.sender.email],
    [for email in aws_ses_email_identity.escalation_recipients : email.email],
    [for email in aws_ses_email_identity.digest_recipients : email.email],
    [for email in aws_ses_email_identity.alert_recipients : email.email]
  )
}

output "escalation_emails" {
  description = "List of escalation email addresses"
  value       = var.escalation_emails
}

output "digest_emails" {
  description = "List of digest email addresses"
  value       = var.digest_emails
}

output "alert_emails" {
  description = "List of alert email addresses"
  value       = var.alert_emails
}

output "log_group_name" {
  description = "Name of CloudWatch log group"
  value       = aws_cloudwatch_log_group.ses.name
}

output "log_group_arn" {
  description = "ARN of CloudWatch log group"
  value       = aws_cloudwatch_log_group.ses.arn
}