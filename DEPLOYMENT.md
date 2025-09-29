# Sentinel Cybersecurity Triage System - Deployment Guide

This guide provides step-by-step instructions for deploying the Sentinel Cybersecurity Triage System to AWS.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Deployment Steps](#detailed-deployment-steps)
4. [Environment Configuration](#environment-configuration)
5. [Validation and Testing](#validation-and-testing)
6. [Post-Deployment Configuration](#post-deployment-configuration)
7. [Troubleshooting](#troubleshooting)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)

## Prerequisites

### Required Tools

- **Terraform** >= 1.5.0
- **AWS CLI** >= 2.0.0
- **Python** >= 3.9
- **Node.js** >= 18.0 (for web application)
- **jq** (for JSON processing)
- **Git**

### AWS Requirements

- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- Sufficient service limits for:
  - Lambda functions (100+ concurrent executions)
  - DynamoDB tables (5+ tables)
  - S3 buckets (4+ buckets)
  - VPC resources (1 VPC, 6+ subnets)
  - OpenSearch Serverless collections (1 collection)

### Permissions Required

The deploying user/role needs the following AWS permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:*",
                "dynamodb:*",
                "s3:*",
                "lambda:*",
                "iam:*",
                "opensearch:*",
                "opensearchserverless:*",
                "events:*",
                "stepfunctions:*",
                "sqs:*",
                "sns:*",
                "cognito-idp:*",
                "apigateway:*",
                "amplify:*",
                "cloudwatch:*",
                "logs:*",
                "xray:*",
                "kms:*"
            ],
            "Resource": "*"
        }
    ]
}
```

## Quick Start

For a rapid deployment to the development environment:

```bash
# Clone the repository
git clone <repository-url>
cd sentinel

# Configure AWS credentials
aws configure

# Deploy to development environment
./scripts/deploy.sh -e dev -a

# Validate deployment
./scripts/validate-deployment.sh -e dev

# Configure RSS feeds (see Post-Deployment Configuration)
./scripts/configure-feeds.sh -e dev
```

## Detailed Deployment Steps

### Step 1: Environment Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd sentinel
   ```

2. **Install dependencies:**
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt
   
   # Install Node.js dependencies (for web app)
   cd web && npm install && cd ..
   ```

3. **Configure AWS CLI:**
   ```bash
   aws configure
   # Enter your AWS Access Key ID, Secret Access Key, Region, and Output format
   ```

4. **Verify AWS access:**
   ```bash
   aws sts get-caller-identity
   ```

### Step 2: Infrastructure Deployment

1. **Review environment configuration:**
   ```bash
   # Edit environment-specific variables
   vim infra/envs/dev.tfvars    # For development
   vim infra/envs/prod.tfvars   # For production
   ```

2. **Initialize Terraform:**
   ```bash
   cd infra
   terraform init
   ```

3. **Plan deployment:**
   ```bash
   # For development
   terraform plan -var-file="envs/dev.tfvars" -out=dev.tfplan
   
   # For production
   terraform plan -var-file="envs/prod.tfvars" -out=prod.tfplan
   ```

4. **Deploy infrastructure:**
   ```bash
   # Using deployment script (recommended)
   ./scripts/deploy.sh -e dev
   
   # Or manually with Terraform
   terraform apply dev.tfplan
   ```

### Step 3: Validation

1. **Run infrastructure validation:**
   ```bash
   ./scripts/validate-deployment.sh -e dev -v
   ```

2. **Check deployment status:**
   ```bash
   # View Terraform outputs
   cd infra && terraform output
   
   # Check AWS resources
   aws dynamodb list-tables
   aws s3 ls
   aws lambda list-functions
   ```

### Step 4: Application Deployment

1. **Deploy Lambda functions:**
   ```bash
   # Lambda functions are deployed automatically with Terraform
   # Verify deployment
   ./scripts/validate-infrastructure.py -e dev
   ```

2. **Deploy web application:**
   ```bash
   cd web
   npm run build
   
   # Deploy to Amplify (configured in Terraform)
   # Check Amplify console for deployment status
   ```

## Environment Configuration

### Development Environment (`dev.tfvars`)

- **Purpose:** Development and testing
- **Resources:** Minimal configuration for cost optimization
- **Features:** 
  - Pay-per-request DynamoDB
  - Smaller Lambda memory allocation
  - Reduced monitoring and alerting
  - Test data and mock configurations

### Production Environment (`prod.tfvars`)

- **Purpose:** Production workloads
- **Resources:** Full-scale configuration for performance
- **Features:**
  - Provisioned DynamoDB with auto-scaling
  - Higher Lambda memory and concurrency
  - Comprehensive monitoring and alerting
  - All 21 RSS feeds configured
  - Enhanced security settings

### Custom Configuration

To create a custom environment:

1. **Copy an existing configuration:**
   ```bash
   cp infra/envs/dev.tfvars infra/envs/staging.tfvars
   ```

2. **Modify settings as needed:**
   ```bash
   vim infra/envs/staging.tfvars
   ```

3. **Deploy with custom configuration:**
   ```bash
   ./scripts/deploy.sh -e staging
   ```

## Validation and Testing

### Infrastructure Validation

```bash
# Comprehensive infrastructure validation
./scripts/validate-deployment.sh -e dev

# Infrastructure-only validation (skip functional tests)
./scripts/validate-deployment.sh -e dev -s

# Verbose output for debugging
./scripts/validate-deployment.sh -e dev -v
```

### Performance Testing

```bash
# Run performance tests
cd tests/performance
make test-all

# Load testing with Locust
make test-locust

# Quick performance validation
make test-quick
```

### Security Validation

```bash
# Run security scans (if tfsec is installed)
cd infra
tfsec .

# Check IAM permissions
aws iam simulate-principal-policy \
    --policy-source-arn $(aws sts get-caller-identity --query Arn --output text) \
    --action-names dynamodb:GetItem s3:GetObject lambda:InvokeFunction \
    --resource-arns "*"
```

## Post-Deployment Configuration

### RSS Feed Configuration

1. **Configure RSS feeds:**
   ```bash
   ./scripts/configure-feeds.sh -e dev
   ```

2. **Verify feed configuration:**
   ```bash
   # Check DynamoDB for feed configurations
   aws dynamodb scan --table-name sentinel-feeds-dev --max-items 5
   ```

### Keyword Configuration

1. **Load target keywords:**
   ```bash
   # Keywords are configured in environment tfvars files
   # They are automatically loaded during deployment
   ```

2. **Update keywords:**
   ```bash
   # Edit the tfvars file and redeploy
   vim infra/envs/dev.tfvars
   ./scripts/deploy.sh -e dev
   ```

### User Management

1. **Create initial users:**
   ```bash
   # Use Cognito console or AWS CLI
   aws cognito-idp admin-create-user \
       --user-pool-id <user-pool-id> \
       --username admin \
       --user-attributes Name=email,Value=admin@example.com \
       --temporary-password TempPass123!
   ```

2. **Configure user groups:**
   ```bash
   # Create analyst and admin groups
   aws cognito-idp create-group \
       --group-name Analysts \
       --user-pool-id <user-pool-id> \
       --description "Security Analysts"
   ```

## Troubleshooting

### Common Issues

#### 1. Terraform State Lock

**Problem:** Terraform state is locked
```
Error: Error acquiring the state lock
```

**Solution:**
```bash
# Force unlock (use with caution)
terraform force-unlock <lock-id>

# Or wait for the lock to expire (usually 15 minutes)
```

#### 2. AWS Service Limits

**Problem:** Service limit exceeded
```
Error: LimitExceededException: Too many functions
```

**Solution:**
```bash
# Request service limit increase
aws service-quotas get-service-quota \
    --service-code lambda \
    --quota-code L-B99A9384

# Or clean up unused resources
```

#### 3. Lambda Deployment Failures

**Problem:** Lambda function deployment fails
```
Error: InvalidParameterValueException: The role defined for the function cannot be assumed by Lambda
```

**Solution:**
```bash
# Check IAM role trust policy
aws iam get-role --role-name <lambda-role-name>

# Verify Lambda execution role permissions
./scripts/validate-infrastructure.py -e dev -v
```

#### 4. VPC Endpoint Issues

**Problem:** Lambda functions cannot access AWS services
```
Error: Unable to connect to endpoint
```

**Solution:**
```bash
# Check VPC endpoints
aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=<vpc-id>

# Verify security groups and NACLs
aws ec2 describe-security-groups --group-ids <security-group-id>
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Terraform debug
export TF_LOG=DEBUG
terraform apply

# AWS CLI debug
aws --debug dynamodb list-tables

# Deployment script verbose mode
./scripts/deploy.sh -e dev --verbose
```

### Log Analysis

Check logs for issues:

```bash
# CloudWatch logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/sentinel"

# Deployment logs
tail -f logs/deployment_*.log

# Validation logs
tail -f logs/validation_*.log
```

## Monitoring and Maintenance

### CloudWatch Dashboards

Access monitoring dashboards:

1. **AWS Console:** CloudWatch → Dashboards → Sentinel-*
2. **Key Metrics:**
   - Lambda function invocations and errors
   - DynamoDB read/write capacity utilization
   - S3 request metrics
   - OpenSearch query performance

### Alerting

Configure alerts for:

- Lambda function errors > 1%
- DynamoDB throttling events
- S3 4xx/5xx errors
- High memory utilization
- Processing latency > 5 minutes

### Regular Maintenance

1. **Weekly:**
   - Review CloudWatch metrics
   - Check error logs
   - Validate feed processing

2. **Monthly:**
   - Update Lambda function code
   - Review and update RSS feed list
   - Performance testing
   - Security updates

3. **Quarterly:**
   - Cost optimization review
   - Capacity planning
   - Disaster recovery testing
   - Security audit

### Backup and Recovery

1. **Automated Backups:**
   - DynamoDB point-in-time recovery (enabled in prod)
   - S3 cross-region replication (enabled in prod)
   - Lambda function versioning

2. **Manual Backups:**
   ```bash
   # Export DynamoDB table
   aws dynamodb export-table-to-point-in-time \
       --table-arn <table-arn> \
       --s3-bucket <backup-bucket>
   
   # Backup Lambda function code
   aws lambda get-function --function-name <function-name>
   ```

### Scaling

Monitor and adjust capacity:

```bash
# DynamoDB auto-scaling
aws application-autoscaling describe-scalable-targets \
    --service-namespace dynamodb

# Lambda concurrency limits
aws lambda get-account-settings

# OpenSearch capacity
aws opensearchserverless get-capacity-policy \
    --name <policy-name>
```

## Support and Documentation

- **Architecture Documentation:** See `docs/architecture.md`
- **API Documentation:** See `docs/api.md`
- **Troubleshooting Guide:** See `docs/troubleshooting.md`
- **Security Guide:** See `docs/security.md`

For additional support, please refer to the project documentation or contact the development team.