# Outputs for WAF Module

output "web_acl_id" {
  description = "ID of the WAF Web ACL"
  value       = aws_wafv2_web_acl.main.id
}

output "web_acl_arn" {
  description = "ARN of the WAF Web ACL"
  value       = aws_wafv2_web_acl.main.arn
}

output "web_acl_name" {
  description = "Name of the WAF Web ACL"
  value       = aws_wafv2_web_acl.main.name
}

output "allowed_ips_set_arn" {
  description = "ARN of allowed IPs set"
  value       = length(var.allowed_ips) > 0 ? aws_wafv2_ip_set.allowed_ips[0].arn : null
}

output "blocked_ips_set_arn" {
  description = "ARN of blocked IPs set"
  value       = length(var.blocked_ips) > 0 ? aws_wafv2_ip_set.blocked_ips[0].arn : null
}

output "log_group_name" {
  description = "Name of CloudWatch log group"
  value       = aws_cloudwatch_log_group.waf.name
}

output "log_group_arn" {
  description = "ARN of CloudWatch log group"
  value       = aws_cloudwatch_log_group.waf.arn
}

# Configuration summary
output "waf_config" {
  description = "WAF configuration summary"
  value = {
    web_acl_id          = aws_wafv2_web_acl.main.id
    web_acl_arn         = aws_wafv2_web_acl.main.arn
    rate_limit          = var.rate_limit
    geo_blocking_enabled = var.enable_geo_blocking
    allowed_countries   = var.allowed_countries
    rules_enabled = [
      "AWSManagedRulesCommonRuleSet",
      "AWSManagedRulesKnownBadInputsRuleSet",
      "RateLimitRule",
      "AWSManagedRulesAmazonIpReputationList",
      "AWSManagedRulesSQLiRuleSet"
    ]
  }
  sensitive = false
}