#!/bin/bash

# Sentinel Agent Management Script
# This script provides comprehensive management capabilities for Sentinel agents
# including status checking, updates, rollbacks, and performance monitoring

set -e

# Configuration
ENVIRONMENT=${1:-dev}
OPERATION=${2:-status}
AGENT_NAME=${3:-all}
AWS_REGION=${AWS_REGION:-us-east-1}
STRANDS_CLI=${STRANDS_CLI:-strands}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Show usage information
show_usage() {
    cat << EOF
Usage: $0 <environment> <operation> [agent_name]

Environment:
  dev, staging, prod

Operations:
  status      - Show agent status and health
  update      - Update agent to latest version
  rollback    - Rollback to previous version
  restart     - Restart agent
  logs        - Show agent logs
  metrics     - Show performance metrics
  test        - Run agent tests
  delete      - Delete agent (use with caution)

Agent Names:
  all                        - All agents (default)
  sentinel-ingestor-agent    - Ingestor agent only
  sentinel-analyst-assistant - Analyst assistant only

Examples:
  $0 dev status
  $0 prod update sentinel-ingestor-agent
  $0 staging rollback all
  $0 dev logs sentinel-analyst-assistant

EOF
}

# Get agent list based on agent_name parameter
get_agent_list() {
    case $AGENT_NAME in
        "all")
            echo "sentinel-ingestor-agent sentinel-analyst-assistant"
            ;;
        "sentinel-ingestor-agent"|"sentinel-analyst-assistant")
            echo "$AGENT_NAME"
            ;;
        *)
            log_error "Unknown agent name: $AGENT_NAME"
            show_usage
            exit 1
            ;;
    esac
}

# Show agent status
show_status() {
    local agents=$(get_agent_list)
    
    log_info "Checking agent status for environment: $ENVIRONMENT"
    echo
    
    for agent in $agents; do
        log_info "Agent: $agent"
        echo "----------------------------------------"
        
        # Get basic status
        if $STRANDS_CLI status --agent $agent --environment $ENVIRONMENT &>/dev/null; then
            $STRANDS_CLI status --agent $agent --environment $ENVIRONMENT
            
            # Get health status
            echo
            log_info "Health Check:"
            if perform_health_check "$agent"; then
                echo -e "${GREEN}✓ Healthy${NC}"
            else
                echo -e "${RED}✗ Unhealthy${NC}"
            fi
            
            # Get recent metrics
            echo
            log_info "Recent Metrics (last 1 hour):"
            show_agent_metrics "$agent" "1h"
            
        else
            echo -e "${RED}✗ Agent not found or not deployed${NC}"
        fi
        
        echo
        echo "========================================"
        echo
    done
}

# Perform health check
perform_health_check() {
    local agent=$1
    
    case $agent in
        "sentinel-ingestor-agent")
            $STRANDS_CLI invoke \
                --agent $agent \
                --environment $ENVIRONMENT \
                --input '{"task": "health_check", "test_mode": true}' \
                --timeout 30 &>/dev/null
            ;;
        "sentinel-analyst-assistant")
            $STRANDS_CLI invoke \
                --agent $agent \
                --environment $ENVIRONMENT \
                --input "Health check query" \
                --timeout 15 &>/dev/null
            ;;
        *)
            return 0
            ;;
    esac
    
    return $?
}

# Show agent metrics
show_agent_metrics() {
    local agent=$1
    local time_range=${2:-1h}
    
    # Get CloudWatch metrics
    local end_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local start_time=$(date -u -d "$time_range ago" +%Y-%m-%dT%H:%M:%SZ)
    
    # Invocation count
    local invocations=$(aws cloudwatch get-metric-statistics \
        --namespace "Sentinel/Agents" \
        --metric-name "Invocations" \
        --dimensions Name=AgentName,Value=$agent Name=Environment,Value=$ENVIRONMENT \
        --start-time "$start_time" \
        --end-time "$end_time" \
        --period 3600 \
        --statistics Sum \
        --query 'Datapoints[0].Sum' \
        --output text 2>/dev/null || echo "0")
    
    # Error rate
    local errors=$(aws cloudwatch get-metric-statistics \
        --namespace "Sentinel/Agents" \
        --metric-name "Errors" \
        --dimensions Name=AgentName,Value=$agent Name=Environment,Value=$ENVIRONMENT \
        --start-time "$start_time" \
        --end-time "$end_time" \
        --period 3600 \
        --statistics Sum \
        --query 'Datapoints[0].Sum' \
        --output text 2>/dev/null || echo "0")
    
    # Average duration
    local avg_duration=$(aws cloudwatch get-metric-statistics \
        --namespace "Sentinel/Agents" \
        --metric-name "Duration" \
        --dimensions Name=AgentName,Value=$agent Name=Environment,Value=$ENVIRONMENT \
        --start-time "$start_time" \
        --end-time "$end_time" \
        --period 3600 \
        --statistics Average \
        --query 'Datapoints[0].Average' \
        --output text 2>/dev/null || echo "0")
    
    echo "  Invocations: $invocations"
    echo "  Errors: $errors"
    echo "  Avg Duration: ${avg_duration}ms"
    
    # Calculate error rate
    if [ "$invocations" != "0" ] && [ "$invocations" != "None" ]; then
        local error_rate=$(echo "scale=2; $errors * 100 / $invocations" | bc -l 2>/dev/null || echo "0")
        echo "  Error Rate: ${error_rate}%"
    else
        echo "  Error Rate: N/A"
    fi
}

# Update agents
update_agents() {
    local agents=$(get_agent_list)
    
    log_info "Updating agents for environment: $ENVIRONMENT"
    
    for agent in $agents; do
        log_info "Updating agent: $agent"
        
        # Backup current version
        backup_agent "$agent"
        
        # Get the appropriate config file
        local config_file
        case $agent in
            "sentinel-ingestor-agent")
                config_file="ingestor-agent.yaml"
                ;;
            "sentinel-analyst-assistant")
                config_file="analyst-assistant-agent.yaml"
                ;;
        esac
        
        # Substitute environment variables
        envsubst < "$config_file" > "${config_file%.yaml}-${ENVIRONMENT}.yaml"
        
        # Deploy update
        if $STRANDS_CLI deploy \
            --config "${config_file%.yaml}-${ENVIRONMENT}.yaml" \
            --target bedrock-agentcore \
            --environment $ENVIRONMENT \
            --region $AWS_REGION \
            --wait-for-completion; then
            
            log_info "Successfully updated $agent"
            
            # Perform health check
            if ! perform_health_check "$agent"; then
                log_error "Health check failed after update for $agent"
                log_warn "Consider rolling back if issues persist"
            fi
        else
            log_error "Failed to update $agent"
        fi
        
        # Cleanup temporary file
        rm -f "${config_file%.yaml}-${ENVIRONMENT}.yaml"
    done
}

# Backup agent
backup_agent() {
    local agent=$1
    
    log_info "Creating backup for $agent"
    
    mkdir -p "backups/${ENVIRONMENT}"
    
    if $STRANDS_CLI export \
        --agent $agent \
        --environment $ENVIRONMENT \
        --output "backups/${ENVIRONMENT}/${agent}-$(date +%Y%m%d-%H%M%S).yaml"; then
        log_info "Backup created for $agent"
    else
        log_warn "Failed to create backup for $agent"
    fi
}

# Rollback agents
rollback_agents() {
    local agents=$(get_agent_list)
    
    log_info "Rolling back agents for environment: $ENVIRONMENT"
    
    for agent in $agents; do
        log_info "Rolling back agent: $agent"
        
        # Find the most recent backup
        local backup_file=$(ls -t "backups/${ENVIRONMENT}/${agent}-"*.yaml 2>/dev/null | head -n1)
        
        if [ -n "$backup_file" ] && [ -f "$backup_file" ]; then
            log_info "Rolling back to: $backup_file"
            
            if $STRANDS_CLI deploy \
                --config "$backup_file" \
                --target bedrock-agentcore \
                --environment $ENVIRONMENT \
                --region $AWS_REGION \
                --wait-for-completion; then
                
                log_info "Successfully rolled back $agent"
                
                # Perform health check
                if perform_health_check "$agent"; then
                    log_info "Health check passed after rollback for $agent"
                else
                    log_warn "Health check failed after rollback for $agent"
                fi
            else
                log_error "Failed to rollback $agent"
            fi
        else
            log_error "No backup found for $agent"
        fi
    done
}

# Restart agents
restart_agents() {
    local agents=$(get_agent_list)
    
    log_info "Restarting agents for environment: $ENVIRONMENT"
    
    for agent in $agents; do
        log_info "Restarting agent: $agent"
        
        if $STRANDS_CLI restart \
            --agent $agent \
            --environment $ENVIRONMENT; then
            
            log_info "Successfully restarted $agent"
            
            # Wait a moment for restart to complete
            sleep 10
            
            # Perform health check
            if perform_health_check "$agent"; then
                log_info "Health check passed after restart for $agent"
            else
                log_warn "Health check failed after restart for $agent"
            fi
        else
            log_error "Failed to restart $agent"
        fi
    done
}

# Show agent logs
show_logs() {
    local agents=$(get_agent_list)
    
    for agent in $agents; do
        log_info "Showing logs for agent: $agent"
        echo "----------------------------------------"
        
        # Show Strands logs
        $STRANDS_CLI logs \
            --agent $agent \
            --environment $ENVIRONMENT \
            --lines 50 \
            --follow false
        
        echo
        echo "========================================"
        echo
    done
}

# Show detailed metrics
show_metrics() {
    local agents=$(get_agent_list)
    local time_range=${4:-24h}
    
    log_info "Showing metrics for environment: $ENVIRONMENT (last $time_range)"
    
    for agent in $agents; do
        log_info "Metrics for agent: $agent"
        echo "----------------------------------------"
        
        # Show detailed metrics
        show_agent_metrics "$agent" "$time_range"
        
        # Show CloudWatch dashboard URL
        echo
        log_info "CloudWatch Dashboard:"
        echo "https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#dashboards:name=Sentinel-${agent}-${ENVIRONMENT}"
        
        echo
        echo "========================================"
        echo
    done
}

# Run agent tests
test_agents() {
    local agents=$(get_agent_list)
    
    log_info "Running tests for environment: $ENVIRONMENT"
    
    for agent in $agents; do
        log_info "Testing agent: $agent"
        
        if $STRANDS_CLI test \
            --agent $agent \
            --environment $ENVIRONMENT \
            --test-suite comprehensive \
            --timeout 300; then
            
            log_info "Tests passed for $agent"
        else
            log_error "Tests failed for $agent"
        fi
    done
}

# Delete agents
delete_agents() {
    local agents=$(get_agent_list)
    
    log_warn "This will permanently delete agents for environment: $ENVIRONMENT"
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        log_info "Operation cancelled"
        return 0
    fi
    
    for agent in $agents; do
        log_warn "Deleting agent: $agent"
        
        # Create final backup
        backup_agent "$agent"
        
        if $STRANDS_CLI delete \
            --agent $agent \
            --environment $ENVIRONMENT \
            --force; then
            
            log_info "Successfully deleted $agent"
        else
            log_error "Failed to delete $agent"
        fi
    done
}

# Main function
main() {
    # Check if help is requested
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        show_usage
        exit 0
    fi
    
    # Validate parameters
    if [ -z "$ENVIRONMENT" ] || [ -z "$OPERATION" ]; then
        log_error "Environment and operation are required"
        show_usage
        exit 1
    fi
    
    # Change to agents directory
    cd "$(dirname "$0")"
    
    # Execute operation
    case $OPERATION in
        "status")
            show_status
            ;;
        "update")
            update_agents
            ;;
        "rollback")
            rollback_agents
            ;;
        "restart")
            restart_agents
            ;;
        "logs")
            show_logs
            ;;
        "metrics")
            show_metrics
            ;;
        "test")
            test_agents
            ;;
        "delete")
            delete_agents
            ;;
        *)
            log_error "Unknown operation: $OPERATION"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"