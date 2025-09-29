#!/bin/bash

# Sentinel CloudFormation Deployment Script
# This script deploys the Sentinel infrastructure using AWS CloudFormation

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="sentinel"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage function
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy Sentinel infrastructure using CloudFormation

OPTIONS:
    -e, --environment ENV    Environment to deploy (dev, staging, prod)
    -t, --template TEMPLATE  Template to deploy (complete, vpc, storage)
    -a, --action ACTION      Action to perform (create, update, delete, validate)
    -r, --region REGION      AWS region (default: us-east-1)
    -s, --stack-name NAME    Custom stack name
    -p, --parameters FILE    Custom parameters file
    -h, --help              Show this help message

EXAMPLES:
    # Deploy complete dev environment
    $0 -e dev -a create

    # Update production environment
    $0 -e prod -a update

    # Deploy only VPC components
    $0 -e dev -t vpc -a create

    # Validate template
    $0 -t complete -a validate

    # Delete stack (be careful!)
    $0 -e dev -a delete
EOF
}

# Parse command line arguments
ENVIRONMENT=""
TEMPLATE="complete"
ACTION="create"
STACK_NAME=""
PARAMETERS_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--template)
            TEMPLATE="$2"
            shift 2
            ;;
        -a|--action)
            ACTION="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -s|--stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        -p|--parameters)
            PARAMETERS_FILE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ "$ACTION" != "validate" && -z "$ENVIRONMENT" ]]; then
    log_error "Environment is required for $ACTION action"
    usage
    exit 1
fi

# Set default stack name if not provided
if [[ -z "$STACK_NAME" ]]; then
    if [[ -n "$ENVIRONMENT" ]]; then
        STACK_NAME="${PROJECT_NAME}-${ENVIRONMENT}-${TEMPLATE}"
    else
        STACK_NAME="${PROJECT_NAME}-${TEMPLATE}"
    fi
fi

# Set template file based on template type
case $TEMPLATE in
    complete)
        TEMPLATE_FILE="$SCRIPT_DIR/sentinel-infrastructure-complete.yaml"
        ;;
    vpc)
        TEMPLATE_FILE="$SCRIPT_DIR/sentinel-vpc-networking.yaml"
        ;;
    storage)
        TEMPLATE_FILE="$SCRIPT_DIR/sentinel-storage.yaml"
        ;;
    *)
        log_error "Unknown template type: $TEMPLATE"
        exit 1
        ;;
esac

# Set parameters file if not provided
if [[ -z "$PARAMETERS_FILE" && -n "$ENVIRONMENT" ]]; then
    PARAMETERS_FILE="$SCRIPT_DIR/parameters-${ENVIRONMENT}.json"
fi

# Validate files exist
if [[ ! -f "$TEMPLATE_FILE" ]]; then
    log_error "Template file not found: $TEMPLATE_FILE"
    exit 1
fi

if [[ -n "$PARAMETERS_FILE" && ! -f "$PARAMETERS_FILE" ]]; then
    log_error "Parameters file not found: $PARAMETERS_FILE"
    exit 1
fi

# Check AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed"
    exit 1
fi

# Validate AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured or invalid"
    exit 1
fi

# Function to validate template
validate_template() {
    log_info "Validating CloudFormation template: $TEMPLATE_FILE"
    
    if aws cloudformation validate-template \
        --template-body "file://$TEMPLATE_FILE" \
        --region "$AWS_REGION" > /dev/null; then
        log_success "Template validation successful"
    else
        log_error "Template validation failed"
        exit 1
    fi
}

# Function to check if stack exists
stack_exists() {
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].StackStatus' \
        --output text 2>/dev/null || echo "DOES_NOT_EXIST"
}

# Function to wait for stack operation to complete
wait_for_stack() {
    local operation=$1
    log_info "Waiting for stack $operation to complete..."
    
    if aws cloudformation wait "stack-${operation}-complete" \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION"; then
        log_success "Stack $operation completed successfully"
    else
        log_error "Stack $operation failed"
        
        # Show recent stack events on failure
        log_info "Recent stack events:"
        aws cloudformation describe-stack-events \
            --stack-name "$STACK_NAME" \
            --region "$AWS_REGION" \
            --max-items 10 \
            --query 'StackEvents[?ResourceStatus==`CREATE_FAILED` || ResourceStatus==`UPDATE_FAILED`].[Timestamp,ResourceType,LogicalResourceId,ResourceStatusReason]' \
            --output table
        
        exit 1
    fi
}

# Function to create stack
create_stack() {
    local stack_status
    stack_status=$(stack_exists)
    
    if [[ "$stack_status" != "DOES_NOT_EXIST" ]]; then
        log_error "Stack $STACK_NAME already exists with status: $stack_status"
        exit 1
    fi
    
    log_info "Creating CloudFormation stack: $STACK_NAME"
    
    local create_cmd="aws cloudformation create-stack \
        --stack-name $STACK_NAME \
        --template-body file://$TEMPLATE_FILE \
        --capabilities CAPABILITY_NAMED_IAM \
        --region $AWS_REGION"
    
    if [[ -n "$PARAMETERS_FILE" ]]; then
        create_cmd="$create_cmd --parameters file://$PARAMETERS_FILE"
    fi
    
    if eval "$create_cmd"; then
        wait_for_stack "create"
        show_outputs
    else
        log_error "Failed to create stack"
        exit 1
    fi
}

# Function to update stack
update_stack() {
    local stack_status
    stack_status=$(stack_exists)
    
    if [[ "$stack_status" == "DOES_NOT_EXIST" ]]; then
        log_error "Stack $STACK_NAME does not exist. Use create action instead."
        exit 1
    fi
    
    log_info "Updating CloudFormation stack: $STACK_NAME"
    
    local update_cmd="aws cloudformation update-stack \
        --stack-name $STACK_NAME \
        --template-body file://$TEMPLATE_FILE \
        --capabilities CAPABILITY_NAMED_IAM \
        --region $AWS_REGION"
    
    if [[ -n "$PARAMETERS_FILE" ]]; then
        update_cmd="$update_cmd --parameters file://$PARAMETERS_FILE"
    fi
    
    if eval "$update_cmd" 2>/dev/null; then
        wait_for_stack "update"
        show_outputs
    else
        local exit_code=$?
        if [[ $exit_code -eq 254 ]]; then
            log_warning "No updates to be performed on stack $STACK_NAME"
        else
            log_error "Failed to update stack"
            exit 1
        fi
    fi
}

# Function to delete stack
delete_stack() {
    local stack_status
    stack_status=$(stack_exists)
    
    if [[ "$stack_status" == "DOES_NOT_EXIST" ]]; then
        log_warning "Stack $STACK_NAME does not exist"
        return 0
    fi
    
    # Confirmation prompt for delete
    log_warning "This will DELETE the stack $STACK_NAME and ALL its resources!"
    read -p "Are you sure you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Delete operation cancelled"
        exit 0
    fi
    
    log_info "Deleting CloudFormation stack: $STACK_NAME"
    
    if aws cloudformation delete-stack \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION"; then
        wait_for_stack "delete"
    else
        log_error "Failed to delete stack"
        exit 1
    fi
}

# Function to show stack outputs
show_outputs() {
    log_info "Stack outputs:"
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey && OutputValue].[OutputKey,OutputValue]' \
        --output table 2>/dev/null || log_warning "No outputs available"
}

# Function to show stack status
show_status() {
    local stack_status
    stack_status=$(stack_exists)
    
    if [[ "$stack_status" == "DOES_NOT_EXIST" ]]; then
        log_info "Stack $STACK_NAME does not exist"
    else
        log_info "Stack $STACK_NAME status: $stack_status"
        show_outputs
    fi
}

# Main execution
log_info "Starting CloudFormation deployment"
log_info "Environment: ${ENVIRONMENT:-N/A}"
log_info "Template: $TEMPLATE"
log_info "Action: $ACTION"
log_info "Stack Name: $STACK_NAME"
log_info "Region: $AWS_REGION"

# Always validate template first
validate_template

# Execute the requested action
case $ACTION in
    create)
        create_stack
        ;;
    update)
        update_stack
        ;;
    delete)
        delete_stack
        ;;
    validate)
        log_success "Template validation completed"
        ;;
    status)
        show_status
        ;;
    *)
        log_error "Unknown action: $ACTION"
        usage
        exit 1
        ;;
esac

log_success "CloudFormation deployment completed successfully!"