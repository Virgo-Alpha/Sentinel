# Backend configuration for Production Environment
# Use this file with: terraform init -backend-config=backend.hcl

bucket         = "sentinel-terraform-state-prod"
key            = "sentinel/prod/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "sentinel-terraform-locks-prod"
encrypt        = true

# Recommended for production: Use KMS encryption and cross-account role
# kms_key_id     = "arn:aws:kms:us-east-1:ACCOUNT:key/KEY-ID"
# role_arn       = "arn:aws:iam::ACCOUNT:role/TerraformProductionRole"