#!/bin/bash

# Sentinel Cybersecurity Triage System - Deployment Script
# This script deploys the complete infrastructure stack using Terraform

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
INFRA_DIR="$PROJECT_ROOT/infra"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/deployment_$TIMESTAMP.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="dev"
AUTO_APPROVE=false
DESTROY=false
VALIDATE_ONLY=false
SKIP_BOOTSTRAP=false
VERBOSE=false

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy Sentinel Cybersecurity Triage System infrastructure

OPTIONS:
    -e, --environment ENV    Target environment (dev|staging|prod) [default: dev]
    -a, --auto-approve      Auto-approve Terraform changes (skip confirmation)
    -d, --destroy           Destroy infrastructure instead of creating
    -v, --validate-only     Only validate Terraform configuration
    -s, --skip-bootstrap    Skip Terraform backend bootstrap
    --verbose               Enable verbose output
    -h, --help              Show this help message

EXAMPLES:
    $0                                    # Deploy to dev environment
    $0 -e prod -a                        # Deploy to prod with auto-approve
    $0 -d -e dev                         # Destroy dev environment
    $0 -v                                # Validate configuration only
    $0 -e staging --verbose              # Deploy to staging with verbose output

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -a|--auto-approve)
            AUTO_APPROVE=true
            shift
            ;;
        -d|--destroy)
            DESTROY=true
            shift
            ;;
        -v|--validate-only)
            VALIDATE_ONLY=true
            shift
            ;;
        -s|--skip-bootstrap)
            SKIP_BOOTSTRAP=true
            shift
            ;;
        --verbose)
            VERBOSE=true
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
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    print_error "Invalid environment: $ENVIRONMENT. Must be dev, staging, or prod."
    exit 1
fi

# Create log directory
mkdir -p "$LOG_DIR"

print_status "Starting Sentinel deployment for environment: $ENVIRONMENT"
print_status "Log file: $LOG_FILE"

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if required tools are installed
    local required_tools=("terraform" "aws" "jq" "python3")
    local missing_tools=()
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_error "Please install the missing tools and try again."
        exit 1
    fi
    
    # Check Terraform version
    local tf_version=$(terraform version -json | jq -r '.terraform_version')
    print_status "Terraform version: $tf_version"
    
    # Check AWS CLI configuration
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI is not configured or credentials are invalid."
        print_error "Please run 'aws configure' or set up AWS credentials."
        exit 1
    fi
    
    local aws_account=$(aws sts get-caller-identity --query Account --output text)
    local aws_region=$(aws configure get region)
    print_status "AWS Account: $aws_account"
    print_status "AWS Region: $aws_region"
    
    # Check if environment-specific variables file exists
    local env_vars_file="$INFRA_DIR/envs/$ENVIRONMENT.tfvars"
    if [[ ! -f "$env_vars_file" ]]; then
        print_error "Environment variables file not found: $env_vars_file"
        exit 1
    fi
    
    print_success "Prerequisites check completed"
}

# Function to bootstrap Terraform backend
bootstrap_terraform() {
    if [[ "$SKIP_BOOTSTRAP" == "true" ]]; then
        print_status "Skipping Terraform backend bootstrap"
        return 0
    fi
    
    print_status "Bootstrapping Terraform backend..."
    
    cd "$INFRA_DIR/bootstrap"
    
    # Initialize bootstrap
    terraform init
    
    # Plan bootstrap
    terraform plan -var="environment=$ENVIRONMENT" -out=bootstrap.tfplan
    
    # Apply bootstrap
    if [[ "$AUTO_APPROVE" == "true" ]]; then
        terraform apply -auto-approve bootstrap.tfplan
    else
        terraform apply bootstrap.tfplan
    fi
    
    # Get backend configuration
    local bucket_name=$(terraform output -raw s3_bucket_name)
    local dynamodb_table=$(terraform output -raw dynamodb_table_name)
    local kms_key_id=$(terraform output -raw kms_key_id)
    
    print_success "Terraform backend bootstrapped successfully"
    print_status "S3 Bucket: $bucket_name"
    print_status "DynamoDB Table: $dynamodb_table"
    print_status "KMS Key: $kms_key_id"
    
    cd "$INFRA_DIR"
}

# Function to validate Terraform configuration
validate_terraform() {
    print_status "Validating Terraform configuration..."
    
    cd "$INFRA_DIR"
    
    # Format check
    if ! terraform fmt -check=true -diff=true; then
        print_warning "Terraform files are not properly formatted"
        if [[ "$VERBOSE" == "true" ]]; then
            terraform fmt -diff=true
        fi
    fi
    
    # Initialize Terraform
    terraform init -backend-config="key=sentinel-$ENVIRONMENT/terraform.tfstate"
    
    # Validate configuration
    terraform validate
    
    # Security scan (if tfsec is available)
    if command -v tfsec &> /dev/null; then
        print_status "Running security scan with tfsec..."
        tfsec . --soft-fail || print_warning "Security scan found issues"
    fi
    
    print_success "Terraform configuration validation completed"
}

# Function to plan Terraform deployment
plan_terraform() {
    print_status "Planning Terraform deployment..."
    
    cd "$INFRA_DIR"
    
    local plan_file="terraform-$ENVIRONMENT-$TIMESTAMP.tfplan"
    local plan_output="$LOG_DIR/terraform-plan-$ENVIRONMENT-$TIMESTAMP.txt"
    
    # Create Terraform plan
    terraform plan \
        -var-file="envs/$ENVIRONMENT.tfvars" \
        -out="$plan_file" \
        -detailed-exitcode \
        | tee "$plan_output"
    
    local plan_exit_code=$?
    
    case $plan_exit_code in
        0)
            print_status "No changes required"
            ;;
        1)
            print_error "Terraform plan failed"
            exit 1
            ;;
        2)
            print_status "Changes detected and planned"
            ;;
    esac
    
    # Show plan summary
    print_status "Plan summary saved to: $plan_output"
    
    if [[ "$VERBOSE" == "true" ]]; then
        terraform show -no-color "$plan_file" | head -50
    fi
    
    echo "$plan_file"  # Return plan file name
}

# Function to apply Terraform deployment
apply_terraform() {
    local plan_file="$1"
    
    print_status "Applying Terraform deployment..."
    
    cd "$INFRA_DIR"
    
    local apply_output="$LOG_DIR/terraform-apply-$ENVIRONMENT-$TIMESTAMP.txt"
    
    # Apply Terraform plan
    if [[ "$AUTO_APPROVE" == "true" ]]; then
        terraform apply -auto-approve "$plan_file" | tee "$apply_output"
    else
        terraform apply "$plan_file" | tee "$apply_output"
    fi
    
    if [[ $? -eq 0 ]]; then
        print_success "Terraform deployment completed successfully"
    else
        print_error "Terraform deployment failed"
        exit 1
    fi
    
    # Save outputs
    local outputs_file="$LOG_DIR/terraform-outputs-$ENVIRONMENT-$TIMESTAMP.json"
    terraform output -json > "$outputs_file"
    print_status "Terraform outputs saved to: $outputs_file"
}

# Function to destroy Terraform infrastructure
destroy_terraform() {
    print_status "Destroying Terraform infrastructure..."
    
    cd "$INFRA_DIR"
    
    local destroy_output="$LOG_DIR/terraform-destroy-$ENVIRONMENT-$TIMESTAMP.txt"
    
    # Destroy infrastructure
    if [[ "$AUTO_APPROVE" == "true" ]]; then
        terraform destroy \
            -var-file="envs/$ENVIRONMENT.tfvars" \
            -auto-approve | tee "$destroy_output"
    else
        terraform destroy \
            -var-file="envs/$ENVIRONMENT.tfvars" | tee "$destroy_output"
    fi
    
    if [[ $? -eq 0 ]]; then
        print_success "Infrastructure destroyed successfully"
    else
        print_error "Infrastructure destruction failed"
        exit 1
    fi
}

# Function to validate deployed resources
validate_deployment() {
    print_status "Validating deployed resources..."
    
    cd "$INFRA_DIR"
    
    # Get Terraform outputs
    local outputs=$(terraform output -json)
    
    # Validate VPC
    local vpc_id=$(echo "$outputs" | jq -r '.vpc_id.value // empty')
    if [[ -n "$vpc_id" ]]; then
        if aws ec2 describe-vpcs --vpc-ids "$vpc_id" &> /dev/null; then
            print_success "VPC validation passed: $vpc_id"
        else
            print_error "VPC validation failed: $vpc_id"
        fi
    fi
    
    # Validate DynamoDB tables
    local articles_table=$(echo "$outputs" | jq -r '.articles_table_name.value // empty')
    if [[ -n "$articles_table" ]]; then
        if aws dynamodb describe-table --table-name "$articles_table" &> /dev/null; then
            print_success "DynamoDB Articles table validation passed: $articles_table"
        else
            print_error "DynamoDB Articles table validation failed: $articles_table"
        fi
    fi
    
    # Validate S3 buckets
    local s3_bucket=$(echo "$outputs" | jq -r '.s3_bucket_name.value // empty')
    if [[ -n "$s3_bucket" ]]; then
        if aws s3api head-bucket --bucket "$s3_bucket" &> /dev/null; then
            print_success "S3 bucket validation passed: $s3_bucket"
        else
            print_error "S3 bucket validation failed: $s3_bucket"
        fi
    fi
    
    # Validate Lambda functions
    local lambda_functions=$(echo "$outputs" | jq -r '.lambda_function_names.value[]? // empty')
    for func in $lambda_functions; do
        if aws lambda get-function --function-name "$func" &> /dev/null; then
            print_success "Lambda function validation passed: $func"
        else
            print_error "Lambda function validation failed: $func"
        fi
    done
    
    # Validate OpenSearch Serverless collection
    local opensearch_collection=$(echo "$outputs" | jq -r '.opensearch_collection_name.value // empty')
    if [[ -n "$opensearch_collection" ]]; then
        if aws opensearchserverless batch-get-collection --names "$opensearch_collection" &> /dev/null; then
            print_success "OpenSearch Serverless collection validation passed: $opensearch_collection"
        else
            print_error "OpenSearch Serverless collection validation failed: $opensearch_collection"
        fi
    fi
    
    print_success "Resource validation completed"
}

# Function to test Lambda functions
test_lambda_functions() {
    print_status "Testing Lambda function deployments..."
    
    cd "$INFRA_DIR"
    
    # Get Lambda function names from Terraform outputs
    local outputs=$(terraform output -json)
    local lambda_functions=$(echo "$outputs" | jq -r '.lambda_function_names.value[]? // empty')
    
    for func in $lambda_functions; do
        print_status "Testing Lambda function: $func"
        
        # Create test event
        local test_event='{
            "test": true,
            "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
            "environment": "'$ENVIRONMENT'"
        }'
        
        # Invoke function
        local response=$(aws lambda invoke \
            --function-name "$func" \
            --payload "$test_event" \
            --cli-binary-format raw-in-base64-out \
            /tmp/lambda-response-$func.json 2>&1)
        
        if [[ $? -eq 0 ]]; then
            local status_code=$(echo "$response" | jq -r '.StatusCode // 0')
            if [[ "$status_code" == "200" ]]; then
                print_success "Lambda function test passed: $func"
            else
                print_warning "Lambda function test returned status $status_code: $func"
            fi
        else
            print_error "Lambda function test failed: $func"
            echo "$response" | tee -a "$LOG_FILE"
        fi
    done
}

# Function to verify IAM permissions
verify_iam_permissions() {
    print_status "Verifying IAM permissions..."
    
    cd "$INFRA_DIR"
    
    # Get IAM role ARNs from Terraform outputs
    local outputs=$(terraform output -json)
    local lambda_roles=$(echo "$outputs" | jq -r '.lambda_execution_roles.value[]? // empty')
    
    for role_arn in $lambda_roles; do
        local role_name=$(basename "$role_arn")
        print_status "Checking IAM role: $role_name"
        
        # Check if role exists and get attached policies
        if aws iam get-role --role-name "$role_name" &> /dev/null; then
            local attached_policies=$(aws iam list-attached-role-policies --role-name "$role_name" --query 'AttachedPolicies[].PolicyArn' --output text)
            print_success "IAM role verified: $role_name"
            if [[ "$VERBOSE" == "true" ]]; then
                echo "  Attached policies: $attached_policies" | tee -a "$LOG_FILE"
            fi
        else
            print_error "IAM role not found: $role_name"
        fi
    done
}

# Function to check VPC endpoints
check_vpc_endpoints() {
    print_status "Checking VPC endpoints..."
    
    cd "$INFRA_DIR"
    
    # Get VPC ID from Terraform outputs
    local outputs=$(terraform output -json)
    local vpc_id=$(echo "$outputs" | jq -r '.vpc_id.value // empty')
    
    if [[ -n "$vpc_id" ]]; then
        local endpoints=$(aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=$vpc_id" --query 'VpcEndpoints[].ServiceName' --output text)
        
        if [[ -n "$endpoints" ]]; then
            print_success "VPC endpoints found:"
            for endpoint in $endpoints; do
                echo "  - $endpoint" | tee -a "$LOG_FILE"
            done
        else
            print_warning "No VPC endpoints found for VPC: $vpc_id"
        fi
    else
        print_warning "VPC ID not found in Terraform outputs"
    fi
}

# Function to generate deployment report
generate_deployment_report() {
    print_status "Generating deployment report..."
    
    local report_file="$LOG_DIR/deployment-report-$ENVIRONMENT-$TIMESTAMP.json"
    
    cd "$INFRA_DIR"
    
    # Get Terraform outputs
    local outputs=$(terraform output -json 2>/dev/null || echo '{}')
    
    # Create deployment report
    cat > "$report_file" << EOF
{
    "deployment": {
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "environment": "$ENVIRONMENT",
        "terraform_version": "$(terraform version -json | jq -r '.terraform_version')",
        "aws_account": "$(aws sts get-caller-identity --query Account --output text)",
        "aws_region": "$(aws configure get region)",
        "deployment_user": "$(aws sts get-caller-identity --query Arn --output text)"
    },
    "terraform_outputs": $outputs,
    "validation_results": {
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "status": "completed"
    }
}
EOF
    
    print_success "Deployment report generated: $report_file"
}

# Main execution flow
main() {
    print_status "Sentinel Cybersecurity Triage System Deployment"
    print_status "================================================"
    
    # Check prerequisites
    check_prerequisites
    
    if [[ "$VALIDATE_ONLY" == "true" ]]; then
        validate_terraform
        print_success "Validation completed successfully"
        exit 0
    fi
    
    if [[ "$DESTROY" == "true" ]]; then
        print_warning "DESTROYING infrastructure for environment: $ENVIRONMENT"
        read -p "Are you sure you want to destroy the infrastructure? (yes/no): " -r
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            print_status "Destruction cancelled"
            exit 0
        fi
        
        validate_terraform
        destroy_terraform
        print_success "Infrastructure destruction completed"
        exit 0
    fi
    
    # Bootstrap Terraform backend
    bootstrap_terraform
    
    # Validate Terraform configuration
    validate_terraform
    
    # Plan deployment
    local plan_file=$(plan_terraform)
    
    # Apply deployment
    apply_terraform "$plan_file"
    
    # Validate deployment
    validate_deployment
    
    # Test Lambda functions
    test_lambda_functions
    
    # Verify IAM permissions
    verify_iam_permissions
    
    # Check VPC endpoints
    check_vpc_endpoints
    
    # Generate deployment report
    generate_deployment_report
    
    print_success "Deployment completed successfully!"
    print_status "Environment: $ENVIRONMENT"
    print_status "Log file: $LOG_FILE"
    print_status "Next steps:"
    print_status "  1. Configure RSS feeds using: scripts/configure-feeds.sh"
    print_status "  2. Run end-to-end validation: scripts/validate-system.sh"
    print_status "  3. Access web application at the provided URL"
}

# Trap to handle script interruption
trap 'print_error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@"