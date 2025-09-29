#!/bin/bash

# Sentinel Strands Agent Deployment Script
# This script deploys both Ingestor and Analyst Assistant agents to Bedrock AgentCore
# with comprehensive health checking, rollback capabilities, and monitoring

set -e

# Configuration
ENVIRONMENT=${1:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
STRANDS_CLI=${STRANDS_CLI:-strands}
DEPLOYMENT_TIMEOUT=${DEPLOYMENT_TIMEOUT:-600}  # 10 minutes
HEALTH_CHECK_RETRIES=${HEALTH_CHECK_RETRIES:-5}
ROLLBACK_ON_FAILURE=${ROLLBACK_ON_FAILURE:-true}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Strands CLI is installed
    if ! command -v $STRANDS_CLI &> /dev/null; then
        log_error "Strands CLI not found. Please install Strands CLI first."
        log_info "Install Strands CLI: https://docs.strands.ai/installation"
        exit 1
    fi
    
    # Check Strands CLI version
    STRANDS_VERSION=$($STRANDS_CLI --version 2>/dev/null || echo "unknown")
    log_info "Strands CLI version: $STRANDS_VERSION"
    
    # Check if AWS CLI is configured
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS CLI not configured or no valid credentials found."
        exit 1
    fi
    
    # Check if required environment variables are set
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        log_info "AWS Account ID: $AWS_ACCOUNT_ID"
    fi
    
    # Check Bedrock service availability
    if ! aws bedrock list-foundation-models --region $AWS_REGION &> /dev/null; then
        log_error "Bedrock service not available in region $AWS_REGION"
        exit 1
    fi
    
    # Check required IAM permissions
    check_iam_permissions
    
    log_info "Prerequisites check completed successfully."
}

# Check IAM permissions
check_iam_permissions() {
    log_info "Checking IAM permissions..."
    
    # Check Bedrock permissions
    if ! aws bedrock list-agents --region $AWS_REGION &> /dev/null; then
        log_warn "Limited Bedrock permissions detected. Some operations may fail."
    fi
    
    # Check Lambda permissions
    if ! aws lambda list-functions --region $AWS_REGION &> /dev/null; then
        log_error "Lambda permissions required for agent tool integration"
        exit 1
    fi
    
    log_info "IAM permissions check completed."
}

# Validate agent configurations
validate_configs() {
    log_info "Validating agent configurations..."
    
    # Validate Ingestor Agent config
    if [ ! -f "ingestor-agent.yaml" ]; then
        log_error "Ingestor agent configuration not found: ingestor-agent.yaml"
        exit 1
    fi
    
    # Validate Analyst Assistant config
    if [ ! -f "analyst-assistant-agent.yaml" ]; then
        log_error "Analyst Assistant agent configuration not found: analyst-assistant-agent.yaml"
        exit 1
    fi
    
    # Basic YAML syntax validation
    if command -v yamllint &> /dev/null; then
        yamllint ingestor-agent.yaml || log_warn "YAML lint warnings for ingestor-agent.yaml"
        yamllint analyst-assistant-agent.yaml || log_warn "YAML lint warnings for analyst-assistant-agent.yaml"
    fi
    
    log_info "Configuration validation completed."
}

# Deploy Ingestor Agent
deploy_ingestor_agent() {
    log_info "Deploying Ingestor Agent to Bedrock AgentCore..."
    
    # Backup existing agent if it exists
    backup_existing_agent "sentinel-ingestor-agent"
    
    # Substitute environment variables in the config
    envsubst < ingestor-agent.yaml > ingestor-agent-${ENVIRONMENT}.yaml
    
    # Validate configuration before deployment
    validate_agent_config "ingestor-agent-${ENVIRONMENT}.yaml"
    
    # Deploy using Strands CLI with timeout
    log_info "Starting deployment with timeout of ${DEPLOYMENT_TIMEOUT} seconds..."
    
    timeout $DEPLOYMENT_TIMEOUT $STRANDS_CLI deploy \
        --config ingestor-agent-${ENVIRONMENT}.yaml \
        --target bedrock-agentcore \
        --environment $ENVIRONMENT \
        --region $AWS_REGION \
        --wait-for-completion \
        --verbose
    
    DEPLOY_EXIT_CODE=$?
    
    if [ $DEPLOY_EXIT_CODE -eq 0 ]; then
        log_info "Ingestor Agent deployed successfully."
        
        # Perform health check
        if ! health_check_agent "sentinel-ingestor-agent"; then
            log_error "Ingestor Agent health check failed."
            if [ "$ROLLBACK_ON_FAILURE" = "true" ]; then
                rollback_agent "sentinel-ingestor-agent"
            fi
            exit 1
        fi
        
        # Store deployment metadata
        store_deployment_metadata "sentinel-ingestor-agent" "ingestor-agent-${ENVIRONMENT}.yaml"
        
    elif [ $DEPLOY_EXIT_CODE -eq 124 ]; then
        log_error "Ingestor Agent deployment timed out after ${DEPLOYMENT_TIMEOUT} seconds."
        exit 1
    else
        log_error "Failed to deploy Ingestor Agent (exit code: $DEPLOY_EXIT_CODE)."
        exit 1
    fi
}

# Deploy Analyst Assistant Agent
deploy_analyst_assistant() {
    log_info "Deploying Analyst Assistant Agent to Bedrock AgentCore..."
    
    # Backup existing agent if it exists
    backup_existing_agent "sentinel-analyst-assistant"
    
    # Substitute environment variables in the config
    envsubst < analyst-assistant-agent.yaml > analyst-assistant-agent-${ENVIRONMENT}.yaml
    
    # Validate configuration before deployment
    validate_agent_config "analyst-assistant-agent-${ENVIRONMENT}.yaml"
    
    # Deploy using Strands CLI with timeout
    log_info "Starting deployment with timeout of ${DEPLOYMENT_TIMEOUT} seconds..."
    
    timeout $DEPLOYMENT_TIMEOUT $STRANDS_CLI deploy \
        --config analyst-assistant-agent-${ENVIRONMENT}.yaml \
        --target bedrock-agentcore \
        --environment $ENVIRONMENT \
        --region $AWS_REGION \
        --wait-for-completion \
        --verbose
    
    DEPLOY_EXIT_CODE=$?
    
    if [ $DEPLOY_EXIT_CODE -eq 0 ]; then
        log_info "Analyst Assistant Agent deployed successfully."
        
        # Perform health check
        if ! health_check_agent "sentinel-analyst-assistant"; then
            log_error "Analyst Assistant Agent health check failed."
            if [ "$ROLLBACK_ON_FAILURE" = "true" ]; then
                rollback_agent "sentinel-analyst-assistant"
            fi
            exit 1
        fi
        
        # Store deployment metadata
        store_deployment_metadata "sentinel-analyst-assistant" "analyst-assistant-agent-${ENVIRONMENT}.yaml"
        
    elif [ $DEPLOY_EXIT_CODE -eq 124 ]; then
        log_error "Analyst Assistant Agent deployment timed out after ${DEPLOYMENT_TIMEOUT} seconds."
        exit 1
    else
        log_error "Failed to deploy Analyst Assistant Agent (exit code: $DEPLOY_EXIT_CODE)."
        exit 1
    fi
}

# Validate agent configuration
validate_agent_config() {
    local config_file=$1
    log_info "Validating agent configuration: $config_file"
    
    # Check if file exists
    if [ ! -f "$config_file" ]; then
        log_error "Configuration file not found: $config_file"
        exit 1
    fi
    
    # Validate YAML syntax
    if command -v yamllint &> /dev/null; then
        yamllint "$config_file" || {
            log_error "YAML validation failed for $config_file"
            exit 1
        }
    fi
    
    # Validate Strands configuration
    $STRANDS_CLI validate --config "$config_file" || {
        log_error "Strands configuration validation failed for $config_file"
        exit 1
    }
    
    log_info "Configuration validation completed for $config_file"
}

# Backup existing agent
backup_existing_agent() {
    local agent_name=$1
    log_info "Backing up existing agent: $agent_name"
    
    # Create backup directory
    mkdir -p "backups/${ENVIRONMENT}"
    
    # Export existing agent configuration if it exists
    if $STRANDS_CLI list --agent $agent_name --environment $ENVIRONMENT &> /dev/null; then
        $STRANDS_CLI export \
            --agent $agent_name \
            --environment $ENVIRONMENT \
            --output "backups/${ENVIRONMENT}/${agent_name}-$(date +%Y%m%d-%H%M%S).yaml"
        
        log_info "Agent backup created for $agent_name"
    else
        log_info "No existing agent found to backup: $agent_name"
    fi
}

# Health check for deployed agent
health_check_agent() {
    local agent_name=$1
    log_info "Performing health check for agent: $agent_name"
    
    local retry_count=0
    while [ $retry_count -lt $HEALTH_CHECK_RETRIES ]; do
        log_info "Health check attempt $((retry_count + 1))/$HEALTH_CHECK_RETRIES"
        
        # Check agent status
        if $STRANDS_CLI status --agent $agent_name --environment $ENVIRONMENT | grep -q "healthy"; then
            log_info "Agent $agent_name is healthy"
            
            # Perform functional test
            if perform_functional_test "$agent_name"; then
                log_info "Functional test passed for $agent_name"
                return 0
            else
                log_warn "Functional test failed for $agent_name, retrying..."
            fi
        else
            log_warn "Agent $agent_name is not healthy, retrying..."
        fi
        
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $HEALTH_CHECK_RETRIES ]; then
            sleep 30
        fi
    done
    
    log_error "Health check failed for $agent_name after $HEALTH_CHECK_RETRIES attempts"
    return 1
}

# Perform functional test
perform_functional_test() {
    local agent_name=$1
    log_info "Performing functional test for $agent_name"
    
    case $agent_name in
        "sentinel-ingestor-agent")
            # Test ingestor agent with a simple feed parsing request
            $STRANDS_CLI invoke \
                --agent $agent_name \
                --environment $ENVIRONMENT \
                --input '{"task": "health_check", "test_mode": true}' \
                --timeout 60
            ;;
        "sentinel-analyst-assistant")
            # Test analyst assistant with a simple query
            $STRANDS_CLI invoke \
                --agent $agent_name \
                --environment $ENVIRONMENT \
                --input "Health check query" \
                --timeout 30
            ;;
        *)
            log_warn "No functional test defined for $agent_name"
            return 0
            ;;
    esac
    
    return $?
}

# Rollback agent deployment
rollback_agent() {
    local agent_name=$1
    log_warn "Rolling back agent deployment: $agent_name"
    
    # Find the most recent backup
    local backup_file=$(ls -t "backups/${ENVIRONMENT}/${agent_name}-"*.yaml 2>/dev/null | head -n1)
    
    if [ -n "$backup_file" ] && [ -f "$backup_file" ]; then
        log_info "Rolling back to backup: $backup_file"
        
        $STRANDS_CLI deploy \
            --config "$backup_file" \
            --target bedrock-agentcore \
            --environment $ENVIRONMENT \
            --region $AWS_REGION \
            --wait-for-completion
        
        if [ $? -eq 0 ]; then
            log_info "Rollback completed successfully for $agent_name"
        else
            log_error "Rollback failed for $agent_name"
        fi
    else
        log_warn "No backup found for $agent_name, cannot rollback"
        
        # Attempt to delete the failed deployment
        log_info "Attempting to delete failed deployment..."
        $STRANDS_CLI delete \
            --agent $agent_name \
            --environment $ENVIRONMENT \
            --force
    fi
}

# Store deployment metadata
store_deployment_metadata() {
    local agent_name=$1
    local config_file=$2
    
    log_info "Storing deployment metadata for $agent_name"
    
    # Create metadata directory
    mkdir -p "deployments/${ENVIRONMENT}"
    
    # Create deployment record
    cat > "deployments/${ENVIRONMENT}/${agent_name}-deployment.json" << EOF
{
    "agent_name": "$agent_name",
    "environment": "$ENVIRONMENT",
    "deployment_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "config_file": "$config_file",
    "deployed_by": "$(whoami)",
    "aws_account": "$AWS_ACCOUNT_ID",
    "aws_region": "$AWS_REGION",
    "strands_version": "$STRANDS_VERSION",
    "deployment_id": "$(uuidgen)"
}
EOF
    
    log_info "Deployment metadata stored for $agent_name"
}

# Monitor agent performance
monitor_agent_performance() {
    local agent_name=$1
    log_info "Setting up performance monitoring for $agent_name"
    
    # Create CloudWatch dashboard for agent metrics
    aws cloudwatch put-dashboard \
        --dashboard-name "Sentinel-${agent_name}-${ENVIRONMENT}" \
        --dashboard-body file://monitoring/dashboard-template.json \
        --region $AWS_REGION
    
    # Set up CloudWatch alarms
    setup_cloudwatch_alarms "$agent_name"
    
    log_info "Performance monitoring configured for $agent_name"
}

# Setup CloudWatch alarms
setup_cloudwatch_alarms() {
    local agent_name=$1
    
    # High error rate alarm
    aws cloudwatch put-metric-alarm \
        --alarm-name "${agent_name}-high-error-rate-${ENVIRONMENT}" \
        --alarm-description "High error rate for $agent_name" \
        --metric-name "ErrorRate" \
        --namespace "Sentinel/Agents" \
        --statistic "Average" \
        --period 300 \
        --threshold 5.0 \
        --comparison-operator "GreaterThanThreshold" \
        --evaluation-periods 2 \
        --alarm-actions "arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:sentinel-alerts" \
        --dimensions Name=AgentName,Value=$agent_name Name=Environment,Value=$ENVIRONMENT \
        --region $AWS_REGION
    
    # Low processing rate alarm
    aws cloudwatch put-metric-alarm \
        --alarm-name "${agent_name}-low-processing-rate-${ENVIRONMENT}" \
        --alarm-description "Low processing rate for $agent_name" \
        --metric-name "ProcessingRate" \
        --namespace "Sentinel/Agents" \
        --statistic "Average" \
        --period 600 \
        --threshold 1.0 \
        --comparison-operator "LessThanThreshold" \
        --evaluation-periods 3 \
        --alarm-actions "arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:sentinel-alerts" \
        --dimensions Name=AgentName,Value=$agent_name Name=Environment,Value=$ENVIRONMENT \
        --region $AWS_REGION
    
    log_info "CloudWatch alarms configured for $agent_name"
}

# Test agent deployments
test_agents() {
    log_info "Testing agent deployments..."
    
    # Test Ingestor Agent
    log_info "Testing Ingestor Agent..."
    if ! $STRANDS_CLI test \
        --agent sentinel-ingestor-agent \
        --environment $ENVIRONMENT \
        --test-suite comprehensive \
        --timeout 300; then
        log_error "Ingestor Agent tests failed"
        return 1
    fi
    
    # Test Analyst Assistant Agent
    log_info "Testing Analyst Assistant Agent..."
    if ! $STRANDS_CLI test \
        --agent sentinel-analyst-assistant \
        --environment $ENVIRONMENT \
        --test-suite comprehensive \
        --timeout 180; then
        log_error "Analyst Assistant Agent tests failed"
        return 1
    fi
    
    log_info "All agent tests completed successfully."
    return 0
}

# Cleanup temporary files
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -f ingestor-agent-${ENVIRONMENT}.yaml
    rm -f analyst-assistant-agent-${ENVIRONMENT}.yaml
}

# Generate deployment report
generate_deployment_report() {
    log_info "Generating deployment report..."
    
    local report_file="deployments/${ENVIRONMENT}/deployment-report-$(date +%Y%m%d-%H%M%S).md"
    mkdir -p "deployments/${ENVIRONMENT}"
    
    cat > "$report_file" << EOF
# Sentinel Agent Deployment Report

**Environment:** $ENVIRONMENT  
**Date:** $(date -u +%Y-%m-%dT%H:%M:%SZ)  
**Deployed by:** $(whoami)  
**AWS Account:** $AWS_ACCOUNT_ID  
**AWS Region:** $AWS_REGION  

## Deployed Agents

### Ingestor Agent
- **Name:** sentinel-ingestor-agent
- **Status:** $(get_agent_status "sentinel-ingestor-agent")
- **Health Check:** $(get_agent_health "sentinel-ingestor-agent")

### Analyst Assistant Agent
- **Name:** sentinel-analyst-assistant
- **Status:** $(get_agent_status "sentinel-analyst-assistant")
- **Health Check:** $(get_agent_health "sentinel-analyst-assistant")

## Monitoring

- CloudWatch Dashboards: Created
- CloudWatch Alarms: Configured
- Performance Monitoring: Active

## Next Steps

1. Monitor agent performance in CloudWatch
2. Review agent logs for any issues
3. Test end-to-end workflows
4. Update documentation if needed

EOF
    
    log_info "Deployment report generated: $report_file"
}

# Get agent status
get_agent_status() {
    local agent_name=$1
    $STRANDS_CLI status --agent $agent_name --environment $ENVIRONMENT 2>/dev/null | grep -o "Status: [^,]*" | cut -d' ' -f2 || echo "Unknown"
}

# Get agent health
get_agent_health() {
    local agent_name=$1
    if health_check_agent "$agent_name" &>/dev/null; then
        echo "Healthy"
    else
        echo "Unhealthy"
    fi
}

# Main deployment function
main() {
    log_info "Starting Sentinel Strands Agent Deployment for environment: $ENVIRONMENT"
    log_info "Configuration: ORCHESTRATOR=agentcore, ENABLE_AGENTS=true"
    
    # Change to agents directory
    cd "$(dirname "$0")"
    
    # Create necessary directories
    mkdir -p backups deployments monitoring
    
    # Run deployment steps
    check_prerequisites
    validate_configs
    
    # Deploy agents
    deploy_ingestor_agent
    deploy_analyst_assistant
    
    # Set up monitoring
    monitor_agent_performance "sentinel-ingestor-agent"
    monitor_agent_performance "sentinel-analyst-assistant"
    
    # Run comprehensive tests
    if ! test_agents; then
        log_error "Agent testing failed. Check logs for details."
        if [ "$ROLLBACK_ON_FAILURE" = "true" ]; then
            log_warn "Rolling back deployments due to test failures..."
            rollback_agent "sentinel-ingestor-agent"
            rollback_agent "sentinel-analyst-assistant"
        fi
        exit 1
    fi
    
    # Generate deployment report
    generate_deployment_report
    
    # Cleanup temporary files
    cleanup
    
    log_info "Sentinel Strands Agent Deployment completed successfully!"
    log_info "Agents are now available in Bedrock AgentCore for environment: $ENVIRONMENT"
    log_info "Monitor performance at: https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#dashboards:name=Sentinel-agents-${ENVIRONMENT}"
}

# Handle script interruption
trap cleanup EXIT

# Run main function
main "$@"