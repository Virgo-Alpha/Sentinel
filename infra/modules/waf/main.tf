# WAF Module for Sentinel Infrastructure
# Creates WAF for web application firewall protection

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

# WAF Web ACL
resource "aws_wafv2_web_acl" "main" {
  name  = "${var.name_prefix}-web-acl"
  scope = "CLOUDFRONT"  # For Amplify apps

  default_action {
    allow {}
  }

  # Rule 1: AWS Managed Core Rule Set
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"

        # Exclude specific rules if needed
        dynamic "excluded_rule" {
          for_each = var.excluded_common_rules
          content {
            name = excluded_rule.value
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name_prefix}-CommonRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # Rule 2: AWS Managed Known Bad Inputs Rule Set
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name_prefix}-KnownBadInputs"
      sampled_requests_enabled   = true
    }
  }

  # Rule 3: Rate Limiting
  rule {
    name     = "RateLimitRule"
    priority = 3

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = var.rate_limit
        aggregate_key_type = "IP"

        scope_down_statement {
          geo_match_statement {
            country_codes = var.allowed_countries
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name_prefix}-RateLimit"
      sampled_requests_enabled   = true
    }
  }

  # Rule 4: Geographic Restriction (if enabled)
  dynamic "rule" {
    for_each = var.enable_geo_blocking ? [1] : []
    content {
      name     = "GeoBlockRule"
      priority = 4

      action {
        block {}
      }

      statement {
        not_statement {
          statement {
            geo_match_statement {
              country_codes = var.allowed_countries
            }
          }
        }
      }

      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "${var.name_prefix}-GeoBlock"
        sampled_requests_enabled   = true
      }
    }
  }

  # Rule 5: IP Reputation List
  rule {
    name     = "AWSManagedRulesAmazonIpReputationList"
    priority = 5

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAmazonIpReputationList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name_prefix}-IpReputation"
      sampled_requests_enabled   = true
    }
  }

  # Rule 6: SQL Injection Protection
  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 6

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name_prefix}-SQLi"
      sampled_requests_enabled   = true
    }
  }

  # Rule 7: Custom IP Whitelist (if provided)
  dynamic "rule" {
    for_each = length(var.allowed_ips) > 0 ? [1] : []
    content {
      name     = "AllowedIPsRule"
      priority = 7

      action {
        allow {}
      }

      statement {
        ip_set_reference_statement {
          arn = aws_wafv2_ip_set.allowed_ips[0].arn
        }
      }

      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "${var.name_prefix}-AllowedIPs"
        sampled_requests_enabled   = true
      }
    }
  }

  # Rule 8: Custom IP Blacklist (if provided)
  dynamic "rule" {
    for_each = length(var.blocked_ips) > 0 ? [1] : []
    content {
      name     = "BlockedIPsRule"
      priority = 8

      action {
        block {}
      }

      statement {
        ip_set_reference_statement {
          arn = aws_wafv2_ip_set.blocked_ips[0].arn
        }
      }

      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "${var.name_prefix}-BlockedIPs"
        sampled_requests_enabled   = true
      }
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.name_prefix}-WebACL"
    sampled_requests_enabled   = true
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-web-acl"
    Purpose = "Web application firewall"
  })
}

# IP Set for Allowed IPs
resource "aws_wafv2_ip_set" "allowed_ips" {
  count = length(var.allowed_ips) > 0 ? 1 : 0

  name  = "${var.name_prefix}-allowed-ips"
  scope = "CLOUDFRONT"

  ip_address_version = "IPV4"
  addresses         = var.allowed_ips

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-allowed-ips"
    Purpose = "Allowed IP addresses"
  })
}

# IP Set for Blocked IPs
resource "aws_wafv2_ip_set" "blocked_ips" {
  count = length(var.blocked_ips) > 0 ? 1 : 0

  name  = "${var.name_prefix}-blocked-ips"
  scope = "CLOUDFRONT"

  ip_address_version = "IPV4"
  addresses         = var.blocked_ips

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-blocked-ips"
    Purpose = "Blocked IP addresses"
  })
}

# CloudWatch Log Group for WAF
resource "aws_cloudwatch_log_group" "waf" {
  name              = "/aws/wafv2/${var.name_prefix}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-waf-logs"
    Purpose = "WAF access logs"
  })
}

# WAF Logging Configuration
resource "aws_wafv2_web_acl_logging_configuration" "main" {
  resource_arn            = aws_wafv2_web_acl.main.arn
  log_destination_configs = [aws_cloudwatch_log_group.waf.arn]

  # Redact sensitive fields
  redacted_fields {
    single_header {
      name = "authorization"
    }
  }

  redacted_fields {
    single_header {
      name = "cookie"
    }
  }

  redacted_fields {
    single_header {
      name = "x-api-key"
    }
  }
}

# CloudWatch Alarms for WAF
resource "aws_cloudwatch_metric_alarm" "blocked_requests" {
  alarm_name          = "${var.name_prefix}-waf-blocked-requests"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "BlockedRequests"
  namespace           = "AWS/WAFV2"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.blocked_requests_threshold
  alarm_description   = "This metric monitors blocked requests by WAF"
  alarm_actions       = var.alarm_topic_arn != null ? [var.alarm_topic_arn] : []

  dimensions = {
    WebACL = aws_wafv2_web_acl.main.name
    Region = "CloudFront"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-waf-blocked-requests-alarm"
  })
}

resource "aws_cloudwatch_metric_alarm" "rate_limit_exceeded" {
  alarm_name          = "${var.name_prefix}-waf-rate-limit-exceeded"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "BlockedRequests"
  namespace           = "AWS/WAFV2"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.rate_limit_threshold
  alarm_description   = "This metric monitors rate limit violations"
  alarm_actions       = var.alarm_topic_arn != null ? [var.alarm_topic_arn] : []

  dimensions = {
    WebACL = aws_wafv2_web_acl.main.name
    Region = "CloudFront"
    Rule   = "RateLimitRule"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-waf-rate-limit-alarm"
  })
}