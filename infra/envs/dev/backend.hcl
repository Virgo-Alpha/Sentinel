# Backend configuration for Development Environment
# Use this file with: terraform init -backend-config=backend.hcl

bucket         = "sentinel-terraform-state-dev"
key            = "sentinel/dev/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "sentinel-terraform-locks-dev"
encrypt        = true

# Optional: Add these for additional security
# kms_key_id     = "arn:aws:kms:us-east-1:ACCOUNT:key/KEY-ID"
# role_arn       = "arn:aws:iam::ACCOUNT:role/TerraformRole"