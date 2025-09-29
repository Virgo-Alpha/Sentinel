# Sentinel CloudFormation Deployment Guide

This directory contains AWS CloudFormation templates as a backup deployment method for the Sentinel Cybersecurity Triage Platform. These templates provide an alternative to the primary Terraform infrastructure.

## Template Structure

### Main Templates

1. **sentinel-infrastructure-complete.yaml** - Complete infrastructure stack (single template)
2. **sentinel-vpc-networking.yaml** - VPC and networking components
3. **sentinel-storage.yaml** - S3 buckets and DynamoDB tables

### Parameter Files

- **parameters-dev.json** - Development environment configuration
- **parameters-prod.json** - Production environment configuration

## Prerequisites

Before deploying the CloudFormation stack, ensure you have:

1. **AWS CLI configured** with appropriate permissions
2. **Lambda deployment packages** uploaded to S3
3. **SES email identities** verified for notifications
4. **Bedrock model access** enabled in your AWS account

## Deployment Instructions

### Option 1: Single Stack Deployment (Recommended for Testing)

Deploy the complete infrastructure in a single stack:

```bash
# Deploy development environment
aws cloudformation create-stack \
  --stack-name sentinel-dev-complete \
  --template-body file://sentinel-infrastructure-complete.yaml \
  --parameters file://parameters-dev.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Deploy production environment
aws cloudformation create-stack \
  --stack-name sentinel-prod-complete \
  --template-body file://sentinel-infrastructure-complete.yaml \
  --parameters file://parameters-prod.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### Option 2: Modular Deployment (Recommended for Production)

Deploy components in separate stacks for better management:

```bash
# 1. Deploy VPC and networking
aws cloudformation create-stack \
  --stack-name sentinel-prod-vpc \
  --template-body file://sentinel-vpc-networking.yaml \
  --parameters ParameterKey=Environment,ParameterValue=prod \
               ParameterKey=ProjectName,ParameterValue=sentinel \
               ParameterKey=VpcCidr,ParameterValue=10.1.0.0/16 \
  --region us-east-1

# 2. Deploy storage components
aws cloudformation create-stack \
  --stack-name sentinel-prod-storage \
  --template-body file://sentinel-storage.yaml \
  --parameters ParameterKey=Environment,ParameterValue=prod \
               ParameterKey=ProjectName,ParameterValue=sentinel \
               ParameterKey=ContentRetentionDays,ParameterValue=2555 \
               ParameterKey=DynamoDBBillingMode,ParameterValue=PROVISIONED \
               ParameterKey=KMSKeyArn,ParameterValue=<KMS_KEY_ARN> \
               ParameterKey=RandomSuffix,ParameterValue=<RANDOM_SUFFIX> \
  --region us-east-1
```

## Stack Updates

To update an existing stack:

```bash
aws cloudformation update-stack \
  --stack-name sentinel-prod-complete \
  --template-body file://sentinel-infrastructure-complete.yaml \
  --parameters file://parameters-prod.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

## Stack Deletion

To delete a stack (be careful with production data):

```bash
# Delete development stack
aws cloudformation delete-stack \
  --stack-name sentinel-dev-complete \
  --region us-east-1

# Delete production stack (use with extreme caution)
aws cloudformation delete-stack \
  --stack-name sentinel-prod-complete \
  --region us-east-1
```

## Parameter Customization

### Environment-Specific Parameters

#### Development Environment
- **LambdaMemorySize**: 256 MB (cost-optimized)
- **ContentRetentionDays**: 90 days
- **MaxDailyLLMCalls**: 1,000 calls
- **LogRetentionDays**: 7 days
- **EnableAgents**: false (start with direct Lambda orchestration)

#### Production Environment
- **LambdaMemorySize**: 1024 MB (performance-optimized)
- **ContentRetentionDays**: 2555 days (7 years for compliance)
- **MaxDailyLLMCalls**: 50,000 calls
- **LogRetentionDays**: 365 days
- **EnableAgents**: true (use Bedrock AgentCore)

### Feature Flags

Control which components are deployed:

- **EnableAgents**: Deploy Bedrock AgentCore integration
- **EnableAmplify**: Deploy web application
- **EnableOpenSearch**: Deploy vector search capabilities
- **EnableEmailNotifications**: Deploy SES email system

### Cost Controls

Set limits to prevent unexpected charges:

- **MaxDailyLLMCalls**: Limit Bedrock API usage
- **MaxMonthlyCostUSD**: Budget alert threshold
- **ContentRetentionDays**: S3 lifecycle management

## Resource Naming Convention

All resources follow the pattern: `{ProjectName}-{Environment}-{ResourceType}-{RandomSuffix}`

Examples:
- S3 Bucket: `sentinel-prod-content-a1b2c3d4`
- DynamoDB Table: `sentinel-prod-articles`
- Lambda Function: `sentinel-prod-feed-parser`

## Monitoring and Observability

The CloudFormation templates include:

1. **CloudWatch Dashboards** - Key metrics and performance indicators
2. **X-Ray Tracing** - Distributed tracing for Lambda functions
3. **CloudWatch Alarms** - Automated alerting for failures
4. **Cost Tracking** - Budget alerts and cost optimization

## Security Features

Built-in security controls:

1. **KMS Encryption** - All data encrypted at rest
2. **VPC Endpoints** - Private communication with AWS services
3. **IAM Least Privilege** - Minimal required permissions
4. **WAF Protection** - Web application firewall (when Amplify enabled)

## Troubleshooting

### Common Issues

1. **Stack Creation Fails**
   - Check IAM permissions
   - Verify parameter values
   - Ensure resource limits not exceeded

2. **Lambda Functions Not Working**
   - Verify deployment packages in S3
   - Check VPC configuration
   - Review CloudWatch logs

3. **SES Email Issues**
   - Verify email identities
   - Check SES sending limits
   - Review bounce/complaint rates

### Validation Commands

```bash
# Validate template syntax
aws cloudformation validate-template \
  --template-body file://sentinel-infrastructure-complete.yaml

# Check stack status
aws cloudformation describe-stacks \
  --stack-name sentinel-prod-complete \
  --region us-east-1

# View stack events
aws cloudformation describe-stack-events \
  --stack-name sentinel-prod-complete \
  --region us-east-1
```

## Migration from Terraform

If migrating from Terraform to CloudFormation:

1. **Export Terraform State** - Document existing resources
2. **Import Resources** - Use CloudFormation import functionality
3. **Validate Configuration** - Ensure parameter parity
4. **Test Deployment** - Deploy to development first
5. **Update DNS/Endpoints** - Update any hardcoded references

## Support and Maintenance

### Regular Tasks

1. **Update Parameters** - Adjust thresholds and limits
2. **Review Costs** - Monitor spending against budgets
3. **Update Templates** - Apply security patches and improvements
4. **Backup Validation** - Test disaster recovery procedures

### Scaling Considerations

- **DynamoDB**: Switch to provisioned capacity for predictable workloads
- **Lambda**: Adjust memory and timeout based on performance metrics
- **S3**: Implement intelligent tiering for cost optimization
- **OpenSearch**: Scale capacity units based on query volume

## Compliance and Governance

The templates support:

- **SOC 2 Type II** - Audit logging and access controls
- **ISO 27001** - Security management framework
- **GDPR** - Data protection and privacy controls
- **NIST Cybersecurity Framework** - Risk management practices

## Contact and Support

For issues with CloudFormation deployment:

1. Check AWS CloudFormation documentation
2. Review CloudWatch logs for detailed error messages
3. Consult AWS Support for complex infrastructure issues
4. Reference Terraform implementation for configuration guidance