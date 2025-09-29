# Sentinel Environment Configurations

This directory contains environment-specific configurations for the Sentinel cybersecurity triage system. Each environment is designed with specific resource allocations, feature flags, and security settings appropriate for its use case.

## 📁 Directory Structure

```
infra/envs/
├── dev/                          # Development environment
│   ├── main.tf                   # Environment-specific Terraform configuration
│   ├── variables.tf              # Development variable definitions with validation
│   ├── outputs.tf                # Development-specific outputs
│   ├── terraform.tfvars          # Development configuration values
│   ├── terraform.tfvars.example  # Template for development configuration
│   ├── backend.hcl               # Development backend configuration
│   └── deploy.sh                 # Development deployment script
├── prod/                         # Production environment
│   ├── main.tf                   # Production Terraform configuration
│   ├── variables.tf              # Production variable definitions with validation
│   ├── outputs.tf                # Production-specific outputs
│   ├── terraform.tfvars          # Production configuration values
│   ├── terraform.tfvars.example  # Template for production configuration
│   ├── backend.hcl               # Production backend configuration
│   └── deploy.sh                 # Production deployment script (enhanced security)
├── validate-config.sh            # Configuration validation script
└── README.md                     # This file
```

## 🏗️ Environment Configurations

### Development Environment (`dev/`)

**Purpose**: Cost-effective environment for development, testing, and experimentation.

**Key Characteristics**:
- **Resource Optimization**: Smaller Lambda memory (256MB), shorter timeouts (180s)
- **Cost Controls**: Strict limits ($50/month, 500 LLM calls/day)
- **Feature Flags**: Conservative settings with optional features disabled
- **Monitoring**: Basic monitoring with shorter log retention (7 days)
- **Security**: Development-appropriate security with local testing support

**Typical Use Cases**:
- Feature development and testing
- Integration testing
- Proof of concept validation
- Developer training and experimentation

### Production Environment (`prod/`)

**Purpose**: High-performance, secure, and reliable environment for production workloads.

**Key Characteristics**:
- **Resource Optimization**: Higher Lambda memory (1024MB), full timeouts (600s)
- **Cost Controls**: Production-appropriate limits ($1500/month, 25000 LLM calls/day)
- **Feature Flags**: Full feature set enabled for complete functionality
- **Monitoring**: Comprehensive monitoring with extended log retention (90 days)
- **Security**: Production-grade security with strict validation and compliance

**Typical Use Cases**:
- Production cybersecurity intelligence processing
- Real-time threat analysis and triage
- Automated security alerting and reporting
- Enterprise security operations

## 🚀 Quick Start

### 1. Choose Your Environment

```bash
# For development
cd infra/envs/dev

# For production
cd infra/envs/prod
```

### 2. Configure Your Environment

```bash
# Copy the example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit the configuration with your specific values
nano terraform.tfvars
```

### 3. Validate Configuration

```bash
# Validate specific environment
../validate-config.sh dev

# Or validate all environments
../validate-config.sh
```

### 4. Deploy

```bash
# Deploy with enhanced validation and safety checks
./deploy.sh
```

## ⚙️ Configuration Guide

### Required Configuration Changes

Before deploying any environment, you **must** update the following values in `terraform.tfvars`:

#### 📧 Email Configuration
```hcl
# Update with your actual email addresses
ses_sender_email = "noreply@yourcompany.com"

escalation_emails = [
  "security-team@yourcompany.com",
  "analysts@yourcompany.com"
]

digest_emails = [
  "security-team@yourcompany.com",
  "management@yourcompany.com"
]

alert_emails = [
  "soc@yourcompany.com",
  "security-alerts@yourcompany.com"
]
```

#### 🌐 Domain and Repository Configuration
```hcl
# For development
domain_name = "sentinel-dev.yourcompany.com"
amplify_repository_url = "https://github.com/yourorg/sentinel-web-app"

# For production
amplify_callback_urls = [
  "https://sentinel.yourcompany.com/callback"
]
amplify_logout_urls = [
  "https://sentinel.yourcompany.com/logout"
]
```

#### 💰 Cost Controls
```hcl
# Adjust based on your expected usage
max_daily_llm_calls  = 1000    # Development: lower limit
max_monthly_cost_usd = 100.0   # Development: strict limit

max_daily_llm_calls  = 25000   # Production: higher limit
max_monthly_cost_usd = 1500.0  # Production: appropriate budget
```

### Optional Configuration Customizations

#### 🎯 AI/ML Thresholds
```hcl
# Adjust based on your quality requirements
relevance_threshold  = 0.7   # Higher = more selective
similarity_threshold = 0.85  # Higher = fewer duplicates detected
confidence_threshold = 0.8   # Higher = more items go to human review
```

#### 🔧 Resource Configuration
```hcl
# Adjust based on your performance requirements
lambda_memory_size     = 512   # MB (128-10240)
lambda_timeout         = 300   # seconds (1-900)
max_concurrent_feeds   = 5     # Number of feeds processed simultaneously
max_articles_per_fetch = 50    # Articles per feed fetch
```

#### 🏗️ Infrastructure Configuration
```hcl
# VPC Configuration
vpc_cidr = "10.0.0.0/16"  # Ensure no conflicts with existing networks
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

# Feature Flags
enable_agents              = true   # Enable Bedrock AgentCore integration
enable_amplify            = true   # Enable web application
enable_opensearch         = true   # Enable vector search
enable_semantic_dedup     = true   # Enable advanced deduplication
enable_auto_publish       = false  # Keep human review (recommended)
```

## 🔒 Security Considerations

### Development Environment Security
- Uses development-appropriate security settings
- Allows localhost callbacks for local development
- Shorter credential rotation periods
- Basic monitoring and alerting

### Production Environment Security
- Enforces HTTPS-only callbacks
- Requires production email domains
- Enhanced IAM policies with least privilege
- Comprehensive audit logging
- Advanced threat detection and monitoring

### Security Best Practices
1. **Never commit `terraform.tfvars`** - Contains sensitive configuration
2. **Use separate AWS accounts** for dev and prod environments
3. **Enable MFA** for production deployments
4. **Regularly rotate credentials** and review access
5. **Monitor costs and usage** to detect anomalies

## 🛠️ Validation and Testing

### Configuration Validation

The `validate-config.sh` script performs comprehensive validation:

```bash
# Validate all environments
./validate-config.sh

# Validate specific environment
./validate-config.sh dev
./validate-config.sh prod
```

**Validation Checks Include**:
- ✅ File existence and syntax
- ✅ Email address format validation
- ✅ Cost limit reasonableness
- ✅ Threshold value ranges
- ✅ Security configuration review
- ✅ Environment-specific requirements

### Pre-Deployment Testing

Before deploying to production:

1. **Deploy to development first**
2. **Run integration tests**
3. **Validate all email notifications**
4. **Test RSS feed processing**
5. **Verify monitoring and alerting**
6. **Perform security scan**

## 📊 Monitoring and Observability

### Development Environment Monitoring
- Basic CloudWatch metrics
- 7-day log retention
- Cost tracking with alerts
- Simple dashboard

### Production Environment Monitoring
- Comprehensive CloudWatch dashboards
- 90-day log retention
- Advanced cost monitoring with anomaly detection
- X-Ray distributed tracing
- Security monitoring and compliance reporting

### Key Metrics to Monitor
- **Processing Metrics**: Feed ingestion rates, relevancy assessment accuracy
- **Performance Metrics**: Lambda execution times, error rates
- **Cost Metrics**: Daily/monthly spend, LLM API usage
- **Security Metrics**: Failed authentication attempts, unusual access patterns

## 🚨 Troubleshooting

### Common Issues

#### Configuration Validation Errors
```bash
# Error: Invalid email addresses
# Solution: Update terraform.tfvars with valid email addresses

# Error: Terraform validation failed
# Solution: Run terraform fmt -recursive and fix syntax errors

# Error: Cost limits too low/high
# Solution: Adjust cost limits based on environment requirements
```

#### Deployment Failures
```bash
# Error: Backend initialization failed
# Solution: Ensure S3 bucket and DynamoDB table exist for state management

# Error: AWS credentials not configured
# Solution: Run aws configure or set environment variables

# Error: Insufficient permissions
# Solution: Ensure AWS user has required permissions for resource creation
```

#### Runtime Issues
```bash
# Error: SES email delivery failures
# Solution: Verify email addresses in SES console

# Error: Lambda timeout errors
# Solution: Increase lambda_timeout in terraform.tfvars

# Error: Cost limit exceeded
# Solution: Review usage and adjust limits or optimize configuration
```

### Getting Help

1. **Check the validation script output** for specific error details
2. **Review CloudWatch logs** for runtime issues
3. **Consult the main project documentation** for architectural guidance
4. **Use AWS support** for infrastructure-specific issues

## 🔄 Environment Lifecycle Management

### Development Environment
- **Creation**: Quick setup for new developers
- **Updates**: Frequent updates for testing new features
- **Destruction**: Can be destroyed and recreated as needed
- **Backup**: Not required (can be recreated from code)

### Production Environment
- **Creation**: Careful planning and validation required
- **Updates**: Change management process with approval
- **Destruction**: Requires explicit approval and data backup
- **Backup**: Automated backups and disaster recovery procedures

### Best Practices
1. **Infrastructure as Code**: All changes through Terraform
2. **Version Control**: Track all configuration changes
3. **Change Management**: Formal process for production changes
4. **Testing**: Validate changes in development first
5. **Documentation**: Keep runbooks and procedures updated

## 📚 Additional Resources

- [Main Sentinel Documentation](../../README.md)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)
- [AWS Security Best Practices](https://aws.amazon.com/architecture/security-identity-compliance/)
- [Cost Optimization Guide](https://aws.amazon.com/aws-cost-management/)

---

**Note**: This configuration system is designed to support the complete Sentinel cybersecurity triage platform. Ensure you understand the security and cost implications before deploying to production environments.