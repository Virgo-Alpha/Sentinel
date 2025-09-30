# Terraform remote state backend configuration
# Note: The backend configuration cannot use variables or interpolation
# You'll need to configure this with actual values during terraform init
# Example: terraform init -backend-config="bucket=your-actual-bucket-name"

terraform {
  backend "s3" {
    # These values must be provided via terraform init -backend-config
    # or a backend.hcl file, as variables cannot be used here
    key     = "sentinel/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}