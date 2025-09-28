# Terraform remote state backend configuration
terraform {
  backend "s3" {
    bucket         = "sentinel-terraform-state-${random_id.state_suffix.hex}"
    key            = "sentinel/terraform.tfstate"
    region         = var.aws_region
    dynamodb_table = "sentinel-terraform-locks"
    encrypt        = true
    
    # These will be provided via terraform init -backend-config
    # or environment variables
  }
  
  required_version = ">= 1.5"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}

# Generate a random suffix for unique resource naming
resource "random_id" "state_suffix" {
  byte_length = 4
}