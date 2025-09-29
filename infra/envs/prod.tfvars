# Production Environment Configuration for Sentinel

# Environment settings
environment = "prod"
project_name = "sentinel"

# AWS Configuration
aws_region = "us-east-1"
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

# Network Configuration
vpc_cidr = "10.1.0.0/16"
private_subnet_cidrs = ["10.1.1.0/24", "10.1.2.0/24", "10.1.3.0/24"]
public_subnet_cidrs = ["10.1.101.0/24", "10.1.102.0/24", "10.1.103.0/24"]

# Feature Flags
enable_agents = true           # Use Bedrock AgentCore in production
enable_amplify = true          # Enable web application
enable_opensearch = true       # Enable semantic deduplication

# DynamoDB Configuration
dynamodb_billing_mode = "PROVISIONED"  # Predictable costs for production
dynamodb_point_in_time_recovery = true # Enable PITR for production
dynamodb_read_capacity = 100
dynamodb_write_capacity = 100
dynamodb_auto_scaling = true

# Lambda Configuration
lambda_memory_size = 1024      # Higher memory for production performance
lambda_timeout = 900           # 15 minutes for complex operations
lambda_reserved_concurrency = 100  # Higher concurrency for production

# S3 Configuration
s3_versioning_enabled = true   # Enable versioning for production
s3_lifecycle_enabled = true    # Enable lifecycle management
s3_transition_days = 30        # Transition to IA after 30 days
s3_expiration_days = 2555      # Keep for 7 years (compliance)
s3_cross_region_replication = true  # Enable replication for DR

# OpenSearch Serverless Configuration
opensearch_capacity_units = 10  # Higher capacity for production

# EventBridge Configuration
eventbridge_schedule_enabled = true
feed_processing_schedule = "rate(15 minutes)"  # Process feeds every 15 minutes

# SQS Configuration
sqs_visibility_timeout = 900   # 15 minutes
sqs_message_retention = 1209600  # 14 days
sqs_max_receive_count = 5      # More retries for production

# SNS Configuration
sns_email_notifications = [
  "security-team@company.com",
  "ops-team@company.com",
  "alerts@company.com"
]

# Cognito Configuration
cognito_password_policy = {
  minimum_length = 12
  require_lowercase = true
  require_numbers = true
  require_symbols = true
  require_uppercase = true
}
cognito_mfa_enabled = true
cognito_advanced_security = true

# API Gateway Configuration
api_gateway_throttle_rate_limit = 10000
api_gateway_throttle_burst_limit = 20000

# CloudWatch Configuration
cloudwatch_log_retention_days = 365  # 1 year retention for production
cloudwatch_detailed_monitoring = true

# X-Ray Configuration
xray_tracing_enabled = true
xray_sampling_rate = 0.05  # 5% sampling for production (cost optimization)

# Auto Scaling Configuration
auto_scaling_enabled = true
auto_scaling_target_utilization = 70
auto_scaling_scale_in_cooldown = 300
auto_scaling_scale_out_cooldown = 60

# Backup Configuration
backup_enabled = true
backup_retention_days = 35
backup_schedule = "cron(0 2 * * ? *)"  # Daily at 2 AM

# Cost Optimization
cost_optimization_enabled = true
unused_resource_cleanup = true
scheduled_scaling = true

# Security Configuration
encryption_at_rest = true
encryption_in_transit = true
enable_waf = true
waf_rate_limit = 2000

# Monitoring and Alerting
monitoring_enabled = true
alerting_enabled = true
alert_endpoints = [
  "arn:aws:sns:us-east-1:123456789012:security-alerts",
  "arn:aws:sns:us-east-1:123456789012:ops-alerts"
]

# High Availability Configuration
multi_az_deployment = true
cross_region_backup = true
disaster_recovery_enabled = true

# Performance Configuration
performance_config = {
  max_processing_time_minutes = 5
  deduplication_threshold = 0.85
  relevancy_threshold = 0.7
  batch_size = 50
  max_concurrent_executions = 100
}

# Tags
common_tags = {
  Environment = "prod"
  Project = "sentinel"
  Owner = "security-team"
  CostCenter = "security"
  ManagedBy = "terraform"
  Purpose = "cybersecurity-triage"
  Compliance = "required"
  DataClassification = "confidential"
}

# RSS Feed Configuration (All 21 feeds for production)
rss_feeds = [
  # Government and National Agencies
  {
    name = "CISA"
    url = "https://www.cisa.gov/cybersecurity-advisories/rss.xml"
    category = "advisories"
    enabled = true
    fetch_interval = 900  # 15 minutes
  },
  {
    name = "NCSC-UK"
    url = "https://www.ncsc.gov.uk/api/1/services/v1/all-rss-feed.xml"
    category = "advisories"
    enabled = true
    fetch_interval = 900
  },
  {
    name = "ANSSI"
    url = "https://www.cert.ssi.gouv.fr/feed/"
    category = "advisories"
    enabled = true
    fetch_interval = 1800  # 30 minutes
  },
  {
    name = "CERT-EU"
    url = "https://cert.europa.eu/cert/newsletter/en/latest_SecurityBulletins_.rss"
    category = "advisories"
    enabled = true
    fetch_interval = 1800
  },
  {
    name = "US-CERT"
    url = "https://us-cert.cisa.gov/ncas/alerts.xml"
    category = "alerts"
    enabled = true
    fetch_interval = 900
  },
  
  # Technology Vendors
  {
    name = "Microsoft Security"
    url = "https://msrc.microsoft.com/blog/feed"
    category = "updates"
    enabled = true
    fetch_interval = 1800
  },
  {
    name = "Google TAG"
    url = "https://blog.google/threat-analysis-group/rss/"
    category = "threat-intel"
    enabled = true
    fetch_interval = 3600  # 1 hour
  },
  {
    name = "Apple Security"
    url = "https://support.apple.com/en-us/HT201222/rss"
    category = "updates"
    enabled = true
    fetch_interval = 3600
  },
  {
    name = "Adobe Security"
    url = "https://helpx.adobe.com/security.rss"
    category = "updates"
    enabled = true
    fetch_interval = 3600
  },
  {
    name = "Oracle Security"
    url = "https://blogs.oracle.com/security/rss"
    category = "updates"
    enabled = true
    fetch_interval = 3600
  },
  
  # Security Vendors
  {
    name = "Fortinet"
    url = "https://www.fortinet.com/blog/rss.xml"
    category = "threat-intel"
    enabled = true
    fetch_interval = 3600
  },
  {
    name = "Palo Alto Networks"
    url = "https://unit42.paloaltonetworks.com/feed/"
    category = "threat-intel"
    enabled = true
    fetch_interval = 3600
  },
  {
    name = "CrowdStrike"
    url = "https://www.crowdstrike.com/blog/feed/"
    category = "threat-intel"
    enabled = true
    fetch_interval = 3600
  },
  {
    name = "FireEye"
    url = "https://www.fireeye.com/blog/feed"
    category = "threat-intel"
    enabled = true
    fetch_interval = 3600
  },
  {
    name = "Symantec"
    url = "https://symantec-enterprise-blogs.security.com/blogs/feed"
    category = "threat-intel"
    enabled = true
    fetch_interval = 3600
  },
  
  # Vulnerability Databases
  {
    name = "NVD"
    url = "https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml"
    category = "vulnerabilities"
    enabled = true
    fetch_interval = 1800
  },
  {
    name = "CVE Details"
    url = "https://www.cvedetails.com/rss-feeds/"
    category = "vulnerabilities"
    enabled = true
    fetch_interval = 1800
  },
  
  # Industry Sources
  {
    name = "SANS ISC"
    url = "https://isc.sans.edu/rssfeed.xml"
    category = "threat-intel"
    enabled = true
    fetch_interval = 3600
  },
  {
    name = "Krebs on Security"
    url = "https://krebsonsecurity.com/feed/"
    category = "news"
    enabled = true
    fetch_interval = 3600
  },
  {
    name = "Schneier on Security"
    url = "https://www.schneier.com/blog/atom.xml"
    category = "news"
    enabled = true
    fetch_interval = 3600
  },
  {
    name = "Dark Reading"
    url = "https://www.darkreading.com/rss_simple.asp"
    category = "news"
    enabled = true
    fetch_interval = 3600
  }
]

# Comprehensive Keyword Configuration
target_keywords = {
  cloud_platforms = [
    "AWS", "Amazon Web Services", "EC2", "S3", "Lambda", "RDS",
    "Azure", "Microsoft 365", "Office 365", "Exchange Online", "SharePoint Online",
    "Google Cloud", "GCP", "Google Workspace", "Gmail", "Google Drive",
    "Salesforce", "ServiceNow", "Workday", "Box", "Dropbox"
  ]
  
  security_vendors = [
    "Fortinet", "FortiGate", "FortiOS", "SentinelOne", "CrowdStrike", "Falcon",
    "Palo Alto", "Prisma", "Cortex", "Cisco", "ASA", "Firepower",
    "Symantec", "Norton", "McAfee", "Trend Micro", "Check Point",
    "Splunk", "QRadar", "ArcSight", "LogRhythm", "Rapid7"
  ]
  
  threat_intel = [
    "vulnerability", "CVE", "exploit", "malware", "ransomware", "phishing",
    "zero-day", "threat actor", "APT", "botnet", "trojan", "backdoor",
    "spyware", "adware", "rootkit", "keylogger", "worm", "virus",
    "DDoS", "SQL injection", "XSS", "CSRF", "RCE", "privilege escalation"
  ]
  
  enterprise_tools = [
    "Active Directory", "LDAP", "Exchange", "SharePoint", "Teams", "Outlook",
    "VMware", "vSphere", "ESXi", "Citrix", "XenApp", "XenDesktop",
    "Oracle", "SAP", "HANA", "PeopleSoft", "Siebel", "JDE",
    "Salesforce", "ServiceNow", "Jira", "Confluence", "Jenkins"
  ]
  
  attack_techniques = [
    "lateral movement", "persistence", "privilege escalation", "defense evasion",
    "credential access", "discovery", "collection", "exfiltration", "impact",
    "initial access", "execution", "command and control", "C2", "C&C"
  ]
  
  compliance_frameworks = [
    "SOC 2", "ISO 27001", "NIST", "PCI DSS", "HIPAA", "GDPR",
    "CCPA", "SOX", "FISMA", "FedRAMP", "CMMC"
  ]
}

# Production-specific settings
prod_settings = {
  debug_logging = false
  mock_external_apis = false
  skip_email_notifications = false
  enable_test_endpoints = false
  cors_allow_all_origins = false
  strict_security_headers = true
  rate_limiting_enabled = true
  ip_whitelisting_enabled = true
}