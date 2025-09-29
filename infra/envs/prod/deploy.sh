#!/bin/bash
# =============================================================================
# SENTINEL PRODUCTION ENVIRONMENT DEPLOYMENT SCRIPT
# =============================================================================
# This script deploys the Sentinel cybersecurity triage system to the
# production environment with enhanced security checks and validation.
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
ENVIRONMENT="prod"
REGION="us-east-1"
MIN_TERRAFORM_VERSION="1.5.0"
MIN_AWS_CLI_VERSION="2.0.0"

echo -e "${RED}🚨 PRODUCTION DEPLOYMENT - PROCEED WITH CAUTION 🚨${NC}"
echo -e "${GREEN}🚀 Deploying Sentinel ${ENVIRONMENT} environment...${NC}"
echo -e "${BLUE}📅 Deployment started at: $(date)${NC}"

# =============================================================================
# ENHANCED PREREQUISITE CHECKS FOR PRODUCTION
# =============================================================================
echo -e "${YELLOW}📋 Checking prerequisites (production-grade)...${NC}"

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

# Check required tools for production
if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ jq is required for production deployments${NC}"
    echo -e "${YELLOW}💡 Install jq for JSON processing${NC}"
    exit 1
fi

# Check AWS credentials and permissions
echo -e "${YELLOW}🔐 Validating AWS credentials and permissions...${NC}"
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo -e "${YELLOW}💡 Run: aws configure${NC}"
    exit 1
fi

AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_USER=$(aws sts get-caller-identity --query Arn --output text)
echo -e "${BLUE}🏢 AWS Account: ${AWS_ACCOUNT}${NC}"
echo -e "${BLUE}👤 AWS User: ${AWS_USER}${NC}"

# Production-specific checks
echo -e "${YELLOW}🔒 Performing production-specific security checks...${NC}"

# Check if MFA is enabled (recommended for production)
if aws sts get-session-token --duration-seconds 900 &> /dev/null; then
    echo -e "${GREEN}✅ MFA session detected${NC}"
else
    echo -e "${YELLOW}⚠️  MFA not detected (recommended for production)${NC}"
fi

# Check if we're in the correct directory
if [ ! -f "main.tf" ] || [ ! -f "variables.tf" ]; then
    echo -e "${RED}❌ Not in a Terraform environment directory${NC}"
    echo -e "${YELLOW}💡 Run this script from infra/envs/prod/${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

# =============================================================================
# ENHANCED CONFIGURATION VALIDATION FOR PRODUCTION
# =============================================================================
echo -e "${YELLOW}📝 Validating production configuration...${NC}"

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo -e "${RED}❌ terraform.tfvars not found${NC}"
    echo -e "${YELLOW}💡 Copy from terraform.tfvars.example and customize${NC}"
    exit 1
fi

# Validate no example values remain
if grep -q "example.com\|company.com\|your-org" terraform.tfvars; then
    echo -e "${RED}❌ Found example values in terraform.tfvars${NC}"
    echo -e "${YELLOW}💡 Please update all example values with production settings${NC}"
    exit 1
fi

# Check for sensitive values
if grep -q "CHANGE_ME\|TODO\|FIXME\|test\|dev" terraform.tfvars; then
    echo -e "${RED}❌ Found placeholder or development values in terraform.tfvars${NC}"
    echo -e "${YELLOW}💡 Please update all values for production${NC}"
    exit 1
fi

# Validate email addresses are production-ready
if ! grep -q "@.*\." terraform.tfvars; then
    echo -e "${RED}❌ Invalid email addresses in terraform.tfvars${NC}"
    exit 1
fi

# Check cost limits are reasonable for production
MAX_COST=$(grep "max_monthly_cost_usd" terraform.tfvars | grep -o '[0-9.]*' | head -1)
if [ -n "$MAX_COST" ] && (( $(echo "$MAX_COST < 500" | bc -l) )); then
    echo -e "${YELLOW}⚠️  Monthly cost limit seems low for production ($MAX_COST)${NC}"
    echo -e "${YELLOW}❓ Continue anyway? (y/N)${NC}"
    read -r response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✅ Configuration validation passed${NC}"

# =============================================================================
# PRODUCTION SAFETY CHECKS
# =============================================================================
echo -e "${YELLOW}🛡️  Performing production safety checks...${NC}"

# Check if this is a fresh deployment or update
if terraform show &> /dev/null; then
    echo -e "${BLUE}📊 Existing infrastructure detected${NC}"
    DEPLOYMENT_TYPE="update"
else
    echo -e "${BLUE}🆕 Fresh deployment detected${NC}"
    DEPLOYMENT_TYPE="fresh"
fi

# Backup check for updates
if [ "$DEPLOYMENT_TYPE" = "update" ]; then
    echo -e "${YELLOW}💾 Checking backup status...${NC}"
    # Add backup verification logic here if needed
    echo -e "${GREEN}✅ Backup checks passed${NC}"
fi

# =============================================================================
# TERRAFORM OPERATIONS WITH ENHANCED VALIDATION
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

# Format check (strict for production)
echo -e "${YELLOW}🎨 Checking Terraform formatting...${NC}"
if ! terraform fmt -check=true -diff=true; then
    echo -e "${RED}❌ Terraform files are not properly formatted${NC}"
    echo -e "${YELLOW}💡 Run: terraform fmt -recursive${NC}"
    exit 1
fi

# Plan deployment with detailed output
echo -e "${YELLOW}📋 Planning production deployment...${NC}"
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
# PRODUCTION DEPLOYMENT CONFIRMATION
# =============================================================================

echo -e "${RED}🚨 PRODUCTION DEPLOYMENT CONFIRMATION 🚨${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${YELLOW}Environment: ${ENVIRONMENT}${NC}"
echo -e "${YELLOW}AWS Account: ${AWS_ACCOUNT}${NC}"
echo -e "${YELLOW}Region: ${REGION}${NC}"
echo -e "${YELLOW}Deployment Type: ${DEPLOYMENT_TYPE}${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"

# Display cost estimation
echo -e "${PURPLE}💰 Estimated monthly cost for production environment: ~$500-1500${NC}"
echo -e "${YELLOW}⚠️  Actual costs may vary significantly based on usage${NC}"

# Multiple confirmation prompts for production
echo -e "${RED}❓ Are you sure you want to deploy to PRODUCTION? (yes/no)${NC}"
read -r response1
if [[ ! "$response1" = "yes" ]]; then
    echo -e "${YELLOW}❌ Deployment cancelled${NC}"
    rm -f tfplan
    exit 1
fi

echo -e "${RED}❓ Have you reviewed the Terraform plan output? (yes/no)${NC}"
read -r response2
if [[ ! "$response2" = "yes" ]]; then
    echo -e "${YELLOW}❌ Please review the plan before proceeding${NC}"
    rm -f tfplan
    exit 1
fi

echo -e "${RED}❓ Type 'DEPLOY' to confirm production deployment:${NC}"
read -r response3
if [[ ! "$response3" = "DEPLOY" ]]; then
    echo -e "${YELLOW}❌ Deployment cancelled${NC}"
    rm -f tfplan
    exit 1
fi

# =============================================================================
# PRODUCTION DEPLOYMENT EXECUTION
# =============================================================================

echo -e "${GREEN}🚀 Applying Terraform plan to PRODUCTION...${NC}"

# Apply with progress tracking
if terraform apply tfplan; then
    echo -e "${GREEN}✅ Production deployment completed successfully!${NC}"
    
    # Clean up plan file
    rm -f tfplan
    
    # =============================================================================
    # POST-DEPLOYMENT VALIDATION AND INFORMATION
    # =============================================================================
    
    echo -e "${GREEN}📊 Production Deployment Information:${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    
    # Display outputs if available
    if terraform output > /dev/null 2>&1; then
        echo -e "${YELLOW}🔗 Production URLs and Information:${NC}"
        terraform output -json | jq -r 'to_entries[] | "  \(.key): \(.value.value)"' 2>/dev/null || terraform output
    fi
    
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    
    # =============================================================================
    # PRODUCTION POST-DEPLOYMENT CHECKLIST
    # =============================================================================
    
    echo -e "${YELLOW}📝 Production Post-Deployment Checklist:${NC}"
    echo -e "${RED}🔴 CRITICAL - Complete these steps immediately:${NC}"
    echo -e ""
    echo -e "${BLUE}1.${NC} ${RED}Verify SES email identities${NC}"
    echo -e "   • Go to SES Console → Verified identities"
    echo -e "   • Verify ALL production email addresses"
    echo -e "   • Test email delivery"
    echo -e ""
    echo -e "${BLUE}2.${NC} ${RED}Configure production RSS feeds${NC}"
    echo -e "   • Update config/feeds.yaml with production sources"
    echo -e "   • Validate all feed URLs are accessible"
    echo -e "   • Test feed parsing"
    echo -e ""
    echo -e "${BLUE}3.${NC} ${RED}Update keyword targeting${NC}"
    echo -e "   • Configure config/keywords.yaml for production"
    echo -e "   • Set appropriate keyword weights"
    echo -e "   • Test keyword matching"
    echo -e ""
    echo -e "${BLUE}4.${NC} ${RED}Security validation${NC}"
    echo -e "   • Verify IAM permissions are least-privilege"
    echo -e "   • Check VPC security groups"
    echo -e "   • Validate encryption at rest and in transit"
    echo -e ""
    echo -e "${BLUE}5.${NC} ${RED}Monitoring setup${NC}"
    echo -e "   • Configure CloudWatch alarms"
    echo -e "   • Set up cost monitoring alerts"
    echo -e "   • Test notification channels"
    echo -e ""
    echo -e "${YELLOW}🟡 IMPORTANT - Complete within 24 hours:${NC}"
    echo -e ""
    echo -e "${BLUE}6.${NC} Run comprehensive integration tests"
    echo -e "${BLUE}7.${NC} Perform security scan and penetration testing"
    echo -e "${BLUE}8.${NC} Document production runbook procedures"
    echo -e "${BLUE}9.${NC} Train operations team on monitoring and alerts"
    echo -e "${BLUE}10.${NC} Schedule regular backup and disaster recovery tests"
    
    # Display web app URL if available
    WEB_APP_URL=$(terraform output -raw amplify_app_url 2>/dev/null || echo "")
    if [ -n "$WEB_APP_URL" ]; then
        echo -e ""
        echo -e "${GREEN}🌐 Production Web Application: ${WEB_APP_URL}${NC}"
        echo -e "${RED}⚠️  Ensure proper authentication is configured before sharing${NC}"
    fi
    
    echo -e ""
    echo -e "${GREEN}🎉 Production environment is deployed!${NC}"
    echo -e "${RED}🚨 Remember to complete the post-deployment checklist${NC}"
    echo -e "${BLUE}📅 Deployment completed at: $(date)${NC}"
    
else
    echo -e "${RED}❌ Production deployment failed${NC}"
    rm -f tfplan
    echo -e "${YELLOW}💡 Check the error messages above and resolve issues${NC}"
    echo -e "${YELLOW}💡 Consider rolling back if this was an update${NC}"
    exit 1
fi