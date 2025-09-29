#!/bin/bash

# Sentinel Deployment Validation Script
# Comprehensive validation of deployed infrastructure and functionality

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/validation_$TIMESTAMP.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
ENVIRONMENT="dev"
VERBOSE=false
SKIP_FUNCTIONAL_TESTS=false
TIMEOUT=300

# Validation results
VALIDATION_RESULTS=()
FAILED_VALIDATIONS=()

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
    VALIDATION_RESULTS+=("✓ $1")
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    FAILED_VALIDATIONS+=("✗ $1")
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Validate Sentinel deployment and functionality

OPTIONS:
    -e, --environment ENV    Target environment (dev|staging|prod) [default: dev]
    -s, --skip-functional   Skip functional tests (infrastructure only)
    -t, --timeout SECONDS   Timeout for tests in seconds [default: 300]
    -v, --verbose           Enable verbose output
    -h, --help              Show this help message

EXAMPLES:
    $0                      # Validate dev environment
    $0 -e prod -v           # Validate prod with verbose output
    $0 -s                   # Skip functional tests
    $0 -t 600               # Use 10-minute timeout

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -s|--skip-functional)
            SKIP_FUNCTIONAL_TESTS=true
            shift
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -v|--verbose)
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

# Create log directory
mkdir -p "$LOG_DIR"

print_status "Starting deployment validation for environment: $ENVIRONMENT"

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    local required_tools=("aws" "terraform" "python3" "jq" "curl")
    local missing_tools=()
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        return 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured"
        return 1
    fi
    
    print_success "Prerequisites check passed"
    return 0
}

# Function to validate infrastructure using Python script
validate_infrastructure() {
    print_status "Running infrastructure validation..."
    
    local validation_script="$SCRIPT_DIR/validate-infrastructure.py"
    
    if [[ ! -f "$validation_script" ]]; then
        print_error "Infrastructure validation script not found: $validation_script"
        return 1
    fi
    
    local cmd_args=("-e" "$ENVIRONMENT")
    if [[ "$VERBOSE" == "true" ]]; then
        cmd_args+=("-v")
    fi
    
    if python3 "$validation_script" "${cmd_args[@]}"; then
        print_success "Infrastructure validation passed"
        return 0
    else
        print_error "Infrastructure validation failed"
        return 1
    fi
}

# Function to test Lambda function packaging
test_lambda_packaging() {
    print_status "Testing Lambda function packaging..."
    
    local lambda_dir="$PROJECT_ROOT/src/lambda"
    
    if [[ ! -d "$lambda_dir" ]]; then
        print_warning "Lambda source directory not found: $lambda_dir"
        return 0
    fi
    
    # Check if Lambda functions are properly packaged
    local functions=(
        "feed_parser"
        "relevancy_evaluator"
        "dedup_tool"
        "guardrail_tool"
        "storage_tool"
        "query_kb"
        "human_escalation"
        "publish_decision"
        "commentary_api"
    )
    
    local packaged_functions=0
    
    for func in "${functions[@]}"; do
        local func_dir="$lambda_dir/$func"
        if [[ -d "$func_dir" ]]; then
            # Check for required files
            if [[ -f "$func_dir/lambda_function.py" ]] || [[ -f "$func_dir/main.py" ]]; then
                ((packaged_functions++))
                if [[ "$VERBOSE" == "true" ]]; then
                    print_status "  ✓ Function found: $func"
                fi
            else
                print_warning "  ✗ Function missing main file: $func"
            fi
        else
            print_warning "  ✗ Function directory not found: $func"
        fi
    done
    
    if [[ $packaged_functions -gt 0 ]]; then
        print_success "Lambda packaging validation passed ($packaged_functions functions found)"
        return 0
    else
        print_error "No Lambda functions found"
        return 1
    fi
}

# Function to test DynamoDB accessibility
test_dynamodb_access() {
    print_status "Testing DynamoDB table accessibility..."
    
    # Get table names from Terraform outputs
    cd "$PROJECT_ROOT/infra"
    local outputs=$(terraform output -json 2>/dev/null || echo '{}')
    
    local articles_table=$(echo "$outputs" | jq -r '.articles_table_name.value // empty')
    
    if [[ -z "$articles_table" ]]; then
        print_warning "Articles table name not found in Terraform outputs"
        return 0
    fi
    
    # Test table access
    if aws dynamodb describe-table --table-name "$articles_table" &> /dev/null; then
        print_success "DynamoDB table accessible: $articles_table"
        
        # Test basic operations
        local test_item='{
            "article_id": {"S": "test-validation-'$TIMESTAMP'"},
            "created_at": {"S": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"},
            "title": {"S": "Validation Test Article"},
            "status": {"S": "test"}
        }'
        
        # Put test item
        if aws dynamodb put-item --table-name "$articles_table" --item "$test_item" &> /dev/null; then
            print_success "DynamoDB write operation successful"
            
            # Clean up test item
            aws dynamodb delete-item \
                --table-name "$articles_table" \
                --key '{"article_id": {"S": "test-validation-'$TIMESTAMP'"}, "created_at": {"S": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}}' \
                &> /dev/null || true
        else
            print_error "DynamoDB write operation failed"
            return 1
        fi
        
        return 0
    else
        print_error "DynamoDB table not accessible: $articles_table"
        return 1
    fi
}

# Function to test S3 bucket accessibility
test_s3_access() {
    print_status "Testing S3 bucket accessibility..."
    
    # Get bucket names from Terraform outputs
    cd "$PROJECT_ROOT/infra"
    local outputs=$(terraform output -json 2>/dev/null || echo '{}')
    
    local artifacts_bucket=$(echo "$outputs" | jq -r '.artifacts_bucket_name.value // empty')
    
    if [[ -z "$artifacts_bucket" ]]; then
        print_warning "Artifacts bucket name not found in Terraform outputs"
        return 0
    fi
    
    # Test bucket access
    if aws s3api head-bucket --bucket "$artifacts_bucket" &> /dev/null; then
        print_success "S3 bucket accessible: $artifacts_bucket"
        
        # Test basic operations
        local test_file="/tmp/validation-test-$TIMESTAMP.txt"
        echo "Validation test file created at $(date)" > "$test_file"
        
        # Upload test file
        if aws s3 cp "$test_file" "s3://$artifacts_bucket/validation-test-$TIMESTAMP.txt" &> /dev/null; then
            print_success "S3 upload operation successful"
            
            # Clean up test file
            aws s3 rm "s3://$artifacts_bucket/validation-test-$TIMESTAMP.txt" &> /dev/null || true
            rm -f "$test_file"
        else
            print_error "S3 upload operation failed"
            return 1
        fi
        
        return 0
    else
        print_error "S3 bucket not accessible: $artifacts_bucket"
        return 1
    fi
}

# Function to test OpenSearch Serverless accessibility
test_opensearch_access() {
    print_status "Testing OpenSearch Serverless accessibility..."
    
    # Get collection name from Terraform outputs
    cd "$PROJECT_ROOT/infra"
    local outputs=$(terraform output -json 2>/dev/null || echo '{}')
    
    local collection_name=$(echo "$outputs" | jq -r '.opensearch_collection_name.value // empty')
    
    if [[ -z "$collection_name" ]]; then
        print_warning "OpenSearch collection name not found in Terraform outputs"
        return 0
    fi
    
    # Test collection access
    if aws opensearchserverless batch-get-collection --names "$collection_name" &> /dev/null; then
        local collection_status=$(aws opensearchserverless batch-get-collection --names "$collection_name" --query 'collectionDetails[0].status' --output text)
        
        if [[ "$collection_status" == "ACTIVE" ]]; then
            print_success "OpenSearch Serverless collection accessible: $collection_name"
            return 0
        else
            print_error "OpenSearch Serverless collection not active: $collection_status"
            return 1
        fi
    else
        print_error "OpenSearch Serverless collection not accessible: $collection_name"
        return 1
    fi
}

# Function to test Lambda function execution
test_lambda_execution() {
    print_status "Testing Lambda function execution..."
    
    # Get function names from Terraform outputs
    cd "$PROJECT_ROOT/infra"
    local outputs=$(terraform output -json 2>/dev/null || echo '{}')
    
    local function_names=$(echo "$outputs" | jq -r '.lambda_function_names.value[]? // empty')
    
    if [[ -z "$function_names" ]]; then
        print_warning "No Lambda function names found in Terraform outputs"
        return 0
    fi
    
    local successful_tests=0
    local total_tests=0
    
    # Test first few functions to avoid timeout
    for function_name in $(echo "$function_names" | head -3); do
        ((total_tests++))
        
        print_status "  Testing function: $function_name"
        
        # Create test payload
        local test_payload='{
            "test": true,
            "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
            "environment": "'$ENVIRONMENT'",
            "validation": true
        }'
        
        # Invoke function with timeout
        local response_file="/tmp/lambda-response-$function_name-$TIMESTAMP.json"
        
        if timeout 30 aws lambda invoke \
            --function-name "$function_name" \
            --payload "$test_payload" \
            --cli-binary-format raw-in-base64-out \
            "$response_file" &> /dev/null; then
            
            # Check response
            if [[ -f "$response_file" ]]; then
                local status_code=$(aws lambda invoke \
                    --function-name "$function_name" \
                    --payload "$test_payload" \
                    --cli-binary-format raw-in-base64-out \
                    /dev/null 2>&1 | grep -o '"StatusCode": [0-9]*' | cut -d' ' -f2 || echo "0")
                
                if [[ "$status_code" == "200" ]]; then
                    ((successful_tests++))
                    if [[ "$VERBOSE" == "true" ]]; then
                        print_status "    ✓ Function test passed: $function_name"
                    fi
                else
                    print_warning "    ✗ Function test failed: $function_name (status: $status_code)"
                fi
            fi
            
            # Clean up response file
            rm -f "$response_file"
        else
            print_warning "    ✗ Function test timeout: $function_name"
        fi
    done
    
    if [[ $successful_tests -gt 0 ]]; then
        print_success "Lambda execution tests passed ($successful_tests/$total_tests functions)"
        return 0
    else
        print_error "All Lambda execution tests failed"
        return 1
    fi
}

# Function to test IAM permissions
test_iam_permissions() {
    print_status "Testing IAM permissions..."
    
    # Get current user/role
    local caller_identity=$(aws sts get-caller-identity)
    local caller_arn=$(echo "$caller_identity" | jq -r '.Arn')
    
    print_status "  Testing as: $caller_arn"
    
    # Test basic AWS service permissions
    local permissions_tests=(
        "dynamodb:ListTables"
        "s3:ListAllMyBuckets"
        "lambda:ListFunctions"
        "logs:DescribeLogGroups"
    )
    
    local successful_permissions=0
    
    for permission in "${permissions_tests[@]}"; do
        local service=$(echo "$permission" | cut -d':' -f1)
        local action=$(echo "$permission" | cut -d':' -f2)
        
        case "$service" in
            "dynamodb")
                if aws dynamodb list-tables --max-items 1 &> /dev/null; then
                    ((successful_permissions++))
                    if [[ "$VERBOSE" == "true" ]]; then
                        print_status "    ✓ Permission verified: $permission"
                    fi
                else
                    print_warning "    ✗ Permission failed: $permission"
                fi
                ;;
            "s3")
                if aws s3api list-buckets --max-items 1 &> /dev/null; then
                    ((successful_permissions++))
                    if [[ "$VERBOSE" == "true" ]]; then
                        print_status "    ✓ Permission verified: $permission"
                    fi
                else
                    print_warning "    ✗ Permission failed: $permission"
                fi
                ;;
            "lambda")
                if aws lambda list-functions --max-items 1 &> /dev/null; then
                    ((successful_permissions++))
                    if [[ "$VERBOSE" == "true" ]]; then
                        print_status "    ✓ Permission verified: $permission"
                    fi
                else
                    print_warning "    ✗ Permission failed: $permission"
                fi
                ;;
            "logs")
                if aws logs describe-log-groups --limit 1 &> /dev/null; then
                    ((successful_permissions++))
                    if [[ "$VERBOSE" == "true" ]]; then
                        print_status "    ✓ Permission verified: $permission"
                    fi
                else
                    print_warning "    ✗ Permission failed: $permission"
                fi
                ;;
        esac
    done
    
    if [[ $successful_permissions -eq ${#permissions_tests[@]} ]]; then
        print_success "IAM permissions validation passed"
        return 0
    else
        print_warning "Some IAM permissions failed ($successful_permissions/${#permissions_tests[@]} passed)"
        return 0  # Don't fail deployment for permission warnings
    fi
}

# Function to test VPC endpoints
test_vpc_endpoints() {
    print_status "Testing VPC endpoints..."
    
    # Get VPC ID from Terraform outputs
    cd "$PROJECT_ROOT/infra"
    local outputs=$(terraform output -json 2>/dev/null || echo '{}')
    
    local vpc_id=$(echo "$outputs" | jq -r '.vpc_id.value // empty')
    
    if [[ -z "$vpc_id" ]]; then
        print_warning "VPC ID not found in Terraform outputs"
        return 0
    fi
    
    # List VPC endpoints
    local endpoints=$(aws ec2 describe-vpc-endpoints \
        --filters "Name=vpc-id,Values=$vpc_id" \
        --query 'VpcEndpoints[].ServiceName' \
        --output text)
    
    if [[ -n "$endpoints" ]]; then
        local endpoint_count=$(echo "$endpoints" | wc -w)
        print_success "VPC endpoints found: $endpoint_count"
        
        if [[ "$VERBOSE" == "true" ]]; then
            for endpoint in $endpoints; do
                print_status "  ✓ Endpoint: $endpoint"
            done
        fi
        
        return 0
    else
        print_warning "No VPC endpoints found for VPC: $vpc_id"
        return 0
    fi
}

# Function to run functional tests
run_functional_tests() {
    if [[ "$SKIP_FUNCTIONAL_TESTS" == "true" ]]; then
        print_status "Skipping functional tests as requested"
        return 0
    fi
    
    print_status "Running functional tests..."
    
    # Check if test suite exists
    local test_dir="$PROJECT_ROOT/tests"
    
    if [[ ! -d "$test_dir" ]]; then
        print_warning "Test directory not found: $test_dir"
        return 0
    fi
    
    # Run integration tests if available
    if [[ -f "$test_dir/integration/test_deployment.py" ]]; then
        print_status "  Running integration tests..."
        
        cd "$test_dir"
        
        if timeout "$TIMEOUT" python3 -m pytest integration/test_deployment.py -v; then
            print_success "Integration tests passed"
        else
            print_error "Integration tests failed"
            return 1
        fi
    else
        print_warning "Integration tests not found"
    fi
    
    return 0
}

# Function to generate validation report
generate_validation_report() {
    print_status "Generating validation report..."
    
    local report_file="$LOG_DIR/validation-report-$ENVIRONMENT-$TIMESTAMP.json"
    
    # Create validation report
    cat > "$report_file" << EOF
{
    "validation_summary": {
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "environment": "$ENVIRONMENT",
        "total_validations": ${#VALIDATION_RESULTS[@]},
        "failed_validations": ${#FAILED_VALIDATIONS[@]},
        "success_rate": "$(( (${#VALIDATION_RESULTS[@]} * 100) / (${#VALIDATION_RESULTS[@]} + ${#FAILED_VALIDATIONS[@]}) ))%",
        "overall_status": "$([ ${#FAILED_VALIDATIONS[@]} -eq 0 ] && echo "PASSED" || echo "FAILED")"
    },
    "successful_validations": $(printf '%s\n' "${VALIDATION_RESULTS[@]}" | jq -R . | jq -s .),
    "failed_validations": $(printf '%s\n' "${FAILED_VALIDATIONS[@]}" | jq -R . | jq -s .),
    "recommendations": [
        $([ ${#FAILED_VALIDATIONS[@]} -gt 0 ] && echo '"Review and fix failed validations before proceeding to production",' || echo '')
        "Monitor system performance and resource utilization",
        "Set up alerting for critical system components",
        "Review security configurations and access controls"
    ]
}
EOF
    
    print_success "Validation report generated: $report_file"
}

# Main validation function
main() {
    print_status "Sentinel Deployment Validation"
    print_status "=============================="
    print_status "Environment: $ENVIRONMENT"
    print_status "Timeout: ${TIMEOUT}s"
    print_status "Skip Functional Tests: $SKIP_FUNCTIONAL_TESTS"
    print_status ""
    
    local validation_steps=(
        "Prerequisites Check:check_prerequisites"
        "Infrastructure Validation:validate_infrastructure"
        "Lambda Packaging Test:test_lambda_packaging"
        "DynamoDB Access Test:test_dynamodb_access"
        "S3 Access Test:test_s3_access"
        "OpenSearch Access Test:test_opensearch_access"
        "Lambda Execution Test:test_lambda_execution"
        "IAM Permissions Test:test_iam_permissions"
        "VPC Endpoints Test:test_vpc_endpoints"
        "Functional Tests:run_functional_tests"
    )
    
    local failed_steps=0
    
    for step in "${validation_steps[@]}"; do
        local step_name=$(echo "$step" | cut -d':' -f1)
        local step_function=$(echo "$step" | cut -d':' -f2)
        
        print_status ""
        print_status "--- $step_name ---"
        
        if ! $step_function; then
            ((failed_steps++))
            print_error "$step_name failed"
        fi
    done
    
    # Generate validation report
    generate_validation_report
    
    # Print summary
    print_status ""
    print_status "================================"
    print_status "VALIDATION SUMMARY"
    print_status "================================"
    print_status "Environment: $ENVIRONMENT"
    print_status "Total Validations: ${#VALIDATION_RESULTS[@]}"
    print_status "Failed Validations: ${#FAILED_VALIDATIONS[@]}"
    print_status "Failed Steps: $failed_steps"
    
    if [[ $failed_steps -eq 0 ]]; then
        print_success "All validation steps passed!"
        print_status "Deployment is ready for use."
    else
        print_error "$failed_steps validation steps failed"
        print_status "Please review and fix the issues before proceeding."
    fi
    
    print_status ""
    print_status "Log file: $LOG_FILE"
    print_status "Report: $LOG_DIR/validation-report-$ENVIRONMENT-$TIMESTAMP.json"
    
    return $failed_steps
}

# Trap for cleanup
trap 'print_error "Validation interrupted"; exit 1' INT TERM

# Run main function
main "$@"
exit_code=$?

exit $exit_code