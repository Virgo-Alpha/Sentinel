#!/bin/bash

# Lambda Package Deployment Script for Sentinel
# This script builds and deploys Lambda function packages to S3

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

Build and deploy Lambda function packages for Sentinel

OPTIONS:
    -e, --environment ENV    Environment (dev, staging, prod)
    -b, --bucket BUCKET      S3 artifacts bucket name
    -s, --source-dir DIR     Source directory (default: ../src)
    -f, --function NAME      Deploy specific function only
    -c, --clean             Clean build artifacts after deployment
    -h, --help              Show this help message

EXAMPLES:
    # Deploy all functions to dev environment
    $0 -e dev -b sentinel-dev-artifacts-abc123

    # Deploy specific function
    $0 -e prod -b sentinel-prod-artifacts-xyz789 -f feed-parser

    # Clean deployment
    $0 -e dev -b sentinel-dev-artifacts-abc123 -c
EOF
}

# Parse command line arguments
ENVIRONMENT=""
BUCKET=""
SOURCE_DIR="../src"
SPECIFIC_FUNCTION=""
CLEAN_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -b|--bucket)
            BUCKET="$2"
            shift 2
            ;;
        -s|--source-dir)
            SOURCE_DIR="$2"
            shift 2
            ;;
        -f|--function)
            SPECIFIC_FUNCTION="$2"
            shift 2
            ;;
        -c|--clean)
            CLEAN_BUILD=true
            shift
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
if [[ -z "$ENVIRONMENT" ]]; then
    log_error "Environment is required"
    usage
    exit 1
fi

if [[ -z "$BUCKET" ]]; then
    log_error "S3 bucket name is required"
    usage
    exit 1
fi

# Check if source directory exists
if [[ ! -d "$SOURCE_DIR" ]]; then
    log_error "Source directory not found: $SOURCE_DIR"
    exit 1
fi

# Create build directory
BUILD_DIR="$SCRIPT_DIR/lambda-builds"
mkdir -p "$BUILD_DIR"

# Lambda function definitions
declare -A LAMBDA_FUNCTIONS=(
    ["feed-parser"]="lambda_tools/feed_parser"
    ["relevancy-evaluator"]="lambda_tools/relevancy_evaluator"
    ["dedup-tool"]="lambda_tools/dedup_tool"
    ["guardrail-tool"]="lambda_tools/guardrail_tool"
    ["storage-tool"]="lambda_tools/storage_tool"
    ["human-escalation"]="lambda_tools/human_escalation"
    ["notifier"]="lambda_tools/notifier"
    ["analyst-assistant"]="lambda_tools/analyst_assistant"
    ["query-kb"]="lambda_tools/query_kb"
    ["commentary-api"]="lambda_tools/commentary_api"
    ["publish-decision"]="lambda_tools/publish_decision"
)

# Function to build a Lambda package
build_lambda_package() {
    local function_name=$1
    local source_path=$2
    
    log_info "Building Lambda package: $function_name"
    
    local package_dir="$BUILD_DIR/$function_name"
    local zip_file="$BUILD_DIR/$function_name.zip"
    
    # Clean previous build
    rm -rf "$package_dir" "$zip_file"
    mkdir -p "$package_dir"
    
    # Copy source files
    if [[ -d "$SOURCE_DIR/$source_path" ]]; then
        cp -r "$SOURCE_DIR/$source_path"/* "$package_dir/"
    else
        log_error "Source path not found: $SOURCE_DIR/$source_path"
        return 1
    fi
    
    # Copy common utilities if they exist
    if [[ -d "$SOURCE_DIR/common" ]]; then
        cp -r "$SOURCE_DIR/common"/* "$package_dir/"
    fi
    
    # Install Python dependencies if requirements.txt exists
    if [[ -f "$package_dir/requirements.txt" ]]; then
        log_info "Installing Python dependencies for $function_name"
        pip install -r "$package_dir/requirements.txt" -t "$package_dir/" --no-deps
    fi
    
    # Create ZIP package
    cd "$package_dir"
    zip -r "$zip_file" . -x "*.pyc" "__pycache__/*" "*.git*" "requirements.txt"
    cd - > /dev/null
    
    log_success "Built package: $zip_file"
    return 0
}

# Function to upload package to S3
upload_package() {
    local function_name=$1
    local zip_file="$BUILD_DIR/$function_name.zip"
    
    if [[ ! -f "$zip_file" ]]; then
        log_error "Package not found: $zip_file"
        return 1
    fi
    
    log_info "Uploading $function_name to S3..."
    
    if aws s3 cp "$zip_file" "s3://$BUCKET/lambda-packages/$function_name.zip" \
        --region "$AWS_REGION"; then
        log_success "Uploaded: s3://$BUCKET/lambda-packages/$function_name.zip"
    else
        log_error "Failed to upload $function_name"
        return 1
    fi
}

# Function to update Lambda function code
update_lambda_function() {
    local function_name=$1
    local lambda_function_name="${PROJECT_NAME}-${ENVIRONMENT}-${function_name}"
    
    log_info "Updating Lambda function: $lambda_function_name"
    
    if aws lambda update-function-code \
        --function-name "$lambda_function_name" \
        --s3-bucket "$BUCKET" \
        --s3-key "lambda-packages/$function_name.zip" \
        --region "$AWS_REGION" > /dev/null; then
        log_success "Updated Lambda function: $lambda_function_name"
    else
        log_warning "Failed to update Lambda function: $lambda_function_name (function may not exist yet)"
    fi
}

# Main deployment logic
log_info "Starting Lambda package deployment"
log_info "Environment: $ENVIRONMENT"
log_info "S3 Bucket: $BUCKET"
log_info "Source Directory: $SOURCE_DIR"

# Check AWS credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    log_error "AWS credentials not configured or invalid"
    exit 1
fi

# Check if bucket exists
if ! aws s3 ls "s3://$BUCKET" > /dev/null 2>&1; then
    log_error "S3 bucket not found or not accessible: $BUCKET"
    exit 1
fi

# Deploy functions
if [[ -n "$SPECIFIC_FUNCTION" ]]; then
    # Deploy specific function
    if [[ -n "${LAMBDA_FUNCTIONS[$SPECIFIC_FUNCTION]}" ]]; then
        build_lambda_package "$SPECIFIC_FUNCTION" "${LAMBDA_FUNCTIONS[$SPECIFIC_FUNCTION]}"
        upload_package "$SPECIFIC_FUNCTION"
        update_lambda_function "$SPECIFIC_FUNCTION"
    else
        log_error "Unknown function: $SPECIFIC_FUNCTION"
        log_info "Available functions: ${!LAMBDA_FUNCTIONS[*]}"
        exit 1
    fi
else
    # Deploy all functions
    for function_name in "${!LAMBDA_FUNCTIONS[@]}"; do
        source_path="${LAMBDA_FUNCTIONS[$function_name]}"
        
        if build_lambda_package "$function_name" "$source_path"; then
            upload_package "$function_name"
            update_lambda_function "$function_name"
        else
            log_error "Failed to build $function_name"
        fi
    done
fi

# Clean up build artifacts if requested
if [[ "$CLEAN_BUILD" == true ]]; then
    log_info "Cleaning build artifacts..."
    rm -rf "$BUILD_DIR"
    log_success "Build artifacts cleaned"
fi

log_success "Lambda package deployment completed!"

# Show deployment summary
log_info "Deployment Summary:"
log_info "- Environment: $ENVIRONMENT"
log_info "- S3 Bucket: $BUCKET"
log_info "- Functions deployed: ${SPECIFIC_FUNCTION:-"all functions"}"
log_info "- Next steps:"
log_info "  1. Deploy/update CloudFormation stack"
log_info "  2. Test Lambda functions"
log_info "  3. Monitor CloudWatch logs"