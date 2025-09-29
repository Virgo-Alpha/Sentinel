# Sentinel Troubleshooting Guide

This comprehensive troubleshooting guide helps administrators and users diagnose and resolve common issues with the Sentinel Cybersecurity Triage System.

## Table of Contents

1. [System Health Monitoring](#system-health-monitoring)
2. [Infrastructure Issues](#infrastructure-issues)
3. [Feed Processing Problems](#feed-processing-problems)
4. [Performance Issues](#performance-issues)
5. [Authentication and Access](#authentication-and-access)
6. [Data Processing Errors](#data-processing-errors)
7. [Web Application Issues](#web-application-issues)
8. [Integration Problems](#integration-problems)
9. [Monitoring and Alerting](#monitoring-and-alerting)
10. [Emergency Procedures](#emergency-procedures)

## System Health Monitoring

### Health Check Dashboard

Access the system health dashboard to get an overview of all components:

```bash
# Check overall system status
curl -H "Authorization: Bearer $API_TOKEN" \
     https://sentinel.company.com/api/v1/health

# Expected response
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "database": "healthy",
    "feeds": "healthy", 
    "processing": "healthy",
    "web_app": "healthy"
  },
  "metrics": {
    "articles_processed_24h": 1247,
    "feeds_active": 21,
    "processing_latency_avg": "2.3s",
    "error_rate": "0.2%"
  }
}
```

### Key Health Indicators

#### 1. Feed Processing Status
Monitor RSS feed ingestion and processing:

```bash
# Check feed processing status
aws dynamodb scan \
    --table-name sentinel-feeds-prod \
    --projection-expression "feed_id, #name, #status, last_processed, error_count" \
    --expression-attribute-names '{"#name": "name", "#status": "status"}'
```

**Healthy Indicators:**
- All feeds showing `status: "active"`
- `last_processed` within expected intervals
- `error_count` low or zero
- Processing latency under 5 minutes

**Warning Signs:**
- Feeds with `status: "error"` or `status: "disabled"`
- `last_processed` timestamps older than 2x fetch interval
- High `error_count` values
- Processing latency over 10 minutes

#### 2. Lambda Function Health
Monitor Lambda function performance and errors:

```bash
# Check Lambda function metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Errors \
    --dimensions Name=FunctionName,Value=sentinel-feed-parser-prod \
    --start-time 2024-01-15T00:00:00Z \
    --end-time 2024-01-15T23:59:59Z \
    --period 3600 \
    --statistics Sum
```

**Key Metrics to Monitor:**
- **Error Rate**: Should be < 1%
- **Duration**: Should be within timeout limits
- **Throttles**: Should be zero or minimal
- **Concurrent Executions**: Should not hit limits

#### 3. Database Performance
Monitor DynamoDB table performance:

```bash
# Check DynamoDB metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/DynamoDB \
    --metric-name ThrottledRequests \
    --dimensions Name=TableName,Value=sentinel-articles-prod \
    --start-time 2024-01-15T00:00:00Z \
    --end-time 2024-01-15T23:59:59Z \
    --period 300 \
    --statistics Sum
```

**Performance Indicators:**
- **Read/Write Capacity**: Utilization under 80%
- **Throttled Requests**: Should be zero
- **System Errors**: Should be minimal
- **Latency**: P99 under 100ms for reads, 50ms for writes

## Infrastructure Issues

### AWS Service Connectivity

#### 1. VPC Endpoint Issues

**Problem**: Lambda functions cannot access AWS services
**Symptoms**:
- Timeout errors in Lambda logs
- "Unable to connect to endpoint" errors
- Intermittent service failures

**Diagnosis**:
```bash
# Check VPC endpoints
aws ec2 describe-vpc-endpoints \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'VpcEndpoints[*].{Service:ServiceName,State:State,RouteTableIds:RouteTableIds}'

# Verify security groups
aws ec2 describe-security-groups \
    --group-ids $LAMBDA_SECURITY_GROUP_ID \
    --query 'SecurityGroups[*].{GroupId:GroupId,IpPermissions:IpPermissions}'
```

**Solutions**:
1. **Verify VPC Endpoints**: Ensure endpoints exist for required services (DynamoDB, S3, etc.)
2. **Check Route Tables**: Verify route tables are associated with VPC endpoints
3. **Security Groups**: Ensure security groups allow HTTPS (443) outbound traffic
4. **NACLs**: Verify Network ACLs don't block required traffic

#### 2. IAM Permission Issues

**Problem**: Access denied errors for AWS services
**Symptoms**:
- "AccessDenied" errors in CloudWatch logs
- Lambda functions failing with permission errors
- Unable to read/write to DynamoDB or S3

**Diagnosis**:
```bash
# Check Lambda execution role
aws iam get-role --role-name sentinel-lambda-execution-role

# List attached policies
aws iam list-attached-role-policies --role-name sentinel-lambda-execution-role

# Simulate policy permissions
aws iam simulate-principal-policy \
    --policy-source-arn arn:aws:iam::123456789012:role/sentinel-lambda-execution-role \
    --action-names dynamodb:PutItem s3:GetObject \
    --resource-arns "*"
```

**Solutions**:
1. **Review IAM Policies**: Ensure all required permissions are granted
2. **Check Resource ARNs**: Verify policies reference correct resource ARNs
3. **Cross-Account Access**: Verify cross-account roles if applicable
4. **Service-Linked Roles**: Ensure service-linked roles exist for AWS services

#### 3. Resource Limits and Quotas

**Problem**: Service limits preventing normal operation
**Symptoms**:
- "LimitExceededException" errors
- Throttling in CloudWatch metrics
- Failed resource creation

**Diagnosis**:
```bash
# Check service quotas
aws service-quotas list-service-quotas \
    --service-code lambda \
    --query 'Quotas[?QuotaName==`Concurrent executions`]'

# Check current usage
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name ConcurrentExecutions \
    --start-time 2024-01-15T00:00:00Z \
    --end-time 2024-01-15T23:59:59Z \
    --period 300 \
    --statistics Maximum
```

**Solutions**:
1. **Request Quota Increases**: Submit AWS support requests for higher limits
2. **Optimize Resource Usage**: Reduce concurrent executions or resource consumption
3. **Implement Backoff**: Add exponential backoff for retries
4. **Load Balancing**: Distribute load across multiple regions if applicable

### Terraform State Issues

#### 1. State Lock Problems

**Problem**: Terraform operations fail due to state lock
**Symptoms**:
- "Error acquiring the state lock" messages
- Terraform operations hanging indefinitely
- Multiple users unable to deploy

**Diagnosis**:
```bash
# Check DynamoDB lock table
aws dynamodb scan \
    --table-name terraform-state-locks \
    --projection-expression "LockID, Info"
```

**Solutions**:
```bash
# Force unlock (use with caution)
terraform force-unlock <lock-id>

# Wait for automatic expiration (usually 15 minutes)
# Or coordinate with team members to ensure no active operations
```

#### 2. State Corruption

**Problem**: Terraform state file is corrupted or inconsistent
**Symptoms**:
- Resources exist in AWS but not in state
- Terraform wants to recreate existing resources
- State file errors during operations

**Solutions**:
```bash
# Import existing resources
terraform import aws_dynamodb_table.articles sentinel-articles-prod

# Refresh state from actual infrastructure
terraform refresh

# Restore from backup (if available)
aws s3 cp s3://terraform-state-bucket/backups/terraform.tfstate.backup ./terraform.tfstate
```

## Feed Processing Problems

### RSS Feed Connectivity Issues

#### 1. Feed URL Accessibility

**Problem**: RSS feeds are not accessible or returning errors
**Symptoms**:
- HTTP 404, 403, or 500 errors in logs
- Empty or malformed feed content
- Timeout errors during feed fetching

**Diagnosis**:
```bash
# Test feed accessibility
curl -I "https://www.cisa.gov/cybersecurity-advisories/rss.xml"

# Check feed content
curl -s "https://www.cisa.gov/cybersecurity-advisories/rss.xml" | head -20

# Validate XML structure
curl -s "https://www.cisa.gov/cybersecurity-advisories/rss.xml" | xmllint --format -
```

**Solutions**:
1. **Update Feed URLs**: Check with feed providers for URL changes
2. **Add User-Agent**: Some feeds require proper User-Agent headers
3. **Handle Redirects**: Ensure HTTP redirects are followed
4. **Implement Retry Logic**: Add exponential backoff for temporary failures

#### 2. Feed Format Issues

**Problem**: RSS feeds have unexpected format or structure
**Symptoms**:
- Parsing errors in Lambda logs
- Missing article content or metadata
- Incorrect date parsing

**Diagnosis**:
```python
# Test feed parsing
import feedparser

feed_url = "https://example.com/feed.xml"
feed = feedparser.parse(feed_url)

print(f"Feed title: {feed.feed.title}")
print(f"Entries: {len(feed.entries)}")
print(f"Bozo (malformed): {feed.bozo}")

if feed.entries:
    entry = feed.entries[0]
    print(f"Entry title: {entry.title}")
    print(f"Entry link: {entry.link}")
    print(f"Entry published: {entry.published}")
```

**Solutions**:
1. **Update Parser Logic**: Modify parsing code to handle new formats
2. **Add Format Detection**: Implement automatic format detection
3. **Fallback Parsing**: Use alternative parsing methods for malformed feeds
4. **Contact Feed Providers**: Report format issues to feed maintainers

### Processing Pipeline Failures

#### 1. Lambda Function Timeouts

**Problem**: Lambda functions timing out during processing
**Symptoms**:
- "Task timed out" errors in CloudWatch logs
- Incomplete article processing
- Articles stuck in processing state

**Diagnosis**:
```bash
# Check Lambda timeout configuration
aws lambda get-function-configuration \
    --function-name sentinel-feed-parser-prod \
    --query 'Timeout'

# Review CloudWatch logs for timeout patterns
aws logs filter-log-events \
    --log-group-name /aws/lambda/sentinel-feed-parser-prod \
    --filter-pattern "Task timed out"
```

**Solutions**:
1. **Increase Timeout**: Extend Lambda timeout limits (max 15 minutes)
2. **Optimize Code**: Improve processing efficiency and reduce execution time
3. **Batch Processing**: Process articles in smaller batches
4. **Async Processing**: Use Step Functions for long-running workflows

#### 2. Memory Issues

**Problem**: Lambda functions running out of memory
**Symptoms**:
- "Runtime exited with error: signal: killed" errors
- Memory usage approaching configured limits
- Inconsistent processing failures

**Diagnosis**:
```bash
# Check memory configuration and usage
aws logs filter-log-events \
    --log-group-name /aws/lambda/sentinel-feed-parser-prod \
    --filter-pattern "REPORT" \
    --limit 10
```

**Solutions**:
1. **Increase Memory**: Allocate more memory to Lambda functions
2. **Optimize Memory Usage**: Reduce memory footprint in code
3. **Process in Chunks**: Break large datasets into smaller chunks
4. **Use Streaming**: Stream large files instead of loading into memory

### Data Quality Issues

#### 1. Duplicate Articles

**Problem**: Same articles being processed multiple times
**Symptoms**:
- Duplicate entries in database
- Inflated article counts
- Deduplication not working properly

**Diagnosis**:
```sql
-- Check for duplicates in DynamoDB
aws dynamodb scan \
    --table-name sentinel-articles-prod \
    --filter-expression "attribute_exists(duplicate_of)" \
    --projection-expression "article_id, title, duplicate_of"
```

**Solutions**:
1. **Improve Deduplication**: Enhance similarity detection algorithms
2. **Better Hashing**: Use more robust content hashing methods
3. **URL Normalization**: Normalize URLs before comparison
4. **Manual Review**: Implement manual duplicate review process

#### 2. Incorrect Relevancy Scoring

**Problem**: Articles receiving incorrect relevancy scores
**Symptoms**:
- Obviously relevant articles scored low
- Irrelevant articles scored high
- Inconsistent scoring patterns

**Diagnosis**:
```python
# Test relevancy scoring
from src.lambda_tools.relevancy_evaluator import RelevancyEvaluator

evaluator = RelevancyEvaluator()
test_content = "Microsoft Azure vulnerability affects authentication"

result = evaluator.evaluate_relevancy(test_content)
print(f"Relevancy score: {result['relevancy_score']}")
print(f"Reasoning: {result['reasoning']}")
```

**Solutions**:
1. **Update Keywords**: Review and update keyword configurations
2. **Retrain Models**: Update AI models with new training data
3. **Adjust Thresholds**: Fine-tune relevancy score thresholds
4. **Human Feedback**: Incorporate analyst feedback into scoring

## Performance Issues

### Slow Query Performance

#### 1. Database Query Optimization

**Problem**: Slow database queries affecting system performance
**Symptoms**:
- High query latency in CloudWatch metrics
- Timeout errors in application logs
- Poor user experience in web interface

**Diagnosis**:
```bash
# Check DynamoDB performance metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/DynamoDB \
    --metric-name SuccessfulRequestLatency \
    --dimensions Name=TableName,Value=sentinel-articles-prod Name=Operation,Value=Query \
    --start-time 2024-01-15T00:00:00Z \
    --end-time 2024-01-15T23:59:59Z \
    --period 300 \
    --statistics Average,Maximum
```

**Solutions**:
1. **Add Indexes**: Create Global Secondary Indexes for common query patterns
2. **Optimize Queries**: Use efficient query patterns and avoid scans
3. **Implement Caching**: Add caching layer for frequently accessed data
4. **Partition Data**: Distribute data across multiple partitions

#### 2. OpenSearch Performance

**Problem**: Slow search queries in OpenSearch Serverless
**Symptoms**:
- Long search response times
- Search timeouts
- High CPU usage in OpenSearch metrics

**Diagnosis**:
```bash
# Check OpenSearch cluster health
curl -X GET "https://search-sentinel-prod.us-east-1.es.amazonaws.com/_cluster/health"

# Check index statistics
curl -X GET "https://search-sentinel-prod.us-east-1.es.amazonaws.com/_stats"
```

**Solutions**:
1. **Optimize Queries**: Use more efficient search queries and filters
2. **Index Optimization**: Optimize index mappings and settings
3. **Increase Capacity**: Scale up OpenSearch Serverless capacity units
4. **Query Caching**: Implement query result caching

### High Resource Utilization

#### 1. Lambda Concurrency Issues

**Problem**: High Lambda concurrency causing throttling
**Symptoms**:
- Throttling errors in CloudWatch metrics
- Delayed processing of articles
- Increased error rates

**Diagnosis**:
```bash
# Check concurrent executions
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name ConcurrentExecutions \
    --start-time 2024-01-15T00:00:00Z \
    --end-time 2024-01-15T23:59:59Z \
    --period 300 \
    --statistics Maximum
```

**Solutions**:
1. **Reserved Concurrency**: Set reserved concurrency for critical functions
2. **Provisioned Concurrency**: Use provisioned concurrency for consistent performance
3. **Queue Management**: Implement SQS queues to manage processing load
4. **Load Distribution**: Distribute processing across multiple functions

#### 2. Memory and CPU Optimization

**Problem**: High memory or CPU usage affecting performance
**Symptoms**:
- Slow response times
- Function timeouts
- High AWS costs

**Solutions**:
1. **Profile Code**: Use profiling tools to identify bottlenecks
2. **Optimize Algorithms**: Improve algorithm efficiency
3. **Reduce Memory Footprint**: Optimize data structures and memory usage
4. **Right-Size Resources**: Adjust Lambda memory allocation based on usage

## Authentication and Access

### Cognito Authentication Issues

#### 1. User Login Problems

**Problem**: Users cannot log in to the web application
**Symptoms**:
- Authentication failures
- "Invalid credentials" errors
- MFA issues

**Diagnosis**:
```bash
# Check Cognito user pool status
aws cognito-idp describe-user-pool --user-pool-id us-east-1_XXXXXXXXX

# Check user status
aws cognito-idp admin-get-user \
    --user-pool-id us-east-1_XXXXXXXXX \
    --username user@company.com
```

**Solutions**:
1. **Reset Password**: Reset user password through Cognito console
2. **Check User Status**: Verify user account is confirmed and enabled
3. **MFA Configuration**: Verify MFA settings and backup codes
4. **App Client Settings**: Check app client configuration and callbacks

#### 2. Permission and Role Issues

**Problem**: Users have incorrect permissions or cannot access features
**Symptoms**:
- "Access denied" errors in web application
- Missing menu items or features
- API authorization failures

**Diagnosis**:
```bash
# Check user groups
aws cognito-idp admin-list-groups-for-user \
    --user-pool-id us-east-1_XXXXXXXXX \
    --username user@company.com

# Verify group permissions
aws cognito-idp get-group \
    --group-name SecurityAnalysts \
    --user-pool-id us-east-1_XXXXXXXXX
```

**Solutions**:
1. **Update User Groups**: Add users to appropriate groups
2. **Review Group Permissions**: Verify group has correct permissions
3. **Check IAM Roles**: Ensure Cognito groups map to correct IAM roles
4. **Clear Token Cache**: Have users clear browser cache and re-login

### API Authentication

#### 1. API Key Issues

**Problem**: API calls failing with authentication errors
**Symptoms**:
- 401 Unauthorized responses
- "Invalid API key" errors
- Intermittent authentication failures

**Diagnosis**:
```bash
# Test API key
curl -H "Authorization: Bearer $API_KEY" \
     https://api.sentinel.company.com/v1/health

# Check API Gateway logs
aws logs filter-log-events \
    --log-group-name API-Gateway-Execution-Logs_xxxxxxxxxx/prod \
    --filter-pattern "401"
```

**Solutions**:
1. **Regenerate API Keys**: Create new API keys if compromised
2. **Check Key Expiration**: Verify API keys haven't expired
3. **Update Usage Plans**: Ensure API keys are associated with usage plans
4. **Review Throttling**: Check if requests are being throttled

## Data Processing Errors

### Content Processing Failures

#### 1. HTML Parsing Issues

**Problem**: Errors parsing HTML content from articles
**Symptoms**:
- Malformed text extraction
- Missing article content
- Encoding issues

**Diagnosis**:
```python
# Test HTML parsing
from bs4 import BeautifulSoup
import requests

url = "https://example.com/article"
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

print(f"Title: {soup.title.string if soup.title else 'No title'}")
print(f"Encoding: {response.encoding}")
print(f"Content length: {len(response.content)}")
```

**Solutions**:
1. **Update Parser**: Use more robust HTML parsing libraries
2. **Handle Encoding**: Properly detect and handle character encoding
3. **Fallback Methods**: Implement fallback parsing methods
4. **Content Validation**: Add validation for extracted content

#### 2. Keyword Matching Errors

**Problem**: Keyword matching not working correctly
**Symptoms**:
- Missing obvious keyword matches
- False positive matches
- Inconsistent matching results

**Diagnosis**:
```bash
# Test keyword matching
python3 scripts/test-keyword-matching.py \
    -c config/keywords.yaml \
    -t "Microsoft Azure vulnerability affects authentication"
```

**Solutions**:
1. **Update Keywords**: Review and update keyword configurations
2. **Adjust Fuzzy Matching**: Fine-tune fuzzy matching parameters
3. **Add Variations**: Include more keyword variations and synonyms
4. **Context Analysis**: Improve context-based matching

### AI/ML Processing Issues

#### 1. Bedrock API Errors

**Problem**: AWS Bedrock API calls failing
**Symptoms**:
- "ModelNotFound" errors
- Rate limiting errors
- Timeout errors

**Diagnosis**:
```bash
# Check Bedrock model availability
aws bedrock list-foundation-models \
    --region us-east-1 \
    --query 'modelSummaries[?modelId==`anthropic.claude-3-sonnet-20240229-v1:0`]'

# Test model invocation
aws bedrock-runtime invoke-model \
    --model-id anthropic.claude-3-sonnet-20240229-v1:0 \
    --body '{"messages":[{"role":"user","content":"Hello"}],"max_tokens":100}' \
    --cli-binary-format raw-in-base64-out \
    /tmp/response.json
```

**Solutions**:
1. **Check Model Availability**: Verify model is available in your region
2. **Request Access**: Request access to specific models if needed
3. **Implement Retry Logic**: Add exponential backoff for rate limits
4. **Use Alternative Models**: Fallback to different models if primary fails

#### 2. Relevancy Assessment Issues

**Problem**: AI relevancy assessment producing poor results
**Symptoms**:
- Inconsistent relevancy scores
- Obviously relevant articles scored low
- Poor quality reasoning

**Solutions**:
1. **Improve Prompts**: Refine AI prompts for better results
2. **Add Examples**: Include few-shot examples in prompts
3. **Validate Responses**: Add validation for AI responses
4. **Human Feedback**: Incorporate human feedback to improve results

## Web Application Issues

### Frontend Problems

#### 1. Page Loading Issues

**Problem**: Web pages not loading or loading slowly
**Symptoms**:
- Blank pages or loading spinners
- JavaScript errors in browser console
- Slow page load times

**Diagnosis**:
```bash
# Check Amplify deployment status
aws amplify get-app --app-id d1234567890123

# Check CloudFront distribution
aws cloudfront get-distribution --id EDFDVBD6EXAMPLE
```

**Solutions**:
1. **Clear Cache**: Clear browser cache and CloudFront cache
2. **Check Deployment**: Verify latest deployment was successful
3. **Review Logs**: Check browser console and network logs
4. **CDN Issues**: Verify CloudFront distribution is healthy

#### 2. API Connectivity Issues

**Problem**: Frontend cannot connect to backend APIs
**Symptoms**:
- API call failures
- CORS errors in browser console
- Authentication errors

**Diagnosis**:
```bash
# Test API connectivity
curl -X GET https://api.sentinel.company.com/v1/health

# Check CORS configuration
aws apigateway get-resource \
    --rest-api-id your-api-id \
    --resource-id your-resource-id
```

**Solutions**:
1. **CORS Configuration**: Update CORS settings in API Gateway
2. **API Gateway Health**: Verify API Gateway is healthy and deployed
3. **Authentication**: Check authentication tokens and headers
4. **Network Issues**: Verify network connectivity and DNS resolution

### Backend API Issues

#### 1. Lambda Function Errors

**Problem**: API endpoints returning errors
**Symptoms**:
- 500 Internal Server Error responses
- Lambda function errors in CloudWatch
- Timeout errors

**Diagnosis**:
```bash
# Check Lambda function logs
aws logs tail /aws/lambda/sentinel-api-prod --follow

# Test Lambda function directly
aws lambda invoke \
    --function-name sentinel-api-prod \
    --payload '{"httpMethod":"GET","path":"/health"}' \
    /tmp/response.json
```

**Solutions**:
1. **Review Code**: Check Lambda function code for errors
2. **Update Dependencies**: Ensure all dependencies are up to date
3. **Increase Resources**: Allocate more memory or timeout to functions
4. **Error Handling**: Improve error handling and logging

#### 2. Database Connection Issues

**Problem**: API cannot connect to database
**Symptoms**:
- Database connection timeouts
- "Unable to connect" errors
- Intermittent API failures

**Solutions**:
1. **Connection Pooling**: Implement proper database connection pooling
2. **VPC Configuration**: Verify VPC and security group settings
3. **Database Health**: Check DynamoDB table status and capacity
4. **Retry Logic**: Implement retry logic for transient failures

## Integration Problems

### SIEM Integration Issues

#### 1. Data Export Failures

**Problem**: Data not being exported to SIEM systems
**Symptoms**:
- Missing security events in SIEM
- Export job failures
- Authentication errors

**Diagnosis**:
```bash
# Check export job status
aws logs filter-log-events \
    --log-group-name /aws/lambda/sentinel-siem-export \
    --filter-pattern "ERROR"

# Test SIEM connectivity
curl -X POST https://siem.company.com/api/events \
     -H "Authorization: Bearer $SIEM_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"test": "connectivity"}'
```

**Solutions**:
1. **Update Credentials**: Refresh SIEM authentication credentials
2. **Check Endpoints**: Verify SIEM endpoint URLs and availability
3. **Data Format**: Ensure data format matches SIEM expectations
4. **Network Access**: Verify network connectivity to SIEM systems

### Notification Issues

#### 1. Email Notifications Not Sent

**Problem**: Email notifications not being delivered
**Symptoms**:
- Missing critical alert emails
- SES bounce notifications
- SMTP errors in logs

**Diagnosis**:
```bash
# Check SES sending statistics
aws ses get-send-statistics

# Check bounce and complaint rates
aws ses get-reputation \
    --identity security-alerts@company.com
```

**Solutions**:
1. **Verify SES Configuration**: Check SES domain and email verification
2. **Review Bounce Rate**: Ensure bounce rate is below SES limits
3. **Update Email Lists**: Remove invalid email addresses
4. **Check Spam Filters**: Verify emails aren't being filtered as spam

#### 2. Slack Integration Problems

**Problem**: Slack notifications not working
**Symptoms**:
- Missing Slack messages
- Webhook errors in logs
- Authentication failures

**Diagnosis**:
```bash
# Test Slack webhook
curl -X POST https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK \
     -H "Content-Type: application/json" \
     -d '{"text": "Test message from Sentinel"}'
```

**Solutions**:
1. **Update Webhook URL**: Refresh Slack webhook URL if expired
2. **Check Permissions**: Verify Slack app has required permissions
3. **Message Format**: Ensure message format is valid JSON
4. **Rate Limiting**: Implement rate limiting for Slack messages

## Monitoring and Alerting

### CloudWatch Issues

#### 1. Missing Metrics

**Problem**: Expected metrics not appearing in CloudWatch
**Symptoms**:
- Empty CloudWatch dashboards
- Missing custom metrics
- Incomplete monitoring data

**Solutions**:
1. **Check Metric Names**: Verify metric names and namespaces are correct
2. **IAM Permissions**: Ensure Lambda functions can write to CloudWatch
3. **Metric Filters**: Verify log metric filters are configured correctly
4. **Custom Metrics**: Check custom metric publishing code

#### 2. Alert Configuration Issues

**Problem**: CloudWatch alarms not triggering correctly
**Symptoms**:
- Missing alert notifications
- False positive alerts
- Delayed alert notifications

**Solutions**:
1. **Review Thresholds**: Adjust alarm thresholds based on actual metrics
2. **Check SNS Topics**: Verify SNS topics and subscriptions are configured
3. **Test Notifications**: Send test notifications to verify delivery
4. **Alarm Actions**: Ensure alarm actions are properly configured

### X-Ray Tracing Issues

#### 1. Missing Traces

**Problem**: X-Ray traces not appearing or incomplete
**Symptoms**:
- Empty X-Ray service map
- Missing trace segments
- Incomplete request tracing

**Solutions**:
1. **Enable Tracing**: Ensure X-Ray tracing is enabled on Lambda functions
2. **IAM Permissions**: Verify functions have X-Ray write permissions
3. **Sampling Rules**: Check X-Ray sampling rules configuration
4. **SDK Integration**: Ensure X-Ray SDK is properly integrated in code

## Emergency Procedures

### System Outage Response

#### 1. Immediate Assessment

When a system outage is detected:

1. **Check System Status**:
   ```bash
   # Quick health check
   curl -f https://sentinel.company.com/api/v1/health || echo "System DOWN"
   
   # Check critical components
   aws dynamodb describe-table --table-name sentinel-articles-prod
   aws lambda get-function --function-name sentinel-feed-parser-prod
   ```

2. **Identify Scope**:
   - Determine which components are affected
   - Check if issue is regional or global
   - Assess impact on users and data processing

3. **Escalation**:
   - Notify on-call engineer immediately
   - Create incident in ticketing system
   - Inform stakeholders of outage

#### 2. Incident Response

**Communication Plan**:
1. **Internal Notification**: Alert security team and management
2. **User Communication**: Update status page and send notifications
3. **Stakeholder Updates**: Regular updates to affected parties
4. **Post-Incident**: Conduct post-mortem and lessons learned

**Recovery Procedures**:
1. **Rollback**: Revert to last known good configuration if needed
2. **Service Restart**: Restart affected services and components
3. **Data Recovery**: Restore from backups if data corruption occurred
4. **Validation**: Verify system functionality before declaring recovery

### Data Recovery Procedures

#### 1. Database Recovery

**DynamoDB Point-in-Time Recovery**:
```bash
# Restore table to specific point in time
aws dynamodb restore-table-to-point-in-time \
    --source-table-name sentinel-articles-prod \
    --target-table-name sentinel-articles-restored \
    --restore-date-time 2024-01-15T10:00:00Z
```

**S3 Data Recovery**:
```bash
# Restore from versioned S3 bucket
aws s3api list-object-versions \
    --bucket sentinel-content-prod \
    --prefix articles/

# Restore specific version
aws s3api get-object \
    --bucket sentinel-content-prod \
    --key articles/article-123.json \
    --version-id version-id \
    restored-article.json
```

#### 2. Configuration Recovery

**Terraform State Recovery**:
```bash
# Restore from backup
aws s3 cp s3://terraform-state-backup/terraform.tfstate.backup \
          terraform.tfstate

# Refresh state from actual infrastructure
terraform refresh
```

### Contact Information

#### Emergency Contacts
- **On-Call Engineer**: +1-555-0123 (24/7)
- **Security Team Lead**: security-lead@company.com
- **Infrastructure Team**: infrastructure@company.com
- **AWS Support**: Enterprise support case

#### Escalation Matrix
1. **Level 1**: On-call engineer (immediate response)
2. **Level 2**: Team lead (within 30 minutes)
3. **Level 3**: Management (within 1 hour)
4. **Level 4**: Executive team (for major incidents)

#### External Support
- **AWS Support**: Enterprise support for infrastructure issues
- **Vendor Support**: Contact information for third-party services
- **Security Vendors**: Emergency contacts for security tools

---

This troubleshooting guide should be regularly updated based on new issues encountered and lessons learned from incident responses. Keep it accessible to all team members and ensure contact information remains current.