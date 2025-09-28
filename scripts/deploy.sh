#!/bin/bash
# Deployment script for Sentinel Cybersecurity Triage System

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="dev"
SKIP_BOOTSTRAP=false
AUTO_APPROVE=false

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV    Environment to deploy (dev, prod) [default: dev]"
    echo "  -s, --skip-bootstrap     Skip Terraform state bootstrap"
    echo "  -y, --auto-approve       Auto-approve Terraform apply"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                       Deploy to dev environment"
    echo "  $0 -e prod              Deploy to production environment"
    echo "  $0 -e dev -y            Deploy to dev with auto-approve"
    echo "  $0 -s -e prod           Deploy to prod, skip bootstrap"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -s|--skip-bootstrap)
            SKIP_BOOTSTRAP=true
            shift
            ;;
        -y|--auto-approve)
            AUTO_APPROVE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|prod)$ ]]; then
    print_error "Invalid environment: $ENVIRONMENT. Must be 'dev' or 'prod'"
    exit 1
fi

print_status "Starting Sentinel deployment for environment: $ENVIRONMENT"

# Check prerequisites
print_status "Checking prerequisites..."

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    print_error "Terraform is not installed. Please install Terraform 1.5+ first."
    exit 1
fi

# Check Terraform version
TERRAFORM_VERSION=$(terraform version -json | jq -r '.terraform_version')
if [[ $(echo "$TERRAFORM_VERSION 1.5.0" | tr " " "\n" | sort -V | head -n1) != "1.5.0" ]]; then
    print_error "Terraform version $TERRAFORM_VERSION is too old. Please upgrade to 1.5.0 or later."
    exit 1
fi

print_success "Prerequisites check passed"

# Get AWS account info
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")

print_status "Deploying to AWS Account: $AWS_ACCOUNT_ID in region: $AWS_REGION"

# Bootstrap Terraform state (if not skipped)
if [[ "$SKIP_BOOTSTRAP" == false ]]; then
    print_status "Bootstrapping Terraform state backend..."
    
    cd infra/bootstrap
    
    terraform init
    
    if [[ "$AUTO_APPROVE" == true ]]; then
        terraform apply -auto-approve \
            -var="aws_region=$AWS_REGION" \
            -var="project_name=sentinel"
    else
        terraform apply \
            -var="aws_region=$AWS_REGION" \
            -var="project_name=sentinel"
    fi
    
    # Get backend configuration
    S3_BUCKET=$(terraform output -raw s3_bucket_name)
    DYNAMODB_TABLE=$(terraform output -raw dynamodb_table_name)
    
    print_success "Terraform state backend created"
    print_status "S3 Bucket: $S3_BUCKET"
    print_status "DynamoDB Table: $DYNAMODB_TABLE"
    
    cd ../..
else
    print_warning "Skipping Terraform state bootstrap"
    # Assume standard naming convention
    S3_BUCKET="sentinel-terraform-state-$(openssl rand -hex 4)"
    DYNAMODB_TABLE="sentinel-terraform-locks"
fi

# Deploy main infrastructure
print_status "Deploying main infrastructure for $ENVIRONMENT environment..."

cd "infra/envs/$ENVIRONMENT"

# Initialize Terraform with backend configuration
if [[ "$SKIP_BOOTSTRAP" == false ]]; then
    terraform init \
        -backend-config="bucket=$S3_BUCKET" \
        -backend-config="dynamodb_table=$DYNAMODB_TABLE" \
        -backend-config="region=$AWS_REGION"
else
    terraform init
fi

# Plan deployment
print_status "Planning Terraform deployment..."
terraform plan -var-file="terraform.tfvars" -out="tfplan"

# Apply deployment
print_status "Applying Terraform deployment..."
if [[ "$AUTO_APPROVE" == true ]]; then
    terraform apply -auto-approve "tfplan"
else
    terraform apply "tfplan"
fi

# Get deployment outputs
print_status "Retrieving deployment information..."

ARTICLES_TABLE=$(terraform output -raw articles_table_name)
CONTENT_BUCKET=$(terraform output -raw content_bucket_name)
STATE_MACHINE_ARN=$(terraform output -raw ingestion_state_machine_arn)

print_success "Infrastructure deployment completed!"

# Display deployment summary
echo ""
echo "=========================================="
echo "         DEPLOYMENT SUMMARY"
echo "=========================================="
echo "Environment: $ENVIRONMENT"
echo "AWS Account: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"
echo ""
echo "Key Resources:"
echo "  Articles Table: $ARTICLES_TABLE"
echo "  Content Bucket: $CONTENT_BUCKET"
echo "  State Machine: $STATE_MACHINE_ARN"
echo ""

# Display next steps
echo "Next Steps:"
echo "1. Configure RSS feeds in config/feeds.yaml"
echo "2. Update keywords in config/keywords.yaml"
echo "3. Set up SES email identities for notifications"
echo "4. Test the ingestion pipeline"
echo "5. Monitor CloudWatch dashboards"
echo ""

# Check if agents are enabled
AGENTS_ENABLED=$(terraform output -raw environment_variables | jq -r '.ENABLE_AGENTS')
if [[ "$AGENTS_ENABLED" == "true" ]]; then
    echo "6. Deploy Strands agents to Bedrock AgentCore"
else
    echo "6. Enable agents when ready with enable_agents=true"
fi

# Check if Amplify is enabled
AMPLIFY_ENABLED=$(terraform output -raw environment_variables | jq -r '.ENABLE_AMPLIFY')
if [[ "$AMPLIFY_ENABLED" == "true" ]]; then
    AMPLIFY_URL=$(terraform output -raw amplify_app_url)
    echo "7. Access web application at: $AMPLIFY_URL"
else
    echo "7. Enable Amplify when ready with enable_amplify=true"
fi

echo ""
print_success "Sentinel deployment completed successfully!"

cd ../../..