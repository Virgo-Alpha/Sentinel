# Sentinel Agent Deployment and Management

This directory contains comprehensive scripts and configurations for deploying and managing Sentinel cybersecurity triage agents using Strands and AWS Bedrock AgentCore.

## Overview

The Sentinel system uses two primary AI agents:

1. **Ingestor Agent** (`sentinel-ingestor-agent`): Autonomous content processing and triage
2. **Analyst Assistant Agent** (`sentinel-analyst-assistant`): Interactive query processing and human collaboration

## Files Structure

```
agents/
├── README.md                          # This documentation
├── ingestor-agent.yaml                # Ingestor agent configuration
├── analyst-assistant-agent.yaml       # Analyst assistant configuration
├── deploy-agents.sh                   # Main deployment script
├── manage-agents.sh                   # Agent management script
├── ci-cd-integration.sh               # CI/CD pipeline integration
├── monitoring/
│   └── dashboard-template.json        # CloudWatch dashboard template
├── backups/                           # Agent configuration backups
├── deployments/                       # Deployment metadata
└── artifacts/                         # Build artifacts
```

## Prerequisites

### Required Tools

1. **Strands CLI**: Install from [Strands Documentation](https://docs.strands.ai/installation)
2. **AWS CLI**: Configured with appropriate permissions
3. **yamllint**: For YAML validation (optional but recommended)
4. **envsubst**: For environment variable substitution
5. **bc**: For mathematical calculations in scripts

### AWS Permissions

The deployment requires the following AWS permissions:

- **Bedrock**: Full access to agents and models
- **Lambda**: List and invoke functions
- **DynamoDB**: Read/write access to tables
- **S3**: Read/write access to buckets
- **CloudWatch**: Create dashboards and alarms
- **SES**: Send email notifications (optional)
- **IAM**: Pass role permissions

### Environment Variables

Set the following environment variables before deployment:

```bash
export AWS_ACCOUNT_ID="123456789012"
export AWS_REGION="us-east-1"
export DYNAMODB_ARTICLES_TABLE="sentinel-articles-dev"
export DYNAMODB_MEMORY_TABLE="sentinel-memory-dev"
export S3_CONTENT_BUCKET="sentinel-content-dev"
export S3_ARTIFACTS_BUCKET="sentinel-artifacts-dev"
export OPENSEARCH_ENDPOINT="https://search-sentinel-dev.us-east-1.es.amazonaws.com"
export KMS_KEY_ID="arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
export PRIVATE_SUBNET_1_ID="subnet-12345678"
export PRIVATE_SUBNET_2_ID="subnet-87654321"
export LAMBDA_SECURITY_GROUP_ID="sg-12345678"
```

## Deployment

### Basic Deployment

Deploy agents to a specific environment:

```bash
# Deploy to development environment
./deploy-agents.sh dev

# Deploy to staging environment
./deploy-agents.sh staging

# Deploy to production environment
./deploy-agents.sh prod
```

### Advanced Deployment Options

Configure deployment behavior with environment variables:

```bash
# Deploy with custom timeout
export DEPLOYMENT_TIMEOUT=1200
./deploy-agents.sh prod

# Deploy without rollback on failure
export ROLLBACK_ON_FAILURE=false
./deploy-agents.sh staging

# Increase health check retries
export HEALTH_CHECK_RETRIES=10
./deploy-agents.sh dev
```

### Deployment Process

The deployment script performs the following steps:

1. **Prerequisites Check**: Validates tools and permissions
2. **Configuration Validation**: Checks YAML syntax and Strands configuration
3. **Backup Creation**: Backs up existing agents
4. **Agent Deployment**: Deploys agents with timeout protection
5. **Health Checks**: Validates agent functionality
6. **Monitoring Setup**: Creates CloudWatch dashboards and alarms
7. **Testing**: Runs comprehensive agent tests
8. **Reporting**: Generates deployment report

## Management

### Agent Status

Check the status of deployed agents:

```bash
# Check all agents
./manage-agents.sh dev status

# Check specific agent
./manage-agents.sh dev status sentinel-ingestor-agent
```

### Agent Updates

Update agents to the latest configuration:

```bash
# Update all agents
./manage-agents.sh dev update

# Update specific agent
./manage-agents.sh dev update sentinel-analyst-assistant
```

### Rollback

Rollback agents to the previous version:

```bash
# Rollback all agents
./manage-agents.sh dev rollback

# Rollback specific agent
./manage-agents.sh dev rollback sentinel-ingestor-agent
```

### Monitoring

View agent metrics and logs:

```bash
# Show performance metrics
./manage-agents.sh dev metrics

# Show agent logs
./manage-agents.sh dev logs

# Show metrics for specific time range
./manage-agents.sh dev metrics all 7d
```

### Testing

Run comprehensive agent tests:

```bash
# Test all agents
./manage-agents.sh dev test

# Test specific agent
./manage-agents.sh dev test sentinel-analyst-assistant
```

## CI/CD Integration

### Pipeline Stages

The CI/CD integration script supports the following pipeline stages:

1. **Build**: Validate configurations and create artifacts
2. **Test**: Run comprehensive tests
3. **Deploy**: Deploy agents to target environment
4. **Promote**: Promote from staging to production
5. **Rollback**: Rollback to previous version
6. **Cleanup**: Clean up old artifacts

### Usage Examples

```bash
# Build stage
./ci-cd-integration.sh build dev abc123 20241201120000

# Test stage
./ci-cd-integration.sh test dev abc123 20241201120000

# Deploy stage
./ci-cd-integration.sh deploy staging abc123 20241201120000

# Promote to production
./ci-cd-integration.sh promote prod

# Rollback production
./ci-cd-integration.sh rollback prod
```

### CI/CD Environment Variables

Configure CI/CD behavior:

```bash
export CI_MODE=true                    # Enable CI/CD mode
export SLACK_WEBHOOK_URL="https://..."  # Slack notifications
export TEAMS_WEBHOOK_URL="https://..."  # Teams notifications
export EMAIL_NOTIFICATIONS=true        # Email notifications
export PARALLEL_DEPLOYMENT=true        # Deploy agents in parallel
export SKIP_TESTS=false                # Skip test execution
```

### GitHub Actions Integration

Example GitHub Actions workflow:

```yaml
name: Deploy Sentinel Agents

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Strands CLI
        run: |
          curl -sSL https://install.strands.ai | bash
          echo "$HOME/.strands/bin" >> $GITHUB_PATH
      - name: Build
        run: ./agents/ci-cd-integration.sh build dev ${{ github.sha }} ${{ github.run_number }}
        env:
          CI_MODE: true
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Test
        run: ./agents/ci-cd-integration.sh test dev ${{ github.sha }} ${{ github.run_number }}
        env:
          CI_MODE: true

  deploy-staging:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Staging
        run: ./agents/ci-cd-integration.sh deploy staging ${{ github.sha }} ${{ github.run_number }}
        env:
          CI_MODE: true
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - uses: actions/checkout@v3
      - name: Promote to Production
        run: ./agents/ci-cd-integration.sh promote prod
        env:
          CI_MODE: true
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

## Monitoring and Observability

### CloudWatch Dashboards

The deployment automatically creates CloudWatch dashboards with the following metrics:

- **Agent Performance**: Invocations, duration, errors, error rates
- **Processing Metrics**: Articles processed, published, escalated
- **Feed Status**: Successful and failed feed fetches
- **Infrastructure**: Bedrock model performance, DynamoDB capacity, S3 usage

### CloudWatch Alarms

Automatic alarms are created for:

- High error rates (>5%)
- Low processing rates (<1 per 10 minutes)
- Agent health check failures

### Log Analysis

View agent logs using CloudWatch Logs Insights:

```sql
SOURCE '/aws/lambda/sentinel-ingestor-agent'
| SOURCE '/aws/lambda/sentinel-analyst-assistant'
| fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100
```

## Troubleshooting

### Common Issues

#### 1. Deployment Timeout

**Symptoms**: Deployment hangs or times out
**Solutions**:
- Increase `DEPLOYMENT_TIMEOUT` environment variable
- Check AWS service limits
- Verify network connectivity to Bedrock

#### 2. Health Check Failures

**Symptoms**: Agents deploy but fail health checks
**Solutions**:
- Check agent logs for errors
- Verify Lambda function permissions
- Ensure all required environment variables are set

#### 3. Configuration Validation Errors

**Symptoms**: YAML or Strands validation fails
**Solutions**:
- Run `yamllint` on configuration files
- Check for missing required fields
- Verify environment variable substitution

#### 4. Permission Errors

**Symptoms**: AWS API calls fail with permission errors
**Solutions**:
- Review IAM policies
- Check role trust relationships
- Verify resource ARNs in configurations

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
./deploy-agents.sh dev
```

### Manual Verification

Manually test agent functionality:

```bash
# Test ingestor agent
strands invoke \
  --agent sentinel-ingestor-agent \
  --environment dev \
  --input '{"task": "health_check", "test_mode": true}'

# Test analyst assistant
strands invoke \
  --agent sentinel-analyst-assistant \
  --environment dev \
  --input "What are the recent security vulnerabilities?"
```

## Security Considerations

### IAM Roles

Agents use least-privilege IAM roles with permissions limited to:

- Required AWS services (Bedrock, Lambda, DynamoDB, S3)
- Specific resources within the environment
- No cross-environment access

### Network Security

Agents are deployed in private subnets with:

- VPC endpoints for AWS services
- Security groups restricting traffic
- No direct internet access

### Data Protection

- All data encrypted at rest using KMS
- Sensitive information redacted from logs
- PII detection and removal in processing pipeline

### Secrets Management

- Use AWS Systems Manager Parameter Store for configuration
- Rotate credentials regularly
- Never store secrets in code or configuration files

## Performance Optimization

### Scaling Configuration

Adjust agent performance based on workload:

```yaml
# In agent configuration
deployment:
  memory_mb: 2048        # Increase for heavy workloads
  timeout_seconds: 900   # Adjust based on processing time
  
behavior:
  performance:
    batch_processing: true      # Enable for high throughput
    parallel_tool_calls: true   # Parallel tool execution
    caching_enabled: true       # Cache frequently accessed data
```

### Cost Optimization

Monitor and optimize costs:

- Use appropriate memory allocation for Lambda functions
- Implement caching to reduce API calls
- Set up cost alerts and budgets
- Regular cleanup of old artifacts and logs

## Support and Maintenance

### Regular Maintenance Tasks

1. **Weekly**: Review agent performance metrics
2. **Monthly**: Update agent configurations and dependencies
3. **Quarterly**: Review and optimize costs
4. **Annually**: Security audit and permission review

### Getting Help

- Check agent logs in CloudWatch
- Review deployment reports
- Use debug mode for detailed troubleshooting
- Contact the development team for complex issues

### Contributing

When making changes to agent configurations:

1. Test changes in development environment first
2. Update documentation as needed
3. Follow the CI/CD pipeline for deployments
4. Monitor post-deployment metrics

## Version History

- **v1.0.0**: Initial agent deployment scripts
- **v1.1.0**: Added CI/CD integration and monitoring
- **v1.2.0**: Enhanced error handling and rollback capabilities
- **v1.3.0**: Added comprehensive management scripts