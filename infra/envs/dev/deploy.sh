#!/bin/bash
# =============================================================================
# SENTINEL DEVELOPMENT ENVIRONMENT DEPLOYMENT SCRIPT
# =============================================================================
# This script deploys the Sentinel cybersecurity triage system to the
# development environment with comprehensive validation and safety checks.
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="dev"
REGION="us-east-1"
MIN_TERRAFORM_VERSION="1.5.0"
MIN_AWS_CLI_VERSION="2.0.0"

echo -e "${GREEN}🚀 Deploying Sentinel ${ENVIRONMENT} environment...${NC}"
echo -e "${BLUE}📅 Deployment started at: $(date)${NC}"

# =============================================================================
# PREREQUISITE CHECKS
# =============================================================================
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

# Check Terraform installation and version
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}❌ Terraform is not installed${NC}"
    echo -e "${YELLOW}💡 Install from: https://www.terraform.io/downloads${NC}"
    exit 1
fi

TERRAFORM_VERSION=$(terraform version -json | jq -r '.terraform_version')
echo -e "${BLUE}📦 Terraform version: ${TERRAFORM_VERSION}${NC}"

# Check AWS CLI installation and version
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed${NC}"
    echo -e "${YELLOW}💡 Install from: https://aws.amazon.com/cli/${NC}"
    exit 1
fi

AWS_CLI_VERSION=$(aws --version | cut -d/ -f2 | cut -d' ' -f1)
echo -e "${BLUE}📦 AWS CLI version: ${AWS_CLI_VERSION}${NC}"

# Check jq for JSON processing
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠️  jq is not installed (recommended for output processing)${NC}"
fi

# Check AWS credentials and permissions
echo -e "${YELLOW}🔐 Validating AWS credentials...${NC}"
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo -e "${YELLOW}💡 Run: aws configure${NC}"
    exit 1
fi

AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_USER=$(aws sts get-caller-identity --query Arn --output text)
echo -e "${BLUE}🏢 AWS Account: ${AWS_ACCOUNT}${NC}"
echo -e "${BLUE}👤 AWS User: ${AWS_USER}${NC}"

# Check if we're in the correct directory
if [ ! -f "main.tf" ] || [ ! -f "variables.tf" ]; then
    echo -e "${RED}❌ Not in a Terraform environment directory${NC}"
    echo -e "${YELLOW}💡 Run this script from infra/envs/dev/${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

# =============================================================================
# CONFIGURATION VALIDATION
# =============================================================================
echo -e "${YELLOW}📝 Validating configuration...${NC}"

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo -e "${YELLOW}⚠️  terraform.tfvars not found. Creating from example...${NC}"
    cp terraform.tfvars.example terraform.tfvars
    echo -e "${RED}❌ Please edit terraform.tfvars with your configuration before proceeding${NC}"
    echo -e "${YELLOW}📝 Required changes:${NC}"
    echo -e "   • Update email addresses"
    echo -e "   • Set domain name"
    echo -e "   • Configure Amplify repository URL (if using)"
    echo -e "   • Review cost limits and thresholds"
    exit 1
fi

# Validate required email configuration
if grep -q "example.com" terraform.tfvars; then
    echo -e "${YELLOW}⚠️  Found example.com in terraform.tfvars${NC}"
    echo -e "${RED}❌ Please update email addresses in terraform.tfvars${NC}"
    exit 1
fi

# Check for sensitive values
if grep -q "CHANGE_ME\|TODO\|FIXME" terraform.tfvars; then
    echo -e "${RED}❌ Found placeholder values in terraform.tfvars${NC}"
    echo -e "${YELLOW}💡 Please update all placeholder values${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Configuration validation passed${NC}"

# =============================================================================
# TERRAFORM OPERATIONS
# =============================================================================

# Initialize Terraform
echo -e "${YELLOW}🔧 Initializing Terraform...${NC}"
if ! terraform init -backend-config=backend.hcl; then
    echo -e "${RED}❌ Terraform initialization failed${NC}"
    exit 1
fi

# Validate configuration
echo -e "${YELLOW}✅ Validating Terraform configuration...${NC}"
if ! terraform validate; then
    echo -e "${RED}❌ Terraform validation failed${NC}"
    exit 1
fi

# Format check
echo -e "${YELLOW}🎨 Checking Terraform formatting...${NC}"
if ! terraform fmt -check=true -diff=true; then
    echo -e "${YELLOW}⚠️  Terraform files are not properly formatted${NC}"
    echo -e "${YELLOW}💡 Run: terraform fmt -recursive${NC}"
fi

# Plan deployment
echo -e "${YELLOW}📋 Planning deployment...${NC}"
if ! terraform plan -out=tfplan -detailed-exitcode; then
    PLAN_EXIT_CODE=$?
    if [ $PLAN_EXIT_CODE -eq 1 ]; then
        echo -e "${RED}❌ Terraform plan failed${NC}"
        exit 1
    elif [ $PLAN_EXIT_CODE -eq 2 ]; then
        echo -e "${BLUE}📊 Changes detected in plan${NC}"
    else
        echo -e "${GREEN}✅ No changes needed${NC}"
        exit 0
    fi
fi

# =============================================================================
# DEPLOYMENT CONFIRMATION AND EXECUTION
# =============================================================================

# Display cost estimation (if available)
echo -e "${PURPLE}💰 Estimated monthly cost for development environment: ~$50-100${NC}"
echo -e "${YELLOW}⚠️  Actual costs may vary based on usage${NC}"

# Ask for confirmation
echo -e "${YELLOW}❓ Do you want to apply this plan? (y/N)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "${GREEN}🚀 Applying Terraform plan...${NC}"
    
    # Apply with progress tracking
    if terraform apply tfplan; then
        echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
        
        # Clean up plan file
        rm -f tfplan
        
        # =============================================================================
        # POST-DEPLOYMENT INFORMATION
        # =============================================================================
        
        echo -e "${GREEN}📊 Deployment Information:${NC}"
        echo -e "${BLUE}════════════════════════════════════════${NC}"
        
        # Display outputs if available
        if terraform output > /dev/null 2>&1; then
            echo -e "${YELLOW}🔗 Important URLs and Information:${NC}"
            terraform output -json | jq -r 'to_entries[] | "  \(.key): \(.value.value)"' 2>/dev/null || terraform output
        fi
        
        echo -e "${BLUE}════════════════════════════════════════${NC}"
        
        # =============================================================================
        # NEXT STEPS
        # =============================================================================
        
        echo -e "${YELLOW}📝 Next Steps:${NC}"
        echo -e "${BLUE}1.${NC} Verify SES email identities in AWS Console"
        echo -e "   • Go to SES Console → Verified identities"
        echo -e "   • Verify all email addresses from terraform.tfvars"
        echo -e ""
        echo -e "${BLUE}2.${NC} Configure RSS feeds"
        echo -e "   • Edit config/feeds.yaml with your RSS sources"
        echo -e "   • Test feed parsing with sample data"
        echo -e ""
        echo -e "${BLUE}3.${NC} Update keyword targeting"
        echo -e "   • Edit config/keywords.yaml with your target technologies"
        echo -e "   • Configure keyword weights and categories"
        echo -e ""
        echo -e "${BLUE}4.${NC} Test the deployment"
        echo -e "   • Run integration tests"
        echo -e "   • Verify Lambda functions are working"
        echo -e "   • Check CloudWatch logs for errors"
        echo -e ""
        echo -e "${BLUE}5.${NC} Access monitoring"
        echo -e "   • CloudWatch Dashboard: AWS Console → CloudWatch"
        echo -e "   • X-Ray Traces: AWS Console → X-Ray"
        echo -e "   • Cost Monitoring: AWS Console → Cost Explorer"
        
        # Display web app URL if available
        WEB_APP_URL=$(terraform output -raw amplify_app_url 2>/dev/null || echo "")
        if [ -n "$WEB_APP_URL" ]; then
            echo -e ""
            echo -e "${GREEN}🌐 Web Application: ${WEB_APP_URL}${NC}"
        fi
        
        echo -e ""
        echo -e "${GREEN}🎉 Development environment is ready!${NC}"
        echo -e "${BLUE}📅 Deployment completed at: $(date)${NC}"
        
    else
        echo -e "${RED}❌ Deployment failed${NC}"
        rm -f tfplan
        exit 1
    fi
    
else
    echo -e "${YELLOW}❌ Deployment cancelled${NC}"
    rm -f tfplan
    echo -e "${BLUE}💡 Plan file removed. Run script again when ready to deploy.${NC}"
fi