#!/bin/bash

# Sentinel Agent CI/CD Pipeline Integration Script
# This script provides CI/CD pipeline integration for automated agent deployments
# with comprehensive testing, validation, and rollback capabilities

set -e

# Configuration
PIPELINE_STAGE=${1:-build}
ENVIRONMENT=${2:-dev}
COMMIT_SHA=${3:-$(git rev-parse HEAD 2>/dev/null || echo "unknown")}
BUILD_NUMBER=${4:-$(date +%Y%m%d%H%M%S)}

# CI/CD specific configuration
CI_MODE=${CI_MODE:-false}
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-}
TEAMS_WEBHOOK_URL=${TEAMS_WEBHOOK_URL:-}
EMAIL_NOTIFICATIONS=${EMAIL_NOTIFICATIONS:-false}

# AWS and Strands configuration
AWS_REGION=${AWS_REGION:-us-east-1}
STRANDS_CLI=${STRANDS_CLI:-strands}

# Colors for output (disabled in CI mode)
if [ "$CI_MODE" = "true" ]; then
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
else
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
fi

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"
}

# Show usage information
show_usage() {
    cat << EOF
Usage: $0 <pipeline_stage> <environment> [commit_sha] [build_number]

Pipeline Stages:
  build       - Build and validate agent configurations
  test        - Run comprehensive tests
  deploy      - Deploy agents to target environment
  promote     - Promote agents from one environment to another
  rollback    - Rollback to previous version
  cleanup     - Clean up temporary resources

Environments:
  dev, staging, prod

Environment Variables:
  CI_MODE=true                    - Enable CI/CD mode (no colors, structured output)
  SLACK_WEBHOOK_URL=<url>         - Slack webhook for notifications
  TEAMS_WEBHOOK_URL=<url>         - Microsoft Teams webhook for notifications
  EMAIL_NOTIFICATIONS=true        - Enable email notifications
  PARALLEL_DEPLOYMENT=true        - Deploy agents in parallel
  SKIP_TESTS=false               - Skip test execution (not recommended)
  DEPLOYMENT_TIMEOUT=900          - Deployment timeout in seconds

Examples:
  $0 build dev
  $0 deploy staging abc123 20241201120000
  $0 promote prod
  $0 rollback prod

EOF
}

# Send notification
send_notification() {
    local message=$1
    local status=${2:-info}
    local title=${3:-"Sentinel Agent Pipeline"}
    
    # Slack notification
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        send_slack_notification "$title" "$message" "$status"
    fi
    
    # Teams notification
    if [ -n "$TEAMS_WEBHOOK_URL" ]; then
        send_teams_notification "$title" "$message" "$status"
    fi
    
    # Email notification
    if [ "$EMAIL_NOTIFICATIONS" = "true" ]; then
        send_email_notification "$title" "$message" "$status"
    fi
}

# Send Slack notification
send_slack_notification() {
    local title=$1
    local message=$2
    local status=$3
    
    local color="good"
    case $status in
        "error"|"failure")
            color="danger"
            ;;
        "warning")
            color="warning"
            ;;
    esac
    
    local payload=$(cat << EOF
{
    "attachments": [
        {
            "color": "$color",
            "title": "$title",
            "text": "$message",
            "fields": [
                {
                    "title": "Environment",
                    "value": "$ENVIRONMENT",
                    "short": true
                },
                {
                    "title": "Stage",
                    "value": "$PIPELINE_STAGE",
                    "short": true
                },
                {
                    "title": "Commit",
                    "value": "$COMMIT_SHA",
                    "short": true
                },
                {
                    "title": "Build",
                    "value": "$BUILD_NUMBER",
                    "short": true
                }
            ],
            "ts": $(date +%s)
        }
    ]
}
EOF
    )
    
    curl -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$SLACK_WEBHOOK_URL" &>/dev/null || log_warn "Failed to send Slack notification"
}

# Send Teams notification
send_teams_notification() {
    local title=$1
    local message=$2
    local status=$3
    
    local color="00FF00"
    case $status in
        "error"|"failure")
            color="FF0000"
            ;;
        "warning")
            color="FFA500"
            ;;
    esac
    
    local payload=$(cat << EOF
{
    "@type": "MessageCard",
    "@context": "http://schema.org/extensions",
    "themeColor": "$color",
    "summary": "$title",
    "sections": [{
        "activityTitle": "$title",
        "activitySubtitle": "$message",
        "facts": [{
            "name": "Environment",
            "value": "$ENVIRONMENT"
        }, {
            "name": "Stage",
            "value": "$PIPELINE_STAGE"
        }, {
            "name": "Commit",
            "value": "$COMMIT_SHA"
        }, {
            "name": "Build",
            "value": "$BUILD_NUMBER"
        }]
    }]
}
EOF
    )
    
    curl -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$TEAMS_WEBHOOK_URL" &>/dev/null || log_warn "Failed to send Teams notification"
}

# Send email notification
send_email_notification() {
    local title=$1
    local message=$2
    local status=$3
    
    # Use AWS SES to send email notification
    local subject="[$status] $title - $ENVIRONMENT"
    local body="$message\n\nEnvironment: $ENVIRONMENT\nStage: $PIPELINE_STAGE\nCommit: $COMMIT_SHA\nBuild: $BUILD_NUMBER"
    
    aws ses send-email \
        --source "sentinel-ci@$(aws sts get-caller-identity --query Account --output text).amazonaws.com" \
        --destination "ToAddresses=devops@company.com" \
        --message "Subject={Data='$subject'},Body={Text={Data='$body'}}" \
        --region $AWS_REGION &>/dev/null || log_warn "Failed to send email notification"
}

# Build stage
build_stage() {
    log_info "Starting build stage for commit $COMMIT_SHA"
    
    # Validate agent configurations
    log_info "Validating agent configurations..."
    
    for config in ingestor-agent.yaml analyst-assistant-agent.yaml; do
        if [ ! -f "$config" ]; then
            log_error "Configuration file not found: $config"
            exit 1
        fi
        
        # YAML syntax validation
        if command -v yamllint &> /dev/null; then
            yamllint "$config" || {
                log_error "YAML validation failed for $config"
                exit 1
            }
        fi
        
        # Strands configuration validation
        $STRANDS_CLI validate --config "$config" || {
            log_error "Strands validation failed for $config"
            exit 1
        }
        
        log_info "✓ $config validated successfully"
    done
    
    # Create build artifacts
    log_info "Creating build artifacts..."
    
    mkdir -p "artifacts/$BUILD_NUMBER"
    
    # Copy configurations with build metadata
    for config in ingestor-agent.yaml analyst-assistant-agent.yaml; do
        # Add build metadata to configuration
        cp "$config" "artifacts/$BUILD_NUMBER/$config"
        
        # Add build information as comments
        cat >> "artifacts/$BUILD_NUMBER/$config" << EOF

# Build Information
# Build Number: $BUILD_NUMBER
# Commit SHA: $COMMIT_SHA
# Build Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)
# Environment: $ENVIRONMENT
EOF
    done
    
    # Create build manifest
    cat > "artifacts/$BUILD_NUMBER/build-manifest.json" << EOF
{
    "build_number": "$BUILD_NUMBER",
    "commit_sha": "$COMMIT_SHA",
    "build_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "environment": "$ENVIRONMENT",
    "pipeline_stage": "$PIPELINE_STAGE",
    "artifacts": [
        "ingestor-agent.yaml",
        "analyst-assistant-agent.yaml"
    ]
}
EOF
    
    log_info "Build stage completed successfully"
    send_notification "Build stage completed for commit $COMMIT_SHA" "success"
}

# Test stage
test_stage() {
    log_info "Starting test stage for build $BUILD_NUMBER"
    
    if [ "$SKIP_TESTS" = "true" ]; then
        log_warn "Skipping tests (SKIP_TESTS=true)"
        return 0
    fi
    
    # Unit tests for configurations
    log_info "Running configuration tests..."
    
    # Test environment variable substitution
    for config in "artifacts/$BUILD_NUMBER/ingestor-agent.yaml" "artifacts/$BUILD_NUMBER/analyst-assistant-agent.yaml"; do
        # Create test environment file
        cat > test.env << EOF
AWS_ACCOUNT_ID=123456789012
DYNAMODB_ARTICLES_TABLE=test-articles
DYNAMODB_MEMORY_TABLE=test-memory
S3_CONTENT_BUCKET=test-content
S3_ARTIFACTS_BUCKET=test-artifacts
OPENSEARCH_ENDPOINT=https://test.us-east-1.es.amazonaws.com
KMS_KEY_ID=arn:aws:kms:us-east-1:123456789012:key/test
PRIVATE_SUBNET_1_ID=subnet-test1
PRIVATE_SUBNET_2_ID=subnet-test2
LAMBDA_SECURITY_GROUP_ID=sg-test
EOF
        
        # Test environment variable substitution
        if envsubst < "$config" > "${config%.yaml}-test.yaml"; then
            log_info "✓ Environment substitution test passed for $(basename $config)"
        else
            log_error "Environment substitution test failed for $(basename $config)"
            exit 1
        fi
        
        # Cleanup test files
        rm -f "${config%.yaml}-test.yaml" test.env
    done
    
    # Integration tests (if agents are already deployed)
    if [ "$ENVIRONMENT" != "prod" ]; then
        log_info "Running integration tests..."
        
        # Test agent availability
        for agent in sentinel-ingestor-agent sentinel-analyst-assistant; do
            if $STRANDS_CLI status --agent $agent --environment $ENVIRONMENT &>/dev/null; then
                log_info "Running tests for $agent..."
                
                if $STRANDS_CLI test \
                    --agent $agent \
                    --environment $ENVIRONMENT \
                    --test-suite basic \
                    --timeout 180; then
                    log_info "✓ Tests passed for $agent"
                else
                    log_error "Tests failed for $agent"
                    exit 1
                fi
            else
                log_warn "Agent $agent not deployed, skipping integration tests"
            fi
        done
    fi
    
    log_info "Test stage completed successfully"
    send_notification "Test stage completed for build $BUILD_NUMBER" "success"
}

# Deploy stage
deploy_stage() {
    log_info "Starting deploy stage for build $BUILD_NUMBER to environment $ENVIRONMENT"
    
    # Check if artifacts exist
    if [ ! -d "artifacts/$BUILD_NUMBER" ]; then
        log_error "Build artifacts not found for build $BUILD_NUMBER"
        exit 1
    fi
    
    # Deploy agents
    local agents=("ingestor-agent" "analyst-assistant-agent")
    local pids=()
    
    if [ "$PARALLEL_DEPLOYMENT" = "true" ]; then
        log_info "Deploying agents in parallel..."
        
        for agent in "${agents[@]}"; do
            deploy_single_agent "$agent" &
            pids+=($!)
        done
        
        # Wait for all deployments to complete
        for pid in "${pids[@]}"; do
            if ! wait $pid; then
                log_error "Parallel deployment failed"
                exit 1
            fi
        done
    else
        log_info "Deploying agents sequentially..."
        
        for agent in "${agents[@]}"; do
            deploy_single_agent "$agent"
        done
    fi
    
    # Post-deployment validation
    log_info "Running post-deployment validation..."
    
    for agent in sentinel-ingestor-agent sentinel-analyst-assistant; do
        if ! perform_health_check "$agent"; then
            log_error "Post-deployment health check failed for $agent"
            exit 1
        fi
    done
    
    log_info "Deploy stage completed successfully"
    send_notification "Deploy stage completed for build $BUILD_NUMBER to $ENVIRONMENT" "success"
}

# Deploy single agent
deploy_single_agent() {
    local agent_type=$1
    local config_file="artifacts/$BUILD_NUMBER/${agent_type}.yaml"
    local agent_name="sentinel-${agent_type%-agent}"
    
    log_info "Deploying $agent_name..."
    
    # Substitute environment variables
    envsubst < "$config_file" > "${config_file%.yaml}-${ENVIRONMENT}.yaml"
    
    # Deploy with timeout
    timeout ${DEPLOYMENT_TIMEOUT:-900} $STRANDS_CLI deploy \
        --config "${config_file%.yaml}-${ENVIRONMENT}.yaml" \
        --target bedrock-agentcore \
        --environment $ENVIRONMENT \
        --region $AWS_REGION \
        --wait-for-completion \
        --verbose
    
    local exit_code=$?
    
    # Cleanup temporary file
    rm -f "${config_file%.yaml}-${ENVIRONMENT}.yaml"
    
    if [ $exit_code -eq 0 ]; then
        log_info "✓ $agent_name deployed successfully"
    elif [ $exit_code -eq 124 ]; then
        log_error "Deployment timeout for $agent_name"
        exit 1
    else
        log_error "Deployment failed for $agent_name (exit code: $exit_code)"
        exit 1
    fi
}

# Perform health check
perform_health_check() {
    local agent=$1
    local max_retries=5
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        case $agent in
            "sentinel-ingestor-agent")
                if $STRANDS_CLI invoke \
                    --agent $agent \
                    --environment $ENVIRONMENT \
                    --input '{"task": "health_check", "test_mode": true}' \
                    --timeout 30 &>/dev/null; then
                    return 0
                fi
                ;;
            "sentinel-analyst-assistant")
                if $STRANDS_CLI invoke \
                    --agent $agent \
                    --environment $ENVIRONMENT \
                    --input "Health check query" \
                    --timeout 15 &>/dev/null; then
                    return 0
                fi
                ;;
        esac
        
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $max_retries ]; then
            log_debug "Health check retry $retry_count/$max_retries for $agent"
            sleep 10
        fi
    done
    
    return 1
}

# Promote stage
promote_stage() {
    log_info "Starting promote stage from staging to prod"
    
    # This would typically involve promoting the same build artifacts
    # from staging to production environment
    
    if [ "$ENVIRONMENT" != "prod" ]; then
        log_error "Promote stage should target prod environment"
        exit 1
    fi
    
    # Get the latest successful build from staging
    local staging_build=$(get_latest_successful_build "staging")
    
    if [ -z "$staging_build" ]; then
        log_error "No successful staging build found to promote"
        exit 1
    fi
    
    log_info "Promoting build $staging_build from staging to prod"
    
    # Deploy the staging build to prod
    BUILD_NUMBER=$staging_build deploy_stage
    
    log_info "Promote stage completed successfully"
    send_notification "Build $staging_build promoted to production" "success"
}

# Get latest successful build
get_latest_successful_build() {
    local env=$1
    
    # This would typically query your CI/CD system or artifact repository
    # For now, return the latest build directory
    ls -1 artifacts/ | grep -E '^[0-9]+$' | sort -nr | head -n1
}

# Rollback stage
rollback_stage() {
    log_info "Starting rollback stage for environment $ENVIRONMENT"
    
    # Use the management script for rollback
    if ./manage-agents.sh "$ENVIRONMENT" rollback all; then
        log_info "Rollback stage completed successfully"
        send_notification "Rollback completed for $ENVIRONMENT" "warning"
    else
        log_error "Rollback stage failed"
        send_notification "Rollback failed for $ENVIRONMENT" "error"
        exit 1
    fi
}

# Cleanup stage
cleanup_stage() {
    log_info "Starting cleanup stage"
    
    # Clean up old build artifacts (keep last 10 builds)
    if [ -d "artifacts" ]; then
        local builds_to_keep=10
        local build_count=$(ls -1 artifacts/ | grep -E '^[0-9]+$' | wc -l)
        
        if [ $build_count -gt $builds_to_keep ]; then
            local builds_to_delete=$((build_count - builds_to_keep))
            log_info "Cleaning up $builds_to_delete old build artifacts..."
            
            ls -1 artifacts/ | grep -E '^[0-9]+$' | sort -n | head -n$builds_to_delete | while read build; do
                rm -rf "artifacts/$build"
                log_debug "Deleted build artifacts: $build"
            done
        fi
    fi
    
    # Clean up temporary files
    find . -name "*-${ENVIRONMENT}.yaml" -type f -delete
    find . -name "*.tmp" -type f -delete
    
    log_info "Cleanup stage completed successfully"
}

# Main function
main() {
    # Check if help is requested
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        show_usage
        exit 0
    fi
    
    # Validate parameters
    if [ -z "$PIPELINE_STAGE" ]; then
        log_error "Pipeline stage is required"
        show_usage
        exit 1
    fi
    
    # Change to agents directory
    cd "$(dirname "$0")"
    
    # Set CI mode output format
    if [ "$CI_MODE" = "true" ]; then
        log_info "Running in CI/CD mode"
        set -x  # Enable command tracing for CI logs
    fi
    
    # Execute pipeline stage
    case $PIPELINE_STAGE in
        "build")
            build_stage
            ;;
        "test")
            test_stage
            ;;
        "deploy")
            deploy_stage
            ;;
        "promote")
            promote_stage
            ;;
        "rollback")
            rollback_stage
            ;;
        "cleanup")
            cleanup_stage
            ;;
        *)
            log_error "Unknown pipeline stage: $PIPELINE_STAGE"
            show_usage
            exit 1
            ;;
    esac
}

# Error handling
trap 'log_error "Pipeline failed at stage: $PIPELINE_STAGE"; send_notification "Pipeline failed at stage: $PIPELINE_STAGE" "error"; exit 1' ERR

# Run main function
main "$@"