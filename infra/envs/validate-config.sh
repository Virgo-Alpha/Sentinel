#!/bin/bash
# =============================================================================
# SENTINEL ENVIRONMENT CONFIGURATION VALIDATOR
# =============================================================================
# This script validates Terraform configurations for both dev and prod
# environments, checking for common issues and security best practices.
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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}🔍 Sentinel Configuration Validator${NC}"
echo -e "${BLUE}═══════════════════════════════════${NC}"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

validate_email() {
    local email="$1"
    if [[ "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        return 0
    else
        return 1
    fi
}

validate_url() {
    local url="$1"
    if [[ "$url" =~ ^https?://[a-zA-Z0-9.-]+.*$ ]]; then
        return 0
    else
        return 1
    fi
}

check_terraform_file() {
    local file="$1"
    local env="$2"
    
    echo -e "${YELLOW}📄 Validating ${file} for ${env}...${NC}"
    
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ File not found: ${file}${NC}"
        return 1
    fi
    
    # Check for syntax errors
    if ! terraform fmt -check=true "$file" &> /dev/null; then
        echo -e "${YELLOW}⚠️  File not properly formatted: ${file}${NC}"
    fi
    
    return 0
}

validate_environment() {
    local env="$1"
    local env_dir="${SCRIPT_DIR}/${env}"
    local errors=0
    
    echo -e "${BLUE}🔍 Validating ${env} environment...${NC}"
    echo -e "${BLUE}═══════════════════════════════════${NC}"
    
    # Check if environment directory exists
    if [ ! -d "$env_dir" ]; then
        echo -e "${RED}❌ Environment directory not found: ${env_dir}${NC}"
        return 1
    fi
    
    cd "$env_dir"
    
    # =============================================================================
    # FILE EXISTENCE CHECKS
    # =============================================================================
    echo -e "${YELLOW}📋 Checking required files...${NC}"
    
    required_files=("main.tf" "variables.tf" "outputs.tf" "backend.hcl" "terraform.tfvars.example")
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            echo -e "${RED}❌ Missing required file: ${file}${NC}"
            ((errors++))
        else
            echo -e "${GREEN}✅ Found: ${file}${NC}"
        fi
    done
    
    # =============================================================================
    # TERRAFORM CONFIGURATION VALIDATION
    # =============================================================================
    echo -e "${YELLOW}🔧 Validating Terraform configuration...${NC}"
    
    if [ -f "terraform.tfvars" ]; then
        # Validate terraform.tfvars
        echo -e "${YELLOW}📝 Checking terraform.tfvars...${NC}"
        
        # Check for example values
        if grep -q "example.com\|company.com\|your-org" terraform.tfvars; then
            echo -e "${YELLOW}⚠️  Found example values in terraform.tfvars${NC}"
            if [ "$env" = "prod" ]; then
                echo -e "${RED}❌ Production environment cannot use example values${NC}"
                ((errors++))
            fi
        fi
        
        # Check for placeholder values
        if grep -q "CHANGE_ME\|TODO\|FIXME" terraform.tfvars; then
            echo -e "${RED}❌ Found placeholder values in terraform.tfvars${NC}"
            ((errors++))
        fi
        
        # Validate email addresses
        echo -e "${YELLOW}📧 Validating email addresses...${NC}"
        while IFS= read -r line; do
            if [[ "$line" =~ ^[[:space:]]*[a-zA-Z_]+.*=.*\"([^\"]+@[^\"]+)\" ]]; then
                email="${BASH_REMATCH[1]}"
                if validate_email "$email"; then
                    echo -e "${GREEN}✅ Valid email: ${email}${NC}"
                else
                    echo -e "${RED}❌ Invalid email: ${email}${NC}"
                    ((errors++))
                fi
            fi
        done < terraform.tfvars
        
        # Check cost limits
        echo -e "${YELLOW}💰 Validating cost controls...${NC}"
        max_cost=$(grep "max_monthly_cost_usd" terraform.tfvars | grep -o '[0-9.]*' | head -1)
        if [ -n "$max_cost" ]; then
            echo -e "${BLUE}💵 Monthly cost limit: \$${max_cost}${NC}"
            if [ "$env" = "dev" ] && (( $(echo "$max_cost > 200" | bc -l) )); then
                echo -e "${YELLOW}⚠️  High cost limit for development environment${NC}"
            elif [ "$env" = "prod" ] && (( $(echo "$max_cost < 500" | bc -l) )); then
                echo -e "${YELLOW}⚠️  Low cost limit for production environment${NC}"
            fi
        fi
        
        # Check thresholds
        echo -e "${YELLOW}🎯 Validating thresholds...${NC}"
        relevance_threshold=$(grep "relevance_threshold" terraform.tfvars | grep -o '[0-9.]*' | head -1)
        if [ -n "$relevance_threshold" ]; then
            if (( $(echo "$relevance_threshold < 0.0 || $relevance_threshold > 1.0" | bc -l) )); then
                echo -e "${RED}❌ Invalid relevance threshold: ${relevance_threshold}${NC}"
                ((errors++))
            else
                echo -e "${GREEN}✅ Relevance threshold: ${relevance_threshold}${NC}"
            fi
        fi
        
    else
        echo -e "${YELLOW}⚠️  terraform.tfvars not found (will use defaults)${NC}"
    fi
    
    # =============================================================================
    # TERRAFORM SYNTAX VALIDATION
    # =============================================================================
    if command -v terraform &> /dev/null; then
        echo -e "${YELLOW}🔍 Running Terraform validation...${NC}"
        
        # Initialize if needed (without backend)
        if [ ! -d ".terraform" ]; then
            if terraform init -backend=false &> /dev/null; then
                echo -e "${GREEN}✅ Terraform initialization successful${NC}"
            else
                echo -e "${RED}❌ Terraform initialization failed${NC}"
                ((errors++))
            fi
        fi
        
        # Validate syntax
        if terraform validate &> /dev/null; then
            echo -e "${GREEN}✅ Terraform validation passed${NC}"
        else
            echo -e "${RED}❌ Terraform validation failed${NC}"
            terraform validate
            ((errors++))
        fi
        
        # Check formatting
        if terraform fmt -check=true &> /dev/null; then
            echo -e "${GREEN}✅ Terraform formatting is correct${NC}"
        else
            echo -e "${YELLOW}⚠️  Terraform files need formatting${NC}"
            echo -e "${BLUE}💡 Run: terraform fmt -recursive${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Terraform not installed, skipping syntax validation${NC}"
    fi
    
    # =============================================================================
    # SECURITY CHECKS
    # =============================================================================
    echo -e "${YELLOW}🔒 Performing security checks...${NC}"
    
    # Check for hardcoded secrets
    if grep -r "password\|secret\|key" . --include="*.tf" --include="*.tfvars" | grep -v "variable\|description"; then
        echo -e "${RED}❌ Potential hardcoded secrets found${NC}"
        ((errors++))
    else
        echo -e "${GREEN}✅ No hardcoded secrets detected${NC}"
    fi
    
    # Check for public access
    if grep -r "0.0.0.0/0\|::/0" . --include="*.tf"; then
        echo -e "${YELLOW}⚠️  Found potential public access configurations${NC}"
        if [ "$env" = "prod" ]; then
            echo -e "${RED}❌ Review public access in production${NC}"
            ((errors++))
        fi
    else
        echo -e "${GREEN}✅ No obvious public access configurations${NC}"
    fi
    
    # =============================================================================
    # ENVIRONMENT-SPECIFIC CHECKS
    # =============================================================================
    if [ "$env" = "prod" ]; then
        echo -e "${YELLOW}🏭 Production-specific checks...${NC}"
        
        # Check for development-specific values
        if grep -q "dev\|test\|localhost" terraform.tfvars 2>/dev/null; then
            echo -e "${RED}❌ Found development values in production config${NC}"
            ((errors++))
        fi
        
        # Check backup configuration
        if grep -q "backup.*required\|Backup.*Required" terraform.tfvars 2>/dev/null; then
            echo -e "${GREEN}✅ Backup configuration found${NC}"
        else
            echo -e "${YELLOW}⚠️  Backup configuration not explicitly set${NC}"
        fi
        
    elif [ "$env" = "dev" ]; then
        echo -e "${YELLOW}🧪 Development-specific checks...${NC}"
        
        # Check for auto-shutdown tags
        if grep -q "AutoShutdown.*true" terraform.tfvars 2>/dev/null; then
            echo -e "${GREEN}✅ Auto-shutdown configured for cost savings${NC}"
        else
            echo -e "${YELLOW}⚠️  Consider adding AutoShutdown tag for cost savings${NC}"
        fi
    fi
    
    # =============================================================================
    # SUMMARY
    # =============================================================================
    echo -e "${BLUE}═══════════════════════════════════${NC}"
    if [ $errors -eq 0 ]; then
        echo -e "${GREEN}✅ ${env} environment validation passed!${NC}"
    else
        echo -e "${RED}❌ ${env} environment validation failed with ${errors} error(s)${NC}"
    fi
    echo -e "${BLUE}═══════════════════════════════════${NC}"
    
    return $errors
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

total_errors=0

# Check command line arguments
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}🔍 Validating all environments...${NC}"
    environments=("dev" "prod")
else
    environments=("$@")
fi

# Validate each environment
for env in "${environments[@]}"; do
    echo ""
    validate_environment "$env"
    env_errors=$?
    total_errors=$((total_errors + env_errors))
    echo ""
done

# =============================================================================
# FINAL SUMMARY
# =============================================================================
echo -e "${BLUE}🏁 Final Validation Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════${NC}"

if [ $total_errors -eq 0 ]; then
    echo -e "${GREEN}🎉 All environment validations passed!${NC}"
    echo -e "${GREEN}✅ Configurations are ready for deployment${NC}"
    exit 0
else
    echo -e "${RED}❌ Validation failed with ${total_errors} total error(s)${NC}"
    echo -e "${YELLOW}💡 Please fix the errors before deploying${NC}"
    exit 1
fi