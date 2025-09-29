#!/bin/bash

# Script to set up Terraform backend infrastructure
# This creates the S3 bucket and DynamoDB table needed for remote state

set -e

# Configuration
REGION=${AWS_REGION:-us-east-1}
PROJECT_NAME=${PROJECT_NAME:-sentinel}
ENVIRONMENT=${ENVIRONMENT:-dev}

# Generate unique suffix
SUFFIX=$(openssl rand -hex 4)
BUCKET_NAME="${PROJECT_NAME}-terraform-state-${SUFFIX}"
TABLE_NAME="${PROJECT_NAME}-terraform-locks"

echo "Setting up Terraform backend infrastructure..."
echo "Region: $REGION"
echo "Bucket: $BUCKET_NAME"
echo "DynamoDB Table: $TABLE_NAME"

# Create S3 bucket for state
echo "Creating S3 bucket..."
aws s3api create-bucket \
  --bucket "$BUCKET_NAME" \
  --region "$REGION" \
  $(if [ "$REGION" != "us-east-1" ]; then echo "--create-bucket-configuration LocationConstraint=$REGION"; fi)

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket "$BUCKET_NAME" \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket "$BUCKET_NAME" \
  --server-side-encryption-configuration '{
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        }
      }
    ]
  }'

# Block public access
aws s3api put-public-access-block \
  --bucket "$BUCKET_NAME" \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Create DynamoDB table for locking
echo "Creating DynamoDB table..."
aws dynamodb create-table \
  --table-name "$TABLE_NAME" \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION"

# Wait for table to be active
echo "Waiting for DynamoDB table to be active..."
aws dynamodb wait table-exists --table-name "$TABLE_NAME" --region "$REGION"

# Create backend configuration file
echo "Creating backend configuration..."
cat > backend.hcl << EOF
bucket         = "$BUCKET_NAME"
region         = "$REGION"
dynamodb_table = "$TABLE_NAME"
EOF

echo ""
echo "Backend infrastructure created successfully!"
echo ""
echo "Next steps:"
echo "1. Review the generated backend.hcl file"
echo "2. Run: terraform init -backend-config=backend.hcl"
echo "3. Continue with your Terraform deployment"
echo ""
echo "Backend configuration:"
echo "  Bucket: $BUCKET_NAME"
echo "  Region: $REGION"
echo "  DynamoDB Table: $TABLE_NAME"