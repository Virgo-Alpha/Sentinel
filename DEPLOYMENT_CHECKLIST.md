# Sentinel Deployment Checklist

This checklist ensures all components are properly deployed and validated before going live.

## Pre-Deployment Checklist

### Prerequisites ✅
- [ ] AWS CLI configured with appropriate credentials
- [ ] Terraform >= 1.5.0 installed
- [ ] Python >= 3.9 installed
- [ ] Node.js >= 18.0 installed (for web app)
- [ ] Required AWS service limits verified
- [ ] IAM permissions validated

### Environment Configuration ✅
- [ ] Environment-specific tfvars file reviewed (`infra/envs/{env}.tfvars`)
- [ ] RSS feed URLs validated and accessible
- [ ] Target keywords configured appropriately
- [ ] Security settings reviewed (encryption, VPC, IAM)
- [ ] Cost optimization settings configured

### Code Quality ✅
- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Security scans completed (tfsec, etc.)
- [ ] Code review completed
- [ ] Documentation updated

## Deployment Execution

### Infrastructure Deployment ✅
- [ ] Terraform backend bootstrapped
  ```bash
  cd infra/bootstrap && terraform init && terraform apply
  ```
- [ ] Main infrastructure planned
  ```bash
  ./scripts/deploy.sh -e {env} --validate-only
  ```
- [ ] Infrastructure deployed
  ```bash
  ./scripts/deploy.sh -e {env}
  ```
- [ ] Deployment logs reviewed for errors
- [ ] Terraform outputs verified

### Infrastructure Validation ✅
- [ ] VPC and networking components created
  ```bash
  aws ec2 describe-vpcs --filters "Name=tag:Project,Values=sentinel"
  ```
- [ ] DynamoDB tables accessible
  ```bash
  aws dynamodb list-tables | grep sentinel
  ```
- [ ] S3 buckets created with proper policies
  ```bash
  aws s3 ls | grep sentinel
  ```
- [ ] Lambda functions deployed and active
  ```bash
  aws lambda list-functions | grep sentinel
  ```
- [ ] OpenSearch Serverless collection active
  ```bash
  aws opensearchserverless list-collections
  ```
- [ ] IAM roles and policies configured
- [ ] VPC endpoints functional
- [ ] CloudWatch dashboards created
- [ ] X-Ray tracing enabled

### Application Configuration ✅
- [ ] RSS feeds configured
  ```bash
  ./scripts/configure-feeds.sh -e {env}
  ```
- [ ] Target keywords loaded
- [ ] Feed categorization verified
- [ ] Keyword matching tested
  ```bash
  ./scripts/test-keyword-matching.py -t
  ```
- [ ] Configuration reload tested

### Lambda Function Testing ✅
- [ ] Feed parser function tested
- [ ] Relevancy evaluator function tested
- [ ] Deduplication tool function tested
- [ ] Guardrail tool function tested
- [ ] Storage tool function tested
- [ ] Query KB function tested
- [ ] Human escalation function tested
- [ ] Publish decision function tested
- [ ] Commentary API function tested

### Web Application Deployment ✅
- [ ] Amplify app configured
- [ ] Cognito user pools created
- [ ] API Gateway endpoints configured
- [ ] Authentication flow tested
- [ ] User groups configured (Analysts, Admins)
- [ ] Web app build and deployment successful

## Post-Deployment Validation

### End-to-End System Testing ✅
- [ ] Complete ingestion cycle tested
  ```bash
  ./scripts/validate-system.sh -e {env}
  ```
- [ ] RSS feed processing verified
- [ ] Article deduplication accuracy ≥85%
- [ ] Keyword detection accuracy ≥70%
- [ ] Human review workflow functional
- [ ] Report generation working
- [ ] XLSX export functional
- [ ] Performance metrics within thresholds (≤5 min latency)

### Security Validation ✅
- [ ] Encryption at rest verified
- [ ] Encryption in transit verified
- [ ] IAM least privilege principles applied
- [ ] VPC security groups configured properly
- [ ] API authentication working
- [ ] Data access controls tested
- [ ] Security headers configured
- [ ] WAF rules active (production only)

### Performance Testing ✅
- [ ] Load testing completed
  ```bash
  cd tests/performance && make test-load
  ```
- [ ] Stress testing completed
- [ ] Volume testing completed
- [ ] Memory usage within limits
- [ ] CPU utilization acceptable
- [ ] Database performance validated
- [ ] API response times acceptable

### Monitoring and Alerting ✅
- [ ] CloudWatch dashboards accessible
- [ ] Key metrics being collected
- [ ] Alerts configured for critical issues
- [ ] Log aggregation working
- [ ] X-Ray traces visible
- [ ] SNS notifications configured
- [ ] Email alerts tested

### Operational Readiness ✅
- [ ] Backup procedures tested
- [ ] Disaster recovery plan validated
- [ ] Runbook documentation complete
- [ ] Troubleshooting guide available
- [ ] Support contacts configured
- [ ] Escalation procedures defined

## Production-Specific Checklist

### Production Environment Only ✅
- [ ] All 21 RSS feeds configured and validated
- [ ] Production-grade resource sizing
- [ ] Auto-scaling configured
- [ ] Cross-region replication enabled
- [ ] Point-in-time recovery enabled
- [ ] Advanced security features enabled
- [ ] Compliance requirements met
- [ ] Cost monitoring and budgets set

### User Management ✅
- [ ] Initial admin users created
- [ ] User groups properly configured
- [ ] Access permissions tested
- [ ] Password policies enforced
- [ ] MFA enabled for admin users
- [ ] User onboarding process documented

### Data Management ✅
- [ ] Data retention policies configured
- [ ] Archival procedures tested
- [ ] Data export capabilities verified
- [ ] Privacy controls implemented
- [ ] Audit logging enabled

## Go-Live Checklist

### Final Validation ✅
- [ ] All previous checklist items completed
- [ ] Stakeholder sign-off obtained
- [ ] Go-live communication sent
- [ ] Support team briefed
- [ ] Rollback plan prepared

### Go-Live Activities ✅
- [ ] DNS cutover (if applicable)
- [ ] User access enabled
- [ ] Monitoring alerts activated
- [ ] Initial data ingestion started
- [ ] System health verified
- [ ] User acceptance testing completed

### Post Go-Live ✅
- [ ] System monitoring for first 24 hours
- [ ] User feedback collected
- [ ] Performance metrics reviewed
- [ ] Any issues documented and resolved
- [ ] Success metrics captured
- [ ] Lessons learned documented

## Rollback Procedures

### If Issues Occur ✅
- [ ] Rollback plan documented and tested
- [ ] Database backup restoration procedure
- [ ] Infrastructure rollback using Terraform
- [ ] User communication plan for downtime
- [ ] Issue escalation procedures

### Rollback Execution ✅
- [ ] Stop new data ingestion
- [ ] Backup current state
- [ ] Execute infrastructure rollback
  ```bash
  ./scripts/deploy.sh -e {env} --destroy
  # Deploy previous version
  ```
- [ ] Restore database from backup
- [ ] Verify system functionality
- [ ] Communicate status to users

## Sign-Off

### Technical Sign-Off ✅
- [ ] **Infrastructure Team**: _________________ Date: _______
- [ ] **Security Team**: _________________ Date: _______
- [ ] **Development Team**: _________________ Date: _______
- [ ] **QA Team**: _________________ Date: _______

### Business Sign-Off ✅
- [ ] **Product Owner**: _________________ Date: _______
- [ ] **Security Operations**: _________________ Date: _______
- [ ] **IT Operations**: _________________ Date: _______

## Environment-Specific Commands

### Development Environment
```bash
# Deploy
./scripts/deploy.sh -e dev

# Configure
./scripts/configure-feeds.sh -e dev

# Validate
./scripts/validate-system.sh -e dev

# Test
cd tests/performance && make test-quick
```

### Production Environment
```bash
# Deploy (with approval)
./scripts/deploy.sh -e prod

# Configure (all feeds)
./scripts/configure-feeds.sh -e prod

# Validate (comprehensive)
./scripts/validate-system.sh -e prod -t 3600

# Performance test
cd tests/performance && make test-all
```

## Troubleshooting Quick Reference

### Common Issues
1. **Terraform state lock**: `terraform force-unlock <lock-id>`
2. **Lambda timeout**: Check CloudWatch logs, increase timeout/memory
3. **DynamoDB throttling**: Check capacity settings, enable auto-scaling
4. **S3 access denied**: Verify IAM policies and bucket policies
5. **VPC connectivity**: Check security groups and NACLs

### Log Locations
- **Deployment logs**: `logs/deployment_*.log`
- **Validation logs**: `logs/validation_*.log`
- **CloudWatch logs**: `/aws/lambda/sentinel-*`
- **Application logs**: Check Amplify console

### Support Contacts
- **Infrastructure Issues**: infrastructure-team@company.com
- **Security Issues**: security-team@company.com
- **Application Issues**: development-team@company.com
- **Emergency**: on-call-engineer@company.com

---

**Note**: This checklist should be customized for your specific organization's requirements and procedures. Ensure all team members are familiar with the deployment process and have access to necessary tools and credentials.