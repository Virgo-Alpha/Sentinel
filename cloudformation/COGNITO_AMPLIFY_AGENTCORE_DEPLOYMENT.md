# Cognito, Amplify, and AgentCore Deployment Guide

This guide provides step-by-step instructions for deploying Cognito authentication, Amplify web application, and Bedrock AgentCore integration for the Sentinel platform.

## Prerequisites

1. **AWS Account Setup**
   - Bedrock model access enabled for Claude and Titan models
   - Amplify service available in your region
   - Cognito service available in your region

2. **Required Permissions**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "cognito-idp:*",
           "cognito-identity:*",
           "amplify:*",
           "bedrock:*",
           "bedrock-agent:*",
           "apigateway:*"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

3. **Git Repository**
   - Frontend code repository for Amplify deployment
   - Repository must be accessible by AWS Amplify

## Step 1: Update CloudFormation Template

**CRITICAL**: The current template is missing the actual resources. You must add them first.

### 1.1 Add Missing Resources to Template

Edit `sentinel-infrastructure-complete.yaml` and add the resources shown in the main deployment guide under "Missing Components in CloudFormation Template".

### 1.2 Validate Updated Template

```bash
# Validate the updated template
aws cloudformation validate-template \
  --template-body file://sentinel-infrastructure-complete.yaml

# Use the deployment script to validate
./deploy.sh -t complete -a validate
```

## Step 2: Deploy Infrastructure with New Components

### 2.1 Update Parameters (if needed)

Edit `parameters-prod.json` to ensure these are set correctly:

```json
{
  "ParameterKey": "EnableAgents",
  "ParameterValue": "true"
},
{
  "ParameterKey": "EnableAmplify", 
  "ParameterValue": "true"
}
```

### 2.2 Deploy Updated Stack

```bash
# Deploy the updated stack
./deploy.sh -e prod -a update

# Monitor the deployment
aws cloudformation describe-stack-events \
  --stack-name sentinel-prod-complete \
  --region us-east-1
```

## Step 3: Configure Cognito Authentication

### 3.1 Get Cognito Resources

```bash
# Get User Pool ID
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name sentinel-prod-complete \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
  --output text)

# Get User Pool Client ID  
CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name sentinel-prod-complete \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolClientId`].OutputValue' \
  --output text)

echo "User Pool ID: $USER_POOL_ID"
echo "Client ID: $CLIENT_ID"
```

### 3.2 Create Admin Users

```bash
# Create admin user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username admin \
  --user-attributes Name=email,Value=admin@company.com Name=email_verified,Value=true \
  --temporary-password TempPass123! \
  --message-action SUPPRESS

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username admin \
  --password SecurePassword123! \
  --permanent

# Create additional users as needed
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username analyst1 \
  --user-attributes Name=email,Value=analyst1@company.com Name=email_verified,Value=true \
  --temporary-password TempPass123! \
  --message-action SUPPRESS
```

### 3.3 Configure User Groups (Optional)

```bash
# Create admin group
aws cognito-idp create-group \
  --group-name Administrators \
  --user-pool-id $USER_POOL_ID \
  --description "System administrators with full access"

# Create analyst group
aws cognito-idp create-group \
  --group-name Analysts \
  --user-pool-id $USER_POOL_ID \
  --description "Security analysts with read/review access"

# Add users to groups
aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username admin \
  --group-name Administrators

aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username analyst1 \
  --group-name Analysts
```

## Step 4: Configure Amplify Web Application

### 4.1 Get Amplify App Information

```bash
# Get Amplify App ID
AMPLIFY_APP_ID=$(aws cloudformation describe-stacks \
  --stack-name sentinel-prod-complete \
  --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppId`].OutputValue' \
  --output text)

# Get Amplify App URL
AMPLIFY_URL=$(aws cloudformation describe-stacks \
  --stack-name sentinel-prod-complete \
  --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppUrl`].OutputValue' \
  --output text)

echo "Amplify App ID: $AMPLIFY_APP_ID"
echo "Amplify URL: $AMPLIFY_URL"
```

### 4.2 Connect Git Repository

```bash
# If you need to connect a different repository
aws amplify update-app \
  --app-id $AMPLIFY_APP_ID \
  --repository https://github.com/your-org/sentinel-frontend \
  --access-token YOUR_GITHUB_TOKEN

# Create and configure main branch
aws amplify create-branch \
  --app-id $AMPLIFY_APP_ID \
  --branch-name main \
  --framework React \
  --enable-auto-build
```

### 4.3 Configure Environment Variables

```bash
# Set environment variables for the frontend
aws amplify put-backend-environment \
  --app-id $AMPLIFY_APP_ID \
  --environment-name production \
  --deployment-artifacts sentinel-prod-deployment

# Update app with environment variables
aws amplify update-app \
  --app-id $AMPLIFY_APP_ID \
  --environment-variables \
    REACT_APP_USER_POOL_ID=$USER_POOL_ID \
    REACT_APP_USER_POOL_CLIENT_ID=$CLIENT_ID \
    REACT_APP_API_GATEWAY_URL=https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/prod \
    REACT_APP_AWS_REGION=us-east-1
```

### 4.4 Deploy Frontend Application

```bash
# Start deployment
aws amplify start-job \
  --app-id $AMPLIFY_APP_ID \
  --branch-name main \
  --job-type RELEASE

# Monitor deployment status
aws amplify get-job \
  --app-id $AMPLIFY_APP_ID \
  --branch-name main \
  --job-id $(aws amplify list-jobs --app-id $AMPLIFY_APP_ID --branch-name main --query 'jobSummaries[0].jobId' --output text)
```

## Step 5: Configure Bedrock AgentCore

### 5.1 Get Agent Information

```bash
# Get Agent ID
AGENT_ID=$(aws cloudformation describe-stacks \
  --stack-name sentinel-prod-complete \
  --query 'Stacks[0].Outputs[?OutputKey==`IngestorAgentId`].OutputValue' \
  --output text)

echo "Agent ID: $AGENT_ID"
```

### 5.2 Prepare and Test Agent

```bash
# Prepare the agent (makes it ready for invocation)
aws bedrock-agent prepare-agent \
  --agent-id $AGENT_ID

# Get agent details
aws bedrock-agent get-agent \
  --agent-id $AGENT_ID

# List agent aliases
aws bedrock-agent list-agent-aliases \
  --agent-id $AGENT_ID
```

### 5.3 Create Production Alias

```bash
# Create production alias
aws bedrock-agent create-agent-alias \
  --agent-id $AGENT_ID \
  --agent-alias-name production \
  --description "Production alias for Sentinel ingestor agent"

# Get alias details
ALIAS_ID=$(aws bedrock-agent list-agent-aliases \
  --agent-id $AGENT_ID \
  --query 'agentAliasSummaries[?agentAliasName==`production`].agentAliasId' \
  --output text)

echo "Production Alias ID: $ALIAS_ID"
```

### 5.4 Test Agent Invocation

```bash
# Test agent invocation
aws bedrock-agent-runtime invoke-agent \
  --agent-id $AGENT_ID \
  --agent-alias-id $ALIAS_ID \
  --session-id test-session-$(date +%s) \
  --input-text "Parse the latest cybersecurity feeds and evaluate article relevance" \
  --output-file agent-response.json

# Check response
cat agent-response.json
```

## Step 6: Configure API Gateway Integration

### 6.1 Get API Gateway Information

```bash
# Get API Gateway URL
API_GATEWAY_URL=$(aws cloudformation describe-stacks \
  --stack-name sentinel-prod-complete \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
  --output text)

echo "API Gateway URL: $API_GATEWAY_URL"
```

### 6.2 Test API Gateway with Cognito

```bash
# Get Cognito token for testing
# First, authenticate a user to get tokens
aws cognito-idp admin-initiate-auth \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=admin,PASSWORD=SecurePassword123! \
  --output json > auth-response.json

# Extract access token
ACCESS_TOKEN=$(cat auth-response.json | jq -r '.AuthenticationResult.AccessToken')

# Test API call with authentication
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     "$API_GATEWAY_URL/articles"
```

## Step 7: Verification and Testing

### 7.1 Verify Cognito Setup

```bash
# List users
aws cognito-idp list-users --user-pool-id $USER_POOL_ID

# List groups
aws cognito-idp list-groups --user-pool-id $USER_POOL_ID

# Test user authentication
aws cognito-idp admin-initiate-auth \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=admin,PASSWORD=SecurePassword123!
```

### 7.2 Verify Amplify Deployment

```bash
# Check app status
aws amplify get-app --app-id $AMPLIFY_APP_ID

# Check branch status
aws amplify get-branch --app-id $AMPLIFY_APP_ID --branch-name main

# Check recent deployments
aws amplify list-jobs --app-id $AMPLIFY_APP_ID --branch-name main
```

### 7.3 Verify Agent Functionality

```bash
# Check agent status
aws bedrock-agent get-agent --agent-id $AGENT_ID

# List action groups
aws bedrock-agent list-agent-action-groups --agent-id $AGENT_ID

# Test agent with different inputs
aws bedrock-agent-runtime invoke-agent \
  --agent-id $AGENT_ID \
  --agent-alias-id $ALIAS_ID \
  --session-id verification-session \
  --input-text "What cybersecurity feeds are you configured to process?" \
  --output-file verification-response.json
```

## Step 8: Frontend Configuration

### 8.1 Update Frontend Configuration

Create or update your frontend configuration file (e.g., `src/config/aws-config.js`):

```javascript
const awsConfig = {
  Auth: {
    region: 'us-east-1',
    userPoolId: process.env.REACT_APP_USER_POOL_ID,
    userPoolWebClientId: process.env.REACT_APP_USER_POOL_CLIENT_ID,
    mandatorySignIn: true,
    authenticationFlowType: 'USER_SRP_AUTH'
  },
  API: {
    endpoints: [
      {
        name: 'SentinelAPI',
        endpoint: process.env.REACT_APP_API_GATEWAY_URL,
        region: 'us-east-1'
      }
    ]
  }
};

export default awsConfig;
```

### 8.2 Update Amplify Build Settings

```bash
# Update build specification
aws amplify update-app \
  --app-id $AMPLIFY_APP_ID \
  --build-spec '{
    "version": 1,
    "frontend": {
      "phases": {
        "preBuild": {
          "commands": [
            "npm install"
          ]
        },
        "build": {
          "commands": [
            "npm run build"
          ]
        }
      },
      "artifacts": {
        "baseDirectory": "build",
        "files": [
          "**/*"
        ]
      },
      "cache": {
        "paths": [
          "node_modules/**/*"
        ]
      }
    }
  }'
```

## Troubleshooting

### Common Issues

1. **Cognito User Pool Not Found**
   ```bash
   # Check if the stack was deployed with EnableAmplify=true
   aws cloudformation describe-stacks \
     --stack-name sentinel-prod-complete \
     --query 'Stacks[0].Parameters[?ParameterKey==`EnableAmplify`].ParameterValue'
   ```

2. **Amplify App Not Deploying**
   ```bash
   # Check build logs
   aws amplify get-job \
     --app-id $AMPLIFY_APP_ID \
     --branch-name main \
     --job-id LATEST_JOB_ID
   ```

3. **Agent Not Responding**
   ```bash
   # Check agent preparation status
   aws bedrock-agent get-agent --agent-id $AGENT_ID \
     --query 'agent.agentStatus'
   
   # Re-prepare if needed
   aws bedrock-agent prepare-agent --agent-id $AGENT_ID
   ```

4. **API Gateway Authentication Failing**
   ```bash
   # Verify authorizer configuration
   aws apigateway get-authorizers \
     --rest-api-id YOUR_API_ID
   ```

### Useful Commands

```bash
# Get all stack outputs
aws cloudformation describe-stacks \
  --stack-name sentinel-prod-complete \
  --query 'Stacks[0].Outputs'

# Monitor CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name sentinel-prod-complete \
  --max-items 20

# Check resource status
aws cloudformation list-stack-resources \
  --stack-name sentinel-prod-complete
```

## Security Considerations

1. **Cognito Security**
   - Enable MFA for admin users
   - Configure password policies
   - Set up account recovery options

2. **Amplify Security**
   - Configure custom domain with SSL
   - Set up proper CORS policies
   - Enable access logging

3. **Agent Security**
   - Limit agent permissions to minimum required
   - Monitor agent invocations
   - Set up cost controls

## Next Steps

After successful deployment:

1. **Configure Monitoring**
   - Set up CloudWatch alarms for authentication failures
   - Monitor Amplify deployment status
   - Track agent invocation metrics

2. **Set Up CI/CD**
   - Configure automatic deployments from Git
   - Set up staging environments
   - Implement proper testing pipelines

3. **User Management**
   - Create user onboarding process
   - Set up role-based access control
   - Configure user lifecycle management

This completes the deployment of Cognito, Amplify, and AgentCore components for the Sentinel platform.