# Sentinel Operations Runbook

This comprehensive operations runbook provides detailed procedures for monitoring, maintaining, and operating the Sentinel Cybersecurity Triage System in production environments.

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Monitoring and Alerting](#monitoring-and-alerting)
3. [Maintenance Procedures](#maintenance-procedures)
4. [Performance Optimization](#performance-optimization)
5. [Backup and Recovery](#backup-and-recovery)
6. [Scaling Operations](#scaling-operations)
7. [Security Operations](#security-operations)
8. [Incident Response](#incident-response)
9. [Change Management](#change-management)
10. [Cost Optimization](#cost-optimization)

## Daily Operations

### Morning Health Check (8:00 AM)

#### 1. System Status Review
```bash
# Check overall system health
curl -f https://sentinel.company.com/api/v1/health

# Review CloudWatch dashboard
# Navigate to: CloudWatch > Dashboards > Sentinel-Production-Overview
```

**Key Metrics to Review:**
- **Feed Processing Status**: All 21 feeds processed in last 24 hours
- **Article Processing Rate**: Target 95% of articles processed within 5 minutes
- **Error Rates**: Lambda error rate < 1%, API error rate < 0.5%
- **Database Performance**: DynamoDB throttling = 0, latency < 100ms
- **User Activity**: Active user sessions, query response times

#### 2. Feed Health Assessment
```bash
# Check feed processing status
aws dynamodb scan \
    --table-name sentinel-feeds-prod \
    --filter-expression "#status <> :active_status" \
    --expression-attribute-names '{"#status": "status"}' \
    --expression-attribute-values '{":active_status": {"S": "active"}}' \
    --projection-expression "feed_id, #name, #status, last_processed, error_count"
```

**Action Items:**
- **Failed Feeds**: Investigate and restart failed feed processing
- **Delayed Feeds**: Check if feeds are processing within expected intervals
- **High Error Counts**: Review feed URLs and parsing logic

#### 3. Performance Metrics Review
```bash
# Check Lambda function performance
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Duration \
    --dimensions Name=FunctionName,Value=sentinel-feed-parser-prod \
    --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 3600 \
    --statistics Average,Maximum
```

**Performance Thresholds:**
- **Feed Parser**: Average < 30s, Maximum < 300s
- **Relevancy Evaluator**: Average < 45s, Maximum < 300s
- **API Functions**: Average < 2s, Maximum < 10s

### Midday Check (12:00 PM)

#### 1. User Activity Monitoring
- Review active user sessions and query patterns
- Check for any user-reported issues or support tickets
- Monitor API usage and rate limiting

#### 2. Data Quality Assessment
```bash
# Check article processing quality
aws dynamodb scan \
    --table-name sentinel-articles-prod \
    --filter-expression "created_at > :yesterday" \
    --expression-attribute-values '{":yesterday": {"S": "'$(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%SZ)'"}}' \
    --select "COUNT"
```

**Quality Metrics:**
- **Processing Rate**: 95% of articles processed within SLA
- **Relevancy Accuracy**: Manual spot-check of high/low relevancy scores
- **Deduplication Rate**: 85%+ duplicate detection accuracy

### Evening Review (6:00 PM)

#### 1. Daily Summary Report
Generate and review daily operational summary:
- Total articles processed
- Feed processing success rates
- User activity statistics
- System performance metrics
- Any incidents or issues resolved

#### 2. Preparation for Next Day
- Review scheduled maintenance windows
- Check for any planned deployments
- Verify backup completion status
- Update on-call rotation if needed

## Monitoring and Alerting

### CloudWatch Dashboards

#### 1. Production Overview Dashboard
**Widgets to Monitor:**
- System health status indicators
- Article processing throughput
- Feed processing success rates
- API response times and error rates
- Database performance metrics
- Cost tracking and budget alerts

#### 2. Technical Operations Dashboard
**Advanced Metrics:**
- Lambda function performance and errors
- DynamoDB read/write capacity utilization
- S3 request metrics and errors
- OpenSearch query performance
- X-Ray trace analysis

#### 3. Business Metrics Dashboard
**Key Performance Indicators:**
- Daily/weekly article volumes
- Relevancy assessment accuracy
- User engagement metrics
- Report generation statistics
- Feed source performance comparison

### Alert Configuration

#### Critical Alerts (Immediate Response Required)

```yaml
critical_alerts:
  system_down:
    metric: "AWS/ApplicationELB/TargetResponseTime"
    threshold: "> 30 seconds"
    evaluation_periods: 2
    notification: "pagerduty + sms"
    
  high_error_rate:
    metric: "AWS/Lambda/Errors"
    threshold: "> 5% error rate"
    evaluation_periods: 3
    notification: "pagerduty + email"
    
  database_throttling:
    metric: "AWS/DynamoDB/ThrottledRequests"
    threshold: "> 0"
    evaluation_periods: 1
    notification: "pagerduty + slack"
```

#### Warning Alerts (Response Within 1 Hour)

```yaml
warning_alerts:
  feed_processing_delay:
    metric: "Custom/Sentinel/FeedProcessingDelay"
    threshold: "> 2 hours"
    evaluation_periods: 2
    notification: "email + slack"
    
  high_memory_usage:
    metric: "AWS/Lambda/MemoryUtilization"
    threshold: "> 80%"
    evaluation_periods: 3
    notification: "email"
    
  cost_anomaly:
    metric: "AWS/Billing/EstimatedCharges"
    threshold: "> 120% of budget"
    evaluation_periods: 1
    notification: "email + slack"
```

#### Informational Alerts (Daily Review)

```yaml
info_alerts:
  low_article_volume:
    metric: "Custom/Sentinel/ArticlesProcessed"
    threshold: "< 50 articles/day"
    evaluation_periods: 1
    notification: "email"
    
  user_activity_low:
    metric: "Custom/Sentinel/ActiveUsers"
    threshold: "< 5 users/day"
    evaluation_periods: 1
    notification: "email"
```

### Custom Metrics

#### Application-Specific Metrics
```python
# Example custom metrics publishing
import boto3

cloudwatch = boto3.client('cloudwatch')

# Feed processing metrics
cloudwatch.put_metric_data(
    Namespace='Sentinel/Feeds',
    MetricData=[
        {
            'MetricName': 'ArticlesProcessed',
            'Value': article_count,
            'Unit': 'Count',
            'Dimensions': [
                {'Name': 'FeedSource', 'Value': feed_source},
                {'Name': 'Environment', 'Value': 'production'}
            ]
        }
    ]
)

# Relevancy assessment metrics
cloudwatch.put_metric_data(
    Namespace='Sentinel/Quality',
    MetricData=[
        {
            'MetricName': 'RelevancyAccuracy',
            'Value': accuracy_percentage,
            'Unit': 'Percent'
        }
    ]
)
```

## Maintenance Procedures

### Weekly Maintenance (Sundays 2:00 AM)

#### 1. Database Maintenance
```bash
# Check DynamoDB table health
aws dynamodb describe-table --table-name sentinel-articles-prod

# Review and optimize indexes
aws dynamodb describe-table --table-name sentinel-articles-prod \
    --query 'Table.GlobalSecondaryIndexes[*].{IndexName:IndexName,Status:IndexStatus,ReadCapacity:ProvisionedThroughput.ReadCapacityUnits,WriteCapacity:ProvisionedThroughput.WriteCapacityUnits}'

# Clean up old test data (if any)
aws dynamodb scan \
    --table-name sentinel-articles-prod \
    --filter-expression "contains(title, :test)" \
    --expression-attribute-values '{":test": {"S": "test"}}' \
    --projection-expression "article_id, created_at"
```

#### 2. Log Management
```bash
# Archive old CloudWatch logs
aws logs describe-log-groups \
    --log-group-name-prefix "/aws/lambda/sentinel" \
    --query 'logGroups[*].{LogGroupName:logGroupName,RetentionInDays:retentionInDays}'

# Set retention policies for cost optimization
for log_group in $(aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/sentinel" --query 'logGroups[*].logGroupName' --output text); do
    aws logs put-retention-policy \
        --log-group-name "$log_group" \
        --retention-in-days 30
done
```

#### 3. Performance Analysis
```bash
# Generate weekly performance report
python3 scripts/generate-performance-report.py \
    --start-date $(date -d '7 days ago' +%Y-%m-%d) \
    --end-date $(date +%Y-%m-%d) \
    --output-format pdf \
    --email-recipients ops-team@company.com
```

### Monthly Maintenance (First Sunday 1:00 AM)

#### 1. Security Updates
```bash
# Check for Lambda runtime updates
aws lambda list-functions \
    --query 'Functions[?starts_with(FunctionName, `sentinel`)].{Name:FunctionName,Runtime:Runtime}'

# Update Lambda function runtimes if needed
aws lambda update-function-configuration \
    --function-name sentinel-feed-parser-prod \
    --runtime python3.11
```

#### 2. Capacity Planning Review
```bash
# Analyze DynamoDB capacity utilization
aws cloudwatch get-metric-statistics \
    --namespace AWS/DynamoDB \
    --metric-name ConsumedReadCapacityUnits \
    --dimensions Name=TableName,Value=sentinel-articles-prod \
    --start-time $(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 86400 \
    --statistics Average,Maximum
```

#### 3. Cost Optimization Review
- Review AWS Cost Explorer for spending trends
- Analyze resource utilization and right-sizing opportunities
- Update reserved capacity based on usage patterns
- Review and optimize data retention policies

### Quarterly Maintenance (First Sunday of Quarter)

#### 1. Disaster Recovery Testing
```bash
# Test backup restoration procedures
aws dynamodb restore-table-to-point-in-time \
    --source-table-name sentinel-articles-prod \
    --target-table-name sentinel-articles-dr-test \
    --restore-date-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%SZ)

# Validate restored data
aws dynamodb scan \
    --table-name sentinel-articles-dr-test \
    --select "COUNT"
```

#### 2. Security Audit
- Review IAM roles and policies for least privilege
- Audit user access and permissions
- Check encryption settings and key rotation
- Review VPC security groups and NACLs
- Conduct penetration testing (if applicable)

#### 3. Performance Baseline Update
- Update performance baselines based on quarterly data
- Adjust alerting thresholds based on observed patterns
- Review and update capacity planning projections
- Optimize queries and indexes based on usage patterns

## Performance Optimization

### Lambda Function Optimization

#### 1. Memory and Timeout Tuning
```bash
# Analyze Lambda performance metrics
aws logs filter-log-events \
    --log-group-name /aws/lambda/sentinel-feed-parser-prod \
    --filter-pattern "REPORT" \
    --start-time $(date -d '7 days ago' +%s)000 \
    --end-time $(date +%s)000 \
    | grep "REPORT" | tail -100
```

**Optimization Guidelines:**
- **Memory**: Set to 1.5x peak memory usage for optimal performance
- **Timeout**: Set to 2x average execution time with reasonable maximum
- **Provisioned Concurrency**: Use for functions with consistent traffic

#### 2. Cold Start Optimization
```python
# Optimize Lambda cold starts
import json
import boto3

# Initialize clients outside handler
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('sentinel-articles-prod')

def lambda_handler(event, context):
    # Handler code here
    pass
```

### Database Performance Tuning

#### 1. DynamoDB Optimization
```bash
# Monitor hot partitions
aws cloudwatch get-metric-statistics \
    --namespace AWS/DynamoDB \
    --metric-name ConsumedReadCapacityUnits \
    --dimensions Name=TableName,Value=sentinel-articles-prod \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Sum
```

**Optimization Strategies:**
- **Partition Key Design**: Ensure even distribution across partitions
- **Global Secondary Indexes**: Create indexes for common query patterns
- **Auto Scaling**: Enable auto scaling for variable workloads
- **Query Optimization**: Use Query instead of Scan operations

#### 2. OpenSearch Performance
```bash
# Check OpenSearch cluster performance
curl -X GET "https://search-sentinel-prod.us-east-1.es.amazonaws.com/_cluster/stats"

# Optimize index settings
curl -X PUT "https://search-sentinel-prod.us-east-1.es.amazonaws.com/articles/_settings" \
     -H "Content-Type: application/json" \
     -d '{
       "index": {
         "refresh_interval": "30s",
         "number_of_replicas": 1
       }
     }'
```

### API Performance Optimization

#### 1. Caching Strategy
```python
# Implement caching for frequently accessed data
import redis
import json

redis_client = redis.Redis(host='sentinel-cache.redis.amazonaws.com')

def get_cached_articles(query_hash):
    cached_result = redis_client.get(f"articles:{query_hash}")
    if cached_result:
        return json.loads(cached_result)
    return None

def cache_articles(query_hash, articles, ttl=300):
    redis_client.setex(
        f"articles:{query_hash}",
        ttl,
        json.dumps(articles)
    )
```

#### 2. API Gateway Optimization
```bash
# Enable API Gateway caching
aws apigateway put-method-response \
    --rest-api-id your-api-id \
    --resource-id your-resource-id \
    --http-method GET \
    --status-code 200 \
    --response-parameters method.response.header.Cache-Control=true
```

## Backup and Recovery

### Automated Backup Procedures

#### 1. DynamoDB Backups
```bash
# Enable point-in-time recovery
aws dynamodb update-continuous-backups \
    --table-name sentinel-articles-prod \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

# Create on-demand backup
aws dynamodb create-backup \
    --table-name sentinel-articles-prod \
    --backup-name "sentinel-articles-$(date +%Y%m%d-%H%M%S)"
```

#### 2. S3 Data Backup
```bash
# Enable versioning and cross-region replication
aws s3api put-bucket-versioning \
    --bucket sentinel-content-prod \
    --versioning-configuration Status=Enabled

# Set up lifecycle policies
aws s3api put-bucket-lifecycle-configuration \
    --bucket sentinel-content-prod \
    --lifecycle-configuration file://s3-lifecycle-policy.json
```

#### 3. Configuration Backup
```bash
# Backup Terraform state
aws s3 cp terraform.tfstate \
    s3://sentinel-terraform-backups/$(date +%Y%m%d)/terraform.tfstate

# Backup configuration files
tar -czf sentinel-config-$(date +%Y%m%d).tar.gz config/
aws s3 cp sentinel-config-$(date +%Y%m%d).tar.gz \
    s3://sentinel-config-backups/
```

### Recovery Procedures

#### 1. Database Recovery
```bash
# Restore DynamoDB table from point-in-time
aws dynamodb restore-table-to-point-in-time \
    --source-table-name sentinel-articles-prod \
    --target-table-name sentinel-articles-restored \
    --restore-date-time 2024-01-15T10:00:00Z

# Restore from backup
aws dynamodb restore-table-from-backup \
    --target-table-name sentinel-articles-restored \
    --backup-arn arn:aws:dynamodb:us-east-1:123456789012:table/sentinel-articles-prod/backup/01234567890123-abcdefgh
```

#### 2. Application Recovery
```bash
# Rollback Lambda function to previous version
aws lambda update-function-code \
    --function-name sentinel-feed-parser-prod \
    --s3-bucket sentinel-lambda-deployments \
    --s3-key previous-version/sentinel-feed-parser.zip

# Rollback infrastructure with Terraform
terraform plan -destroy -target=aws_lambda_function.feed_parser
terraform apply -target=aws_lambda_function.feed_parser
```

### Recovery Testing

#### Monthly Recovery Drills
```bash
# Test database recovery
./scripts/test-database-recovery.sh --environment staging

# Test application recovery
./scripts/test-application-recovery.sh --environment staging

# Validate recovered data
./scripts/validate-recovery.sh --environment staging
```

## Scaling Operations

### Horizontal Scaling

#### 1. Lambda Concurrency Management
```bash
# Monitor concurrent executions
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name ConcurrentExecutions \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Maximum

# Set reserved concurrency for critical functions
aws lambda put-reserved-concurrency-config \
    --function-name sentinel-feed-parser-prod \
    --reserved-concurrent-executions 100
```

#### 2. Database Scaling
```bash
# Enable DynamoDB auto scaling
aws application-autoscaling register-scalable-target \
    --service-namespace dynamodb \
    --resource-id table/sentinel-articles-prod \
    --scalable-dimension dynamodb:table:ReadCapacityUnits \
    --min-capacity 5 \
    --max-capacity 1000

# Configure scaling policy
aws application-autoscaling put-scaling-policy \
    --service-namespace dynamodb \
    --resource-id table/sentinel-articles-prod \
    --scalable-dimension dynamodb:table:ReadCapacityUnits \
    --policy-name sentinel-articles-read-scaling-policy \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

### Vertical Scaling

#### 1. Lambda Resource Allocation
```bash
# Increase Lambda memory for better performance
aws lambda update-function-configuration \
    --function-name sentinel-feed-parser-prod \
    --memory-size 1024 \
    --timeout 900
```

#### 2. OpenSearch Capacity
```bash
# Scale OpenSearch Serverless capacity
aws opensearchserverless put-capacity-policy \
    --name sentinel-capacity-policy \
    --policy '{
      "Rules": [
        {
          "Resource": ["collection/sentinel-articles"],
          "ResourceType": "collection",
          "MinIndexingCapacityInOCU": 2,
          "MaxIndexingCapacityInOCU": 20,
          "MinSearchCapacityInOCU": 2,
          "MaxSearchCapacityInOCU": 20
        }
      ]
    }'
```

### Load Testing

#### 1. Performance Testing
```bash
# Run load tests
cd tests/performance
make test-load USERS=100 DURATION=10m

# Stress testing
make test-stress USERS=500 DURATION=5m

# Volume testing
make test-volume ARTICLES=10000
```

#### 2. Capacity Planning
```python
# Calculate required capacity based on growth projections
def calculate_capacity_requirements(current_load, growth_rate, time_horizon):
    """Calculate future capacity requirements."""
    future_load = current_load * (1 + growth_rate) ** time_horizon
    safety_margin = 1.2  # 20% safety margin
    return future_load * safety_margin

# Example calculation
current_articles_per_day = 1000
monthly_growth_rate = 0.1  # 10% monthly growth
months_ahead = 12

required_capacity = calculate_capacity_requirements(
    current_articles_per_day, 
    monthly_growth_rate, 
    months_ahead
)
print(f"Required capacity in 12 months: {required_capacity:.0f} articles/day")
```

## Security Operations

### Access Management

#### 1. User Access Review (Monthly)
```bash
# Review Cognito users
aws cognito-idp list-users \
    --user-pool-id us-east-1_XXXXXXXXX \
    --query 'Users[*].{Username:Username,Status:UserStatus,Created:UserCreateDate,LastModified:UserLastModifiedDate}'

# Review user groups and permissions
aws cognito-idp list-groups \
    --user-pool-id us-east-1_XXXXXXXXX
```

#### 2. IAM Role Audit
```bash
# Review Lambda execution roles
aws iam list-roles \
    --path-prefix /sentinel/ \
    --query 'Roles[*].{RoleName:RoleName,Created:CreateDate,LastUsed:RoleLastUsed.LastUsedDate}'

# Check for unused roles
aws iam generate-service-last-accessed-details \
    --arn arn:aws:iam::123456789012:role/sentinel-lambda-execution-role
```

### Security Monitoring

#### 1. CloudTrail Analysis
```bash
# Monitor API calls for suspicious activity
aws logs filter-log-events \
    --log-group-name CloudTrail/SentinelAPILogs \
    --filter-pattern '{ $.errorCode = "AccessDenied" || $.errorCode = "UnauthorizedOperation" }' \
    --start-time $(date -d '24 hours ago' +%s)000
```

#### 2. VPC Flow Logs
```bash
# Analyze network traffic patterns
aws logs filter-log-events \
    --log-group-name /aws/vpc/flowlogs \
    --filter-pattern '[version, account, eni, source, destination, srcport, destport="443", protocol="6", packets, bytes, windowstart, windowend, action="REJECT"]'
```

### Vulnerability Management

#### 1. Dependency Scanning
```bash
# Scan Python dependencies for vulnerabilities
pip-audit --requirement requirements.txt --format json

# Scan Node.js dependencies
cd web && npm audit --audit-level moderate
```

#### 2. Infrastructure Security
```bash
# Run security scans on Terraform code
tfsec infra/

# Check for security misconfigurations
checkov -d infra/ --framework terraform
```

## Incident Response

### Incident Classification

#### Severity Levels

**Critical (P0)**
- Complete system outage
- Data breach or security incident
- Data corruption or loss
- **Response Time**: Immediate (< 15 minutes)
- **Escalation**: On-call engineer + management

**High (P1)**
- Partial system outage affecting multiple users
- Performance degradation > 50%
- Failed backups or security alerts
- **Response Time**: < 1 hour
- **Escalation**: On-call engineer

**Medium (P2)**
- Single component failure with workaround
- Performance degradation < 50%
- Non-critical feature unavailable
- **Response Time**: < 4 hours
- **Escalation**: During business hours

**Low (P3)**
- Minor issues with minimal impact
- Cosmetic or usability issues
- Enhancement requests
- **Response Time**: < 24 hours
- **Escalation**: Normal support queue

### Incident Response Procedures

#### 1. Initial Response (First 15 Minutes)
```bash
# Immediate assessment
./scripts/incident-response.sh --assess

# Check system status
curl -f https://sentinel.company.com/api/v1/health

# Review recent deployments
aws lambda list-functions \
    --query 'Functions[?starts_with(FunctionName, `sentinel`)].{Name:FunctionName,LastModified:LastModified}' \
    --output table
```

#### 2. Communication Protocol
1. **Create Incident**: Log incident in ticketing system
2. **Notify Stakeholders**: Send initial notification
3. **Status Updates**: Provide updates every 30 minutes
4. **Resolution Notice**: Confirm resolution and impact

#### 3. Post-Incident Review
- **Root Cause Analysis**: Identify underlying cause
- **Timeline Documentation**: Create detailed incident timeline
- **Action Items**: Define preventive measures
- **Process Improvements**: Update procedures based on lessons learned

### Runbook Templates

#### Database Incident Response
```bash
#!/bin/bash
# Database incident response template

echo "=== Database Incident Response ==="
echo "1. Check database connectivity"
aws dynamodb describe-table --table-name sentinel-articles-prod

echo "2. Check for throttling"
aws cloudwatch get-metric-statistics \
    --namespace AWS/DynamoDB \
    --metric-name ThrottledRequests \
    --dimensions Name=TableName,Value=sentinel-articles-prod \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Sum

echo "3. Check capacity utilization"
# Add capacity check commands here
```

## Change Management

### Deployment Procedures

#### 1. Pre-Deployment Checklist
- [ ] Code review completed and approved
- [ ] Unit tests passing (>95% coverage)
- [ ] Integration tests passing
- [ ] Security scan completed
- [ ] Performance impact assessed
- [ ] Rollback plan prepared
- [ ] Stakeholders notified

#### 2. Deployment Process
```bash
# 1. Deploy to staging environment
./scripts/deploy.sh -e staging

# 2. Run validation tests
./scripts/validate-deployment.sh -e staging

# 3. Deploy to production (with approval)
./scripts/deploy.sh -e prod

# 4. Validate production deployment
./scripts/validate-deployment.sh -e prod

# 5. Monitor for issues
./scripts/monitor-deployment.sh --duration 30m
```

#### 3. Rollback Procedures
```bash
# Emergency rollback
./scripts/rollback.sh -e prod --to-version previous

# Validate rollback
./scripts/validate-deployment.sh -e prod
```

### Configuration Changes

#### 1. RSS Feed Updates
```bash
# Update feed configuration
vim config/feeds.yaml

# Validate configuration
python3 scripts/validate-config.py --config config/feeds.yaml

# Deploy configuration
./scripts/configure-feeds.sh -e prod -f
```

#### 2. Keyword Updates
```bash
# Update keywords
vim config/keywords.yaml

# Test keyword matching
python3 scripts/test-keyword-matching.py -c config/keywords.yaml -t

# Deploy keywords
./scripts/deploy-keywords.sh -e prod
```

## Cost Optimization

### Cost Monitoring

#### 1. Daily Cost Review
```bash
# Check daily costs
aws ce get-cost-and-usage \
    --time-period Start=$(date -d '1 day ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
    --granularity DAILY \
    --metrics BlendedCost \
    --group-by Type=DIMENSION,Key=SERVICE
```

#### 2. Resource Utilization Analysis
```bash
# Lambda utilization
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Duration \
    --dimensions Name=FunctionName,Value=sentinel-feed-parser-prod \
    --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 86400 \
    --statistics Average

# DynamoDB utilization
aws cloudwatch get-metric-statistics \
    --namespace AWS/DynamoDB \
    --metric-name ConsumedReadCapacityUnits \
    --dimensions Name=TableName,Value=sentinel-articles-prod \
    --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 86400 \
    --statistics Average
```

### Optimization Strategies

#### 1. Right-Sizing Resources
- **Lambda Functions**: Optimize memory allocation based on actual usage
- **DynamoDB**: Use on-demand billing for variable workloads
- **S3**: Implement lifecycle policies for cost-effective storage
- **OpenSearch**: Right-size capacity units based on usage patterns

#### 2. Reserved Capacity
```bash
# Purchase DynamoDB reserved capacity for predictable workloads
aws dynamodb purchase-reserved-capacity-offerings \
    --reserved-capacity-offerings-id 12345678-1234-1234-1234-123456789012
```

#### 3. Data Lifecycle Management
```bash
# Implement S3 lifecycle policies
aws s3api put-bucket-lifecycle-configuration \
    --bucket sentinel-content-prod \
    --lifecycle-configuration '{
      "Rules": [
        {
          "ID": "ArchiveOldContent",
          "Status": "Enabled",
          "Filter": {"Prefix": "articles/"},
          "Transitions": [
            {
              "Days": 30,
              "StorageClass": "STANDARD_IA"
            },
            {
              "Days": 90,
              "StorageClass": "GLACIER"
            }
          ]
        }
      ]
    }'
```

---

This operations runbook should be regularly updated based on operational experience and system changes. Keep it accessible to all operations team members and ensure procedures are tested regularly.