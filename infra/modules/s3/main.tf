# S3 Module for Sentinel Infrastructure
# Creates buckets for artifacts, raw content, normalized content, and traces

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

# Content Bucket - stores raw and normalized article content
resource "aws_s3_bucket" "content" {
  bucket = "${var.name_prefix}-content-${var.resource_suffix}"

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-content-bucket"
    Purpose     = "Article content storage"
    ContentType = "Raw and normalized articles"
  })
}

# Artifacts Bucket - stores Lambda deployment packages and other artifacts
resource "aws_s3_bucket" "artifacts" {
  bucket = "${var.name_prefix}-artifacts-${var.resource_suffix}"

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-artifacts-bucket"
    Purpose     = "Lambda artifacts and deployment packages"
    ContentType = "Code artifacts"
  })
}

# Traces Bucket - stores execution traces and debugging information
resource "aws_s3_bucket" "traces" {
  bucket = "${var.name_prefix}-traces-${var.resource_suffix}"

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-traces-bucket"
    Purpose     = "Execution traces and debugging"
    ContentType = "Trace data"
  })
}

# S3 Bucket Versioning - Content
resource "aws_s3_bucket_versioning" "content" {
  bucket = aws_s3_bucket.content.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket Versioning - Artifacts
resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket Versioning - Traces
resource "aws_s3_bucket_versioning" "traces" {
  bucket = aws_s3_bucket.traces.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket Encryption - Content
resource "aws_s3_bucket_server_side_encryption_configuration" "content" {
  bucket = aws_s3_bucket.content.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# S3 Bucket Encryption - Artifacts
resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# S3 Bucket Encryption - Traces
resource "aws_s3_bucket_server_side_encryption_configuration" "traces" {
  bucket = aws_s3_bucket.traces.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# S3 Bucket Public Access Block - Content
resource "aws_s3_bucket_public_access_block" "content" {
  bucket = aws_s3_bucket.content.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket Public Access Block - Artifacts
resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket Public Access Block - Traces
resource "aws_s3_bucket_public_access_block" "traces" {
  bucket = aws_s3_bucket.traces.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket Lifecycle Configuration - Content
resource "aws_s3_bucket_lifecycle_configuration" "content" {
  bucket = aws_s3_bucket.content.id

  rule {
    id     = "content_lifecycle"
    status = "Enabled"

    # Transition to IA after 30 days
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    # Transition to Glacier after 90 days
    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    # Delete after retention period
    expiration {
      days = var.retention_days
    }

    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    # Handle non-current versions
    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# S3 Bucket Lifecycle Configuration - Artifacts
resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    id     = "artifacts_lifecycle"
    status = "Enabled"

    # Keep artifacts longer than content
    expiration {
      days = var.retention_days * 2
    }

    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    # Handle non-current versions - keep more versions for artifacts
    noncurrent_version_expiration {
      noncurrent_days = 180
    }
  }
}

# S3 Bucket Lifecycle Configuration - Traces
resource "aws_s3_bucket_lifecycle_configuration" "traces" {
  bucket = aws_s3_bucket.traces.id

  rule {
    id     = "traces_lifecycle"
    status = "Enabled"

    # Transition to IA quickly for traces
    transition {
      days          = 7
      storage_class = "STANDARD_IA"
    }

    # Transition to Glacier for long-term storage
    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    # Delete traces after shorter period
    expiration {
      days = var.retention_days / 2
    }

    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }

    # Handle non-current versions
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# S3 Bucket Notification for Lambda triggers (artifacts bucket)
resource "aws_s3_bucket_notification" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  # Lambda function will be created later, so we use depends_on
  depends_on = [aws_s3_bucket.artifacts]
}

# S3 Bucket Policy - Content
resource "aws_s3_bucket_policy" "content" {
  bucket = aws_s3_bucket.content.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyInsecureConnections"
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.content.arn,
          "${aws_s3_bucket.content.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid    = "AllowSentinelLambdaAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.name_prefix}-*"
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.content.arn}/*"
      }
    ]
  })
}

# S3 Bucket Policy - Artifacts
resource "aws_s3_bucket_policy" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyInsecureConnections"
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.artifacts.arn,
          "${aws_s3_bucket.artifacts.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid    = "AllowLambdaServiceAccess"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.artifacts.arn}/*"
      }
    ]
  })
}

# S3 Bucket Policy - Traces
resource "aws_s3_bucket_policy" "traces" {
  bucket = aws_s3_bucket.traces.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyInsecureConnections"
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.traces.arn,
          "${aws_s3_bucket.traces.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid    = "AllowSentinelLambdaAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.name_prefix}-*"
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.traces.arn}/*"
      }
    ]
  })
}