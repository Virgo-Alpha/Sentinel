# Sentinel Configuration Management Guide

This guide covers managing RSS feeds, keywords, email notifications, user access, and configuration changes in Sentinel.

## RSS Feed Management

### Adding New RSS Feeds

#### 1. Update Feed Configuration
```bash
# Edit the feeds configuration
vim config/feeds.yaml

# Add new feed entry
feeds:
  - name: "New Security Feed"
    url: "https://example.com/security.xml"
    category: "advisories"
    enabled: true
    fetch_interval: "30m"
    description: "Security advisories from Example Corp"
```

#### 2. Validate and Deploy
```bash
# Validate configuration
python3 scripts/validate-config.py --config config/feeds.yaml

# Deploy to environment
./scripts/configure-feeds.sh -e prod -f

# Verify feed processing
aws dynamodb get-item \
    --table-name sentinel-feeds-prod \
    --key '{"feed_id": {"S": "new-security-feed"}}'
```

### Feed Troubleshooting
- **URL Validation**: Test feed accessibility with curl
- **Format Issues**: Validate XML/RSS format
- **Processing Errors**: Check CloudWatch logs
- **Performance**: Monitor fetch intervals and response times

## Keyword Management

### Updating Keywords
```bash
# Edit keyword configuration
vim config/keywords.yaml

# Test keyword matching
python3 scripts/test-keyword-matching.py -c config/keywords.yaml -t

# Deploy keywords
./scripts/deploy-keywords.sh -e prod
```

### Best Practices
- Use specific keywords over generic terms
- Include variations and synonyms
- Set appropriate weights (0.0-1.0)
- Test with sample content before deployment#
# Email Notification Configuration

### SES Setup
```bash
# Verify email domain
aws ses verify-domain-identity --domain company.com

# Configure DKIM
aws ses put-identity-dkim-attributes \
    --identity company.com \
    --dkim-enabled

# Set up notification templates
aws ses create-template \
    --template '{
      "TemplateName": "SecurityAlert",
      "Subject": "Sentinel Security Alert",
      "HtmlPart": "<h1>Security Alert</h1><p>{{content}}</p>",
      "TextPart": "Security Alert: {{content}}"
    }'
```

### Managing Recipients
```bash
# Add email recipients to configuration
vim config/notifications.yaml

# Update notification settings
notifications:
  email:
    critical_alerts:
      - security-team@company.com
      - management@company.com
    daily_digest:
      - analysts@company.com
```

## User Management

### Creating Users
```bash
# Create new user in Cognito
aws cognito-idp admin-create-user \
    --user-pool-id us-east-1_XXXXXXXXX \
    --username new.analyst@company.com \
    --user-attributes Name=email,Value=new.analyst@company.com \
    --temporary-password TempPass123!

# Add user to appropriate group
aws cognito-idp admin-add-user-to-group \
    --user-pool-id us-east-1_XXXXXXXXX \
    --username new.analyst@company.com \
    --group-name SecurityAnalysts
```

### Access Control
- **SecurityAnalysts**: Article review and basic reporting
- **SecurityManagers**: Advanced reporting and user management  
- **Administrators**: Full system configuration access

## Configuration Change Management

### Change Process
1. **Test in Development**: Validate changes in dev environment
2. **Create Change Request**: Document changes and impact
3. **Peer Review**: Have changes reviewed by team member
4. **Deploy to Staging**: Test in staging environment
5. **Production Deployment**: Deploy with rollback plan
6. **Validation**: Verify changes work as expected

### Rollback Procedures
```bash
# Rollback feed configuration
git checkout HEAD~1 config/feeds.yaml
./scripts/configure-feeds.sh -e prod -f

# Rollback keyword configuration  
git checkout HEAD~1 config/keywords.yaml
./scripts/deploy-keywords.sh -e prod

# Rollback infrastructure changes
cd infra/
terraform plan -destroy -target=resource.name
terraform apply -target=resource.name
```

### Audit Trail
- All configuration changes tracked in Git
- Deployment logs stored in CloudWatch
- Change requests documented in ticketing system
- Regular configuration reviews and audits