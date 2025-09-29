#!/bin/bash

# Sentinel CloudFormation Template Validation Script
# This script validates all CloudFormation templates and parameter files

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured or invalid"
    exit 1
fi

# Function to validate a CloudFormation template
validate_template() {
    local template_file=$1
    local template_name=$(basename "$template_file" .yaml)
    
    log_info "Validating template: $template_name"
    
    if aws cloudformation validate-template \
        --template-body "file://$template_file" \
        --region "$AWS_REGION" > /dev/null 2>&1; then
        log_success "✓ $template_name is valid"
        return 0
    else
        log_error "✗ $template_name validation failed"
        aws cloudformation validate-template \
            --template-body "file://$template_file" \
            --region "$AWS_REGION" 2>&1 | head -5
        return 1
    fi
}

# Function to validate parameter files
validate_parameters() {
    local param_file=$1
    local param_name=$(basename "$param_file" .json)
    
    log_info "Validating parameters: $param_name"
    
    if jq empty "$param_file" 2>/dev/null; then
        log_success "✓ $param_name JSON is valid"
        
        # Check for required parameters
        local required_params=("Environment" "ProjectName")
        local missing_params=()
        
        for param in "${required_params[@]}"; do
            if ! jq -e ".[] | select(.ParameterKey == \"$param\")" "$param_file" > /dev/null; then
                missing_params+=("$param")
            fi
        done
        
        if [[ ${#missing_params[@]} -eq 0 ]]; then
            log_success "✓ $param_name has all required parameters"
            return 0
        else
            log_warning "⚠ $param_name missing parameters: ${missing_params[*]}"
            return 1
        fi
    else
        log_error "✗ $param_name JSON is invalid"
        return 1
    fi
}

# Function to check template syntax with cfn-lint (if available)
check_cfn_lint() {
    if command -v cfn-lint &> /dev/null; then
        log_info "Running cfn-lint checks..."
        
        for template in "$SCRIPT_DIR"/*.yaml; do
            if [[ -f "$template" ]]; then
                local template_name=$(basename "$template" .yaml)
                log_info "Linting: $template_name"
                
                if cfn-lint "$template" --region "$AWS_REGION"; then
                    log_success "✓ $template_name passed cfn-lint"
                else
                    log_warning "⚠ $template_name has cfn-lint warnings"
                fi
            fi
        done
    else
        log_warning "cfn-lint not installed. Install with: pip install cfn-lint"
    fi
}

# Function to estimate costs (if available)
estimate_costs() {
    if command -v aws &> /dev/null; then
        log_info "Cost estimation not implemented in this script"
        log_info "Use AWS Cost Calculator or deploy to dev environment for cost analysis"
    fi
}

# Main validation process
main() {
    log_info "Starting CloudFormation template validation"
    log_info "Region: $AWS_REGION"
    echo
    
    local validation_errors=0
    
    # Validate CloudFormation templates
    log_info "=== Validating CloudFormation Templates ==="
    for template in "$SCRIPT_DIR"/*.yaml; do
        if [[ -f "$template" ]]; then
            if ! validate_template "$template"; then
                ((validation_errors++))
            fi
        fi
    done
    echo
    
    # Validate parameter files
    log_info "=== Validating Parameter Files ==="
    for param_file in "$SCRIPT_DIR"/parameters-*.json; do
        if [[ -f "$param_file" ]]; then
            if ! validate_parameters "$param_file"; then
                ((validation_errors++))
            fi
        fi
    done
    echo
    
    # Check with cfn-lint if available
    log_info "=== Additional Checks ==="
    check_cfn_lint
    echo
    
    # Summary
    log_info "=== Validation Summary ==="
    if [[ $validation_errors -eq 0 ]]; then
        log_success "All templates and parameters are valid!"
        log_info "Ready for deployment"
    else
        log_error "$validation_errors validation error(s) found"
        log_error "Please fix the errors before deployment"
        exit 1
    fi
    
    # Additional recommendations
    echo
    log_info "=== Deployment Recommendations ==="
    log_info "1. Test deployment in dev environment first"
    log_info "2. Review parameter values for your environment"
    log_info "3. Ensure Lambda packages are uploaded to S3"
    log_info "4. Verify SES email identities are configured"
    log_info "5. Check Bedrock model access in your region"
    
    echo
    log_info "To deploy, run:"
    log_info "  ./deploy.sh -e dev -a create"
    log_info "  ./deploy.sh -e prod -a create"
}

# Run main function
main "$@"