# Amplify Module for Sentinel Infrastructure
# Creates Amplify app with branch configuration and build settings

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

# Amplify App
resource "aws_amplify_app" "main" {
  name       = "${var.name_prefix}-web-app"
  repository = var.repository_url

  # Build settings
  build_spec = var.build_spec != null ? var.build_spec : templatefile("${path.module}/build_spec.yml", {
    api_gateway_url     = var.api_gateway_url
    user_pool_id       = var.user_pool_id
    user_pool_client_id = var.user_pool_client_id
    identity_pool_id   = var.identity_pool_id
    region             = data.aws_region.current.name
  })

  # Platform
  platform = "WEB"

  # Environment variables
  environment_variables = merge(var.environment_variables, {
    REACT_APP_AWS_REGION                = data.aws_region.current.name
    REACT_APP_USER_POOL_ID             = var.user_pool_id
    REACT_APP_USER_POOL_WEB_CLIENT_ID  = var.user_pool_client_id
    REACT_APP_IDENTITY_POOL_ID         = var.identity_pool_id
    REACT_APP_API_GATEWAY_URL          = var.api_gateway_url
    REACT_APP_PROJECT_NAME             = var.name_prefix
    AMPLIFY_DIFF_DEPLOY                = "false"
    AMPLIFY_MONOREPO_APP_ROOT          = var.app_root_path
  })

  # Custom rules for SPA routing
  custom_rule {
    source = "/<*>"
    status = "404-200"
    target = "/index.html"
  }

  # Security headers
  custom_rule {
    source = "https://*.amazonaws.com"
    status = "200"
    target = "https://*.amazonaws.com"
    condition = ""
  }

  # IAM service role
  iam_service_role_arn = aws_iam_role.amplify_service.arn

  # Auto branch creation
  enable_auto_branch_creation = var.enable_auto_branch_creation
  auto_branch_creation_patterns = var.auto_branch_creation_patterns

  auto_branch_creation_config {
    enable_auto_build           = true
    enable_basic_auth          = false
    enable_performance_mode    = false
    enable_pull_request_preview = true
    framework                  = "React"
    stage                      = "DEVELOPMENT"
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-amplify-app"
    Purpose = "Sentinel web application"
  })
}

# Amplify Branch (Main)
resource "aws_amplify_branch" "main" {
  app_id      = aws_amplify_app.main.id
  branch_name = var.main_branch_name

  framework                = "React"
  stage                   = "PRODUCTION"
  enable_auto_build       = true
  enable_basic_auth       = false
  enable_performance_mode = var.enable_performance_mode
  enable_pull_request_preview = false

  # Environment variables specific to main branch
  environment_variables = {
    REACT_APP_ENVIRONMENT = "production"
    REACT_APP_LOG_LEVEL   = "warn"
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-amplify-main-branch"
    Purpose = "Production branch"
  })
}

# Amplify Branch (Development)
resource "aws_amplify_branch" "development" {
  count = var.create_dev_branch ? 1 : 0

  app_id      = aws_amplify_app.main.id
  branch_name = var.dev_branch_name

  framework                = "React"
  stage                   = "DEVELOPMENT"
  enable_auto_build       = true
  enable_basic_auth       = var.enable_dev_basic_auth
  enable_performance_mode = false
  enable_pull_request_preview = true

  # Basic auth for development
  dynamic "basic_auth_credentials" {
    for_each = var.enable_dev_basic_auth ? [1] : []
    content {
      username = var.dev_basic_auth_username
      password = var.dev_basic_auth_password
    }
  }

  # Environment variables specific to development branch
  environment_variables = {
    REACT_APP_ENVIRONMENT = "development"
    REACT_APP_LOG_LEVEL   = "debug"
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-amplify-dev-branch"
    Purpose = "Development branch"
  })
}

# Amplify Domain Association (if custom domain provided)
resource "aws_amplify_domain_association" "main" {
  count = var.custom_domain != null ? 1 : 0

  app_id      = aws_amplify_app.main.id
  domain_name = var.custom_domain

  # Main branch subdomain
  sub_domain {
    branch_name = aws_amplify_branch.main.branch_name
    prefix      = var.main_subdomain_prefix
  }

  # Development branch subdomain
  dynamic "sub_domain" {
    for_each = var.create_dev_branch ? [1] : []
    content {
      branch_name = aws_amplify_branch.development[0].branch_name
      prefix      = var.dev_subdomain_prefix
    }
  }

  # Wait for certificate validation
  wait_for_verification = true
}

# IAM Service Role for Amplify
resource "aws_iam_role" "amplify_service" {
  name = "${var.name_prefix}-amplify-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "amplify.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-amplify-service-role"
    Purpose = "Amplify service role"
  })
}

# IAM Policy for Amplify Service Role
resource "aws_iam_role_policy" "amplify_service" {
  name = "${var.name_prefix}-amplify-service-policy"
  role = aws_iam_role.amplify_service.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/amplify/*"
      },
      {
        Effect = "Allow"
        Action = [
          "amplify:GetApp",
          "amplify:GetBranch",
          "amplify:GetJob",
          "amplify:ListJobs"
        ]
        Resource = "*"
      }
    ]
  })
}

# Amplify Webhook (for manual deployments)
resource "aws_amplify_webhook" "main" {
  app_id      = aws_amplify_app.main.id
  branch_name = aws_amplify_branch.main.branch_name
  description = "Webhook for manual deployments"
}

# CloudWatch Log Group for Amplify
resource "aws_cloudwatch_log_group" "amplify" {
  name              = "/aws/amplify/${var.name_prefix}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-amplify-logs"
    Purpose = "Amplify build and deployment logs"
  })
}

# CloudWatch Alarms for Amplify
resource "aws_cloudwatch_metric_alarm" "build_failures" {
  alarm_name          = "${var.name_prefix}-amplify-build-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "BuildFailures"
  namespace           = "AWS/Amplify"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "This metric monitors Amplify build failures"
  alarm_actions       = var.alarm_topic_arn != null ? [var.alarm_topic_arn] : []

  dimensions = {
    AppId = aws_amplify_app.main.id
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-amplify-build-failures-alarm"
  })
}