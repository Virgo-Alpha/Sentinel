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

3. **Configure Cognito, Amplify, and AgentCore**

   **IMPORTANT**: The current CloudFormation template is missing the actual Cognito, Amplify, and Bedrock AgentCore resources. You need to add these resources to the template first.

   #### 3.1 Deploy Missing Components
   
   The template currently only has feature flags but not the actual resources. You need to:
   
   ```bash
   # First, update the CloudFormation template to include missing resources
   # See the "Missing Components" section below for required additions
   
   # Then deploy with the updated template
   ./deploy.sh -e prod -a update
   ```

   #### 3.2 Configure Cognito (After adding Cognito resources to template)
   ```bash
   # Get the User Pool ID from stack outputs
   USER_POOL_ID=$(aws cloudformation describe-stacks \
     --stack-name sentinel-prod-complete \
     --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
     --output text)
   
   # Create admin user
   aws cognito-idp admin-create-user \
     --user-pool-id $USER_POOL_ID \
     --username admin \
     --temporary-password TempPass123! \
     --message-action SUPPRESS \
     --user-attributes Name=email,Value=admin@company.com
   
   # Set permanent password
   aws cognito-idp admin-set-user-password \
     --user-pool-id $USER_POOL_ID \
     --username admin \
     --password SecurePassword123! \
     --permanent
   ```

   #### 3.3 Configure Amplify (After adding Amplify resources to template)
   ```bash
   # Get the Amplify App ID from stack outputs
   AMPLIFY_APP_ID=$(aws cloudformation describe-stacks \
     --stack-name sentinel-prod-complete \
     --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppId`].OutputValue' \
     --output text)
   
   # Connect to Git repository
   aws amplify create-branch \
     --app-id $AMPLIFY_APP_ID \
     --branch-name main \
     --framework React
   
   # Start deployment
   aws amplify start-job \
     --app-id $AMPLIFY_APP_ID \
     --branch-name main \
     --job-type RELEASE
   ```

   #### 3.4 Configure Bedrock AgentCore (After adding Agent resources to template)
   ```bash
   # Get the Agent ID from stack outputs
   AGENT_ID=$(aws cloudformation describe-stacks \
     --stack-name sentinel-prod-complete \
     --query 'Stacks[0].Outputs[?OutputKey==`IngestorAgentId`].OutputValue' \
     --output text)
   
   # Create agent alias for production
   aws bedrock-agent create-agent-alias \
     --agent-id $AGENT_ID \
     --agent-alias-name production \
     --description "Production alias for Sentinel ingestor agent"
   
   # Prepare the agent (this makes it ready for invocation)
   aws bedrock-agent prepare-agent \
     --agent-id $AGENT_ID
   ```

4. **Set up SES email identities**
   ```bash
   aws ses verify-email-identity --email-address security-team@company.com
   ```

### Step 4: Deploy Lambda Functions

1. **Prepare Lambda Source Code**
   
   Create the required source code structure as detailed in `LAMBDA_DEPLOYMENT_GUIDE.md`. The basic structure should be:
   
   ```
   src/
   ├── common/                    # Shared utilities
   ├── lambda_tools/
   │   ├── feed_parser/
   │   ├── relevancy_evaluator/
   │   ├── dedup_tool/
   │   ├── guardrail_tool/
   │   ├── storage_tool/
   │   ├── human_escalation/
   │   ├── notifier/
   │   ├── analyst_assistant/
   │   ├── query_kb/
   │   ├── commentary_api/
   │   └── publish_decision/
   ```

2. **Get Artifacts Bucket Name**
   ```bash
   # Get the artifacts bucket name from CloudFormation outputs
   ARTIFACTS_BUCKET=$(aws cloudformation describe-stacks \
     --stack-name sentinel-prod-complete \
     --query 'Stacks[0].Outputs[?OutputKey==`ArtifactsBucketName`].OutputValue' \
     --output text)
   
   echo "Artifacts bucket: $ARTIFACTS_BUCKET"
   ```

3. **Deploy Lambda Packages**
   ```bash
   # Use the automated deployment script
   ./deploy-lambda-packages.sh -e prod -b $ARTIFACTS_BUCKET
   
   # Or deploy specific functions
   ./deploy-lambda-packages.sh -e prod -b $ARTIFACTS_BUCKET -f feed-parser
   ./deploy-lambda-packages.sh -e prod -b $ARTIFACTS_BUCKET -f relevancy-evaluator
   ```

4. **Verify Lambda Deployment**
   ```bash
   # List deployed functions
   aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `sentinel-prod`)].FunctionName'
   
   # Test a function
   aws lambda invoke \
     --function-name sentinel-prod-feed-parser \
     --payload '{"test": true}' \
     response.json && cat response.json
   ```

### Step 5: Post-Deployment Configuration

1. **Configure RSS Feeds**
   ```bash
   # Upload feed configuration
   aws s3 cp ../config/feeds.yaml s3://sentinel-prod-content-<suffix>/config/
   ```

2. **Test Step Functions Workflow**
   ```bash
   # Get state machine ARN
   STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
     --stack-name sentinel-prod-complete \
     --query 'Stacks[0].Outputs[?OutputKey==`IngestionStateMachineArn`].OutputValue' \
     --output text)
   
   # Start test execution
   aws stepfunctions start-execution \
     --state-machine-arn $STATE_MACHINE_ARN \
     --name "test-execution-$(date +%s)" \
     --input '{
       "feedConfigs": [
         {
           "url": "https://feeds.feedburner.com/eset/blog",
           "source": "ESET"
         }
       ],
       "batchSize": 3
     }'
   ```

3. **Set Up Monitoring**
   ```bash
   # Monitor Lambda function logs
   aws logs tail /aws/lambda/sentinel-prod-feed-parser --follow
   
   # Check Step Functions execution
   aws stepfunctions list-executions --state-machine-arn $STATE_MACHINE_ARN
   
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

## Missing Components in CloudFormation Template

**CRITICAL**: The current CloudFormation template (`sentinel-infrastructure-complete.yaml`) is missing the actual resources for Cognito, Amplify, and Bedrock AgentCore. The template only has feature flags but not the resources themselves.

### Required Additions to CloudFormation Template

You need to add these resources to `sentinel-infrastructure-complete.yaml`:

#### 1. Cognito User Pool and Client
```yaml
# Add to Resources section
CognitoUserPool:
  Type: AWS::Cognito::UserPool
  Condition: EnableAmplifyCondition
  Properties:
    UserPoolName: !Sub '${ProjectName}-${Environment}-user-pool'
    AutoVerifiedAttributes:
      - email
    Policies:
      PasswordPolicy:
        MinimumLength: 8
        RequireUppercase: true
        RequireLowercase: true
        RequireNumbers: true
        RequireSymbols: true
    Schema:
      - Name: email
        AttributeDataType: String
        Required: true
        Mutable: true

CognitoUserPoolClient:
  Type: AWS::Cognito::UserPoolClient
  Condition: EnableAmplifyCondition
  Properties:
    ClientName: !Sub '${ProjectName}-${Environment}-client'
    UserPoolId: !Ref CognitoUserPool
    GenerateSecret: false
    SupportedIdentityProviders:
      - COGNITO
    CallbackURLs:
      - https://localhost:3000/callback
    LogoutURLs:
      - https://localhost:3000/logout
    AllowedOAuthFlows:
      - code
    AllowedOAuthScopes:
      - email
      - openid
      - profile
    AllowedOAuthFlowsUserPoolClient: true

CognitoIdentityPool:
  Type: AWS::Cognito::IdentityPool
  Condition: EnableAmplifyCondition
  Properties:
    IdentityPoolName: !Sub '${ProjectName}-${Environment}-identity-pool'
    AllowUnauthenticatedIdentities: false
    CognitoIdentityProviders:
      - ClientId: !Ref CognitoUserPoolClient
        ProviderName: !GetAtt CognitoUserPool.ProviderName
```

#### 2. Amplify Application
```yaml
# Add to Resources section
AmplifyApp:
  Type: AWS::Amplify::App
  Condition: EnableAmplifyCondition
  Properties:
    Name: !Sub '${ProjectName}-${Environment}-app'
    Description: Sentinel Cybersecurity Triage Platform Web Interface
    Repository: https://github.com/your-org/sentinel-frontend
    Platform: WEB
    EnvironmentVariables:
      - Name: REACT_APP_USER_POOL_ID
        Value: !Ref CognitoUserPool
      - Name: REACT_APP_USER_POOL_CLIENT_ID
        Value: !Ref CognitoUserPoolClient
      - Name: REACT_APP_API_GATEWAY_URL
        Value: !Sub 'https://${ApiGateway}.execute-api.${AWS::Region}.amazonaws.com/prod'
    BuildSpec: |
      version: 1
      frontend:
        phases:
          preBuild:
            commands:
              - npm install
          build:
            commands:
              - npm run build
        artifacts:
          baseDirectory: build
          files:
            - '**/*'
        cache:
          paths:
            - node_modules/**/*

AmplifyBranch:
  Type: AWS::Amplify::Branch
  Condition: EnableAmplifyCondition
  Properties:
    AppId: !GetAtt AmplifyApp.AppId
    BranchName: main
    EnableAutoBuild: true
    Framework: React
```

#### 3. Bedrock AgentCore Resources
```yaml
# Add to Resources section
BedrockAgentRole:
  Type: AWS::IAM::Role
  Condition: EnableAgentsCondition
  Properties:
    RoleName: !Sub '${ProjectName}-${Environment}-bedrock-agent-role'
    AssumeRolePolicyDocument:
      Version: '2012-10-17'
      Statement:
        - Effect: Allow
          Principal:
            Service: bedrock.amazonaws.com
          Action: sts:AssumeRole
    Policies:
      - PolicyName: BedrockAgentPolicy
        PolicyDocument:
          Version: '2012-10-17'
          Statement:
            - Effect: Allow
              Action:
                - bedrock:InvokeModel
                - bedrock:InvokeModelWithResponseStream
              Resource: '*'
            - Effect: Allow
              Action:
                - lambda:InvokeFunction
              Resource: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:${ProjectName}-${Environment}-*'

IngestorAgent:
  Type: AWS::Bedrock::Agent
  Condition: EnableAgentsCondition
  Properties:
    AgentName: !Sub '${ProjectName}-${Environment}-ingestor-agent'
    Description: 'Sentinel cybersecurity news ingestor agent'
    FoundationModel: !Ref BedrockModelId
    Instruction: |
      You are a cybersecurity news ingestor agent for the Sentinel platform. 
      Your role is to process RSS feeds, evaluate article relevance, and coordinate 
      the ingestion pipeline. You have access to various tools for feed parsing, 
      relevance evaluation, deduplication, and content storage.
    AgentResourceRoleArn: !GetAtt BedrockAgentRole.Arn
    ActionGroups:
      - ActionGroupName: feed-processing
        Description: Tools for processing RSS feeds and articles
        ActionGroupExecutor:
          Lambda: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:${ProjectName}-${Environment}-feed-parser'
        ApiSchema:
          Payload: |
            {
              "openapi": "3.0.0",
              "info": {
                "title": "Feed Processing API",
                "version": "1.0.0"
              },
              "paths": {
                "/parse-feeds": {
                  "post": {
                    "description": "Parse RSS feeds and extract articles",
                    "parameters": [
                      {
                        "name": "feedConfigs",
                        "in": "query",
                        "required": true,
                        "schema": {"type": "array"}
                      }
                    ]
                  }
                }
              }
            }

AgentAlias:
  Type: AWS::Bedrock::AgentAlias
  Condition: EnableAgentsCondition
  Properties:
    AgentId: !Ref IngestorAgent
    AgentAliasName: !Sub '${Environment}-alias'
    Description: !Sub 'Agent alias for ${Environment} environment'
```

#### 4. API Gateway for Web Interface
```yaml
# Add to Resources section
ApiGateway:
  Type: AWS::ApiGateway::RestApi
  Properties:
    Name: !Sub '${ProjectName}-${Environment}-api'
    Description: Sentinel API Gateway for web interface
    EndpointConfiguration:
      Types:
        - REGIONAL

ApiGatewayAuthorizer:
  Type: AWS::ApiGateway::Authorizer
  Properties:
    Name: !Sub '${ProjectName}-${Environment}-cognito-authorizer'
    RestApiId: !Ref ApiGateway
    Type: COGNITO_USER_POOLS
    ProviderARNs:
      - !GetAtt CognitoUserPool.Arn
    IdentitySource: method.request.header.Authorization
```

### Required Outputs to Add
```yaml
# Add to Outputs section
UserPoolId:
  Description: Cognito User Pool ID
  Value: !Ref CognitoUserPool
  Condition: EnableAmplifyCondition
  Export:
    Name: !Sub '${ProjectName}-${Environment}-user-pool-id'

UserPoolClientId:
  Description: Cognito User Pool Client ID
  Value: !Ref CognitoUserPoolClient
  Condition: EnableAmplifyCondition
  Export:
    Name: !Sub '${ProjectName}-${Environment}-user-pool-client-id'

AmplifyAppId:
  Description: Amplify App ID
  Value: !GetAtt AmplifyApp.AppId
  Condition: EnableAmplifyCondition
  Export:
    Name: !Sub '${ProjectName}-${Environment}-amplify-app-id'

AmplifyAppUrl:
  Description: Amplify App URL
  Value: !Sub 'https://${AmplifyBranch.BranchName}.${AmplifyApp.DefaultDomain}'
  Condition: EnableAmplifyCondition

IngestorAgentId:
  Description: Bedrock Ingestor Agent ID
  Value: !Ref IngestorAgent
  Condition: EnableAgentsCondition
  Export:
    Name: !Sub '${ProjectName}-${Environment}-ingestor-agent-id'

ApiGatewayUrl:
  Description: API Gateway URL
  Value: !Sub 'https://${ApiGateway}.execute-api.${AWS::Region}.amazonaws.com/prod'
  Export:
    Name: !Sub '${ProjectName}-${Environment}-api-gateway-url'
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