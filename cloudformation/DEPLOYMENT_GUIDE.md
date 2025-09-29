# Sentinel CloudFormation Deployment Guide

This comprehensive guide covers deploying the Sentinel Cybersecurity Triage Platform using AWS CloudFormation as an alternative to Terraform.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Template Architecture](#template-architecture)
4. [Deployment Options](#deployment-options)
5. [Step-by-Step Deployment](#step-by-step-deployment)
6. [Configuration Management](#configuration-management)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)
8. [Troubleshooting](#troubleshooting)
9. [Cost Optimization](#cost-optimization)
10. [Security Considerations](#security-considerations)

## Overview

The CloudFormation templates provide a complete infrastructure-as-code solution for deploying Sentinel, including:

- **Core Infrastructure**: VPC, subnets, security groups, NAT gateways
- **Storage Layer**: S3 buckets, DynamoDB tables with GSIs
- **Compute Layer**: Lambda functions with proper IAM roles
- **Orchestration**: Step Functions, EventBridge scheduling
- **Messaging**: SQS queues, SNS topics for notifications
- **Security**: KMS encryption, VPC endpoints, WAF protection
- **Monitoring**: CloudWatch dashboards, X-Ray tracing, alarms
- **Web Interface**: Cognito authentication, API Gateway, Amplify hosting

## Prerequisites

### AWS Account Setup

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Bedrock Model Access** enabled for:
   - `anthropic.claude-3-5-sonnet-20241022-v2:0`
   - `amazon.titan-embed-text-v1`
4. **SES Email Verification** for notification addresses
5. **Service Limits** reviewed and increased if necessary

### Required Permissions

Your AWS user/role needs the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "iam:*",
        "lambda:*",
        "s3:*",
        "dynamodb:*",
        "opensearch:*",
        "bedrock:*",
        "cognito-idp:*",
        "apigateway:*",
        "amplify:*",
        "events:*",
        "states:*",
        "sqs:*",
        "sns:*",
        "ses:*",
        "kms:*",
        "logs:*",
        "xray:*",
        "wafv2:*",
        "ec2:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### Local Environment

```bash
# Install required tools
pip install awscli
pip install cfn-lint  # Optional but recommended

# Configure AWS CLI
aws configure

# Verify access
aws sts get-caller-identity
```

## Template Architecture

### Template Files

1. **sentinel-infrastructure-complete.yaml**
   - Single comprehensive template
   - All resources in one stack
   - Best for development and testing

2. **sentinel-vpc-networking.yaml**
   - VPC and networking components only
   - Modular approach for production
   - Can be shared across environments

3. **sentinel-storage.yaml**
   - S3 buckets and DynamoDB tables
   - Separate lifecycle management
   - Data persistence layer

### Parameter Files

- **parameters-dev.json**: Development environment settings
- **parameters-prod.json**: Production environment settings

## Deployment Options

### Option 1: Complete Stack (Recommended for Development)

Deploy everything in a single stack:

```bash
# Development
./deploy.sh -e dev -a create

# Production
./deploy.sh -e prod -a create
```

### Option 2: Modular Deployment (Recommended for Production)

Deploy components separately:

```bash
# 1. VPC and Networking
./deploy.sh -e prod -t vpc -a create

# 2. Storage Components
./deploy.sh -e prod -t storage -a create

# 3. Complete Infrastructure (references existing VPC/storage)
./deploy.sh -e prod -t complete -a create
```

### Option 3: Manual AWS CLI

Direct CloudFormation commands:

```bash
# Validate template
aws cloudformation validate-template \
  --template-body file://sentinel-infrastructure-complete.yaml

# Create stack
aws cloudformation create-stack \
  --stack-name sentinel-prod-complete \
  --template-body file://sentinel-infrastructure-complete.yaml \
  --parameters file://parameters-prod.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Monitor progress
aws cloudformation describe-stack-events \
  --stack-name sentinel-prod-complete
```

## Step-by-Step Deployment

### Step 1: Preparation

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd Sentinel/cloudformation
   ```

2. **Validate Templates**
   ```bash
   ./validate-templates.sh
   ```

3. **Review Parameters**
   ```bash
   # Edit parameter files as needed
   vim parameters-dev.json
   vim parameters-prod.json
   ```

### Step 2: Development Deployment

1. **Deploy Development Environment**
   ```bash
   ./deploy.sh -e dev -a create
   ```

2. **Verify Deployment**
   ```bash
   ./deploy.sh -e dev -a status
   ```

3. **Test Basic Functionality**
   ```bash
   # Check S3 buckets
   aws s3 ls | grep sentinel-dev
   
   # Check DynamoDB tables
   aws dynamodb list-tables | grep sentinel-dev
   
   # Check Lambda functions
   aws lambda list-functions | grep sentinel-dev
   ```

### Step 3: Production Deployment

1. **Review Production Parameters**
   ```bash
   cat parameters-prod.json
   ```

2. **Deploy Production Environment**
   ```bash
   ./deploy.sh -e prod -a create
   ```

3. **Configure Additional Services**
   ```bash
   # Set up SES email identities
   aws ses verify-email-identity --email-address security-team@company.com
   
   # Configure Cognito users (if Amplify enabled)
   aws cognito-idp admin-create-user \
     --user-pool-id <USER_POOL_ID> \
     --username admin \
     --temporary-password TempPass123! \
     --message-action SUPPRESS
   ```

### Step 4: Post-Deployment Configuration

1. **Upload Lambda Packages**
   ```bash
   # Build and upload Lambda deployment packages
   cd ../src
   zip -r feed-parser.zip lambda_tools/feed_parser.py
   aws s3 cp feed-parser.zip s3://sentinel-prod-artifacts-<suffix>/lambda-packages/
   ```

2. **Configure RSS Feeds**
   ```bash
   # Upload feed configuration
   aws s3 cp ../config/feeds.yaml s3://sentinel-prod-content-<suffix>/config/
   ```

3. **Set Up Monitoring**
   ```bash
   # Create additional CloudWatch alarms
   aws cloudwatch put-metric-alarm \
     --alarm-name "Sentinel-HighErrorRate" \
     --alarm-description "High error rate in Lambda functions" \
     --metric-name Errors \
     --namespace AWS/Lambda \
     --statistic Sum \
     --period 300 \
     --threshold 10 \
     --comparison-operator GreaterThanThreshold
   ```

## Configuration Management

### Environment Variables

Key configuration parameters are set via CloudFormation parameters and passed as environment variables to Lambda functions:

```yaml
Environment:
  Variables:
    ENVIRONMENT: !Ref Environment
    PROJECT_NAME: !Ref ProjectName
    ARTICLES_TABLE: !Ref ArticlesTable
    BEDROCK_MODEL_ID: !Ref BedrockModelId
    RELEVANCE_THRESHOLD: !Ref RelevanceThreshold
```

### Feature Flags

Control deployment components using feature flags:

- **EnableAgents**: Deploy Bedrock AgentCore integration
- **EnableAmplify**: Deploy web application components
- **EnableOpenSearch**: Deploy vector search capabilities
- **EnableEmailNotifications**: Deploy SES email system

### Parameter Customization

Modify parameter files for your environment:

```json
{
  "ParameterKey": "RelevanceThreshold",
  "ParameterValue": "0.8"
},
{
  "ParameterKey": "MaxDailyLLMCalls",
  "ParameterValue": "10000"
}
```

## Monitoring and Maintenance

### CloudWatch Dashboards

Access the automatically created dashboard:
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=sentinel-prod-dashboard
```

### Key Metrics to Monitor

1. **Lambda Function Metrics**
   - Invocation count
   - Error rate
   - Duration
   - Throttles

2. **DynamoDB Metrics**
   - Read/Write capacity utilization
   - Throttled requests
   - Item count

3. **S3 Metrics**
   - Storage utilization
   - Request metrics
   - Error rates

4. **Cost Metrics**
   - Daily spend by service
   - Monthly budget alerts

### Maintenance Tasks

1. **Regular Updates**
   ```bash
   # Update stack with new parameters
   ./deploy.sh -e prod -a update
   ```

2. **Log Management**
   ```bash
   # Review CloudWatch logs
   aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/sentinel-prod"
   ```

3. **Security Updates**
   ```bash
   # Rotate KMS keys annually
   aws kms create-key --description "Sentinel encryption key rotation"
   ```

## Troubleshooting

### Common Issues

1. **Stack Creation Fails**
   ```bash
   # Check stack events
   aws cloudformation describe-stack-events --stack-name sentinel-prod-complete
   
   # Common causes:
   # - Insufficient IAM permissions
   # - Resource limits exceeded
   # - Invalid parameter values
   # - Bedrock model access not enabled
   ```

2. **Lambda Functions Not Working**
   ```bash
   # Check function logs
   aws logs tail /aws/lambda/sentinel-prod-feed-parser --follow
   
   # Common causes:
   # - Missing deployment packages
   # - VPC configuration issues
   # - Environment variable errors
   ```

3. **DynamoDB Throttling**
   ```bash
   # Check table metrics
   aws dynamodb describe-table --table-name sentinel-prod-articles
   
   # Solutions:
   # - Switch to on-demand billing
   # - Increase provisioned capacity
   # - Implement exponential backoff
   ```

### Debugging Commands

```bash
# Validate template syntax
aws cloudformation validate-template --template-body file://template.yaml

# Check stack status
aws cloudformation describe-stacks --stack-name sentinel-prod-complete

# View stack outputs
aws cloudformation describe-stacks \
  --stack-name sentinel-prod-complete \
  --query 'Stacks[0].Outputs'

# Check resource status
aws cloudformation list-stack-resources --stack-name sentinel-prod-complete
```

## Cost Optimization

### Development Environment

- Use smaller Lambda memory sizes (256 MB)
- Shorter S3 retention periods (90 days)
- Pay-per-request DynamoDB billing
- Disable detailed monitoring

### Production Environment

- Right-size Lambda functions based on metrics
- Use S3 Intelligent Tiering
- Consider DynamoDB reserved capacity
- Implement lifecycle policies

### Cost Monitoring

```bash
# Set up budget alerts
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget '{
    "BudgetName": "Sentinel-Monthly-Budget",
    "BudgetLimit": {
      "Amount": "1000",
      "Unit": "USD"
    },
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }'
```

## Security Considerations

### Encryption

- All data encrypted at rest using KMS
- In-transit encryption for all communications
- Separate KMS keys per environment

### Access Control

- Least privilege IAM policies
- VPC endpoints for AWS service communication
- Security groups restrict network access

### Compliance

- CloudTrail logging enabled
- VPC Flow Logs for network monitoring
- Resource tagging for governance

### Security Monitoring

```bash
# Enable GuardDuty
aws guardduty create-detector --enable

# Enable Security Hub
aws securityhub enable-security-hub

# Enable Config
aws configservice put-configuration-recorder \
  --configuration-recorder name=default,roleARN=arn:aws:iam::account:role/config-role
```

## Disaster Recovery

### Backup Strategy

1. **DynamoDB**: Point-in-time recovery enabled
2. **S3**: Cross-region replication for critical data
3. **Lambda**: Code stored in version control
4. **Configuration**: Infrastructure as code in Git

### Recovery Procedures

```bash
# Restore DynamoDB table
aws dynamodb restore-table-to-point-in-time \
  --source-table-name sentinel-prod-articles \
  --target-table-name sentinel-prod-articles-restored \
  --restore-date-time 2024-01-01T00:00:00.000Z

# Redeploy infrastructure
./deploy.sh -e prod -a create -s sentinel-prod-recovery
```

## Migration from Terraform

If migrating from existing Terraform infrastructure:

1. **Export Terraform State**
   ```bash
   terraform show -json > terraform-state.json
   ```

2. **Map Resources**
   - Compare Terraform resources with CloudFormation
   - Identify resources to import vs recreate

3. **Import Existing Resources**
   ```bash
   aws cloudformation create-change-set \
     --stack-name sentinel-prod-complete \
     --change-set-name import-existing \
     --template-body file://template.yaml \
     --change-set-type IMPORT \
     --resources-to-import file://resources-to-import.json
   ```

4. **Validate Migration**
   - Test all functionality
   - Verify data integrity
   - Update monitoring and alerting

## Support and Documentation

### Additional Resources

- [AWS CloudFormation Documentation](https://docs.aws.amazon.com/cloudformation/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [Sentinel Terraform Documentation](../infra/README.md)

### Getting Help

1. **AWS Support**: For infrastructure issues
2. **CloudFormation Forums**: Community support
3. **Project Documentation**: Internal knowledge base
4. **Monitoring Dashboards**: Real-time system status

This deployment guide provides comprehensive coverage of deploying Sentinel using CloudFormation as a backup to the primary Terraform infrastructure.