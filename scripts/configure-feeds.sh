#!/bin/bash

# RSS Feed Configuration Script for Sentinel
# Loads all RSS feed configurations and target keywords into the system

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$PROJECT_ROOT/config"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/feed_configuration_$TIMESTAMP.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
ENVIRONMENT="dev"
DRY_RUN=false
FORCE_UPDATE=false
VERBOSE=false
VALIDATE_FEEDS=true

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Configure RSS feeds and keywords for Sentinel

OPTIONS:
    -e, --environment ENV    Target environment (dev|staging|prod) [default: dev]
    -d, --dry-run           Show what would be configured without making changes
    -f, --force             Force update existing configurations
    -s, --skip-validation   Skip RSS feed URL validation
    -v, --verbose           Enable verbose output
    -h, --help              Show this help message

EXAMPLES:
    $0                      # Configure feeds for dev environment
    $0 -e prod -f           # Force update feeds in production
    $0 -d -v                # Dry run with verbose output
    $0 -s                   # Skip feed validation (faster)

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -f|--force)
            FORCE_UPDATE=true
            shift
            ;;
        -s|--skip-validation)
            VALIDATE_FEEDS=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Create log directory
mkdir -p "$LOG_DIR"
mkdir -p "$CONFIG_DIR"

print_status "Starting RSS feed configuration for environment: $ENVIRONMENT"

# Function to get Terraform outputs
get_terraform_outputs() {
    cd "$PROJECT_ROOT/infra"
    
    if ! terraform output -json > /tmp/tf_outputs.json 2>/dev/null; then
        print_error "Failed to get Terraform outputs. Ensure infrastructure is deployed."
        return 1
    fi
    
    # Extract table names
    FEEDS_TABLE=$(jq -r '.feeds_table_name.value // empty' /tmp/tf_outputs.json)
    ARTICLES_TABLE=$(jq -r '.articles_table_name.value // empty' /tmp/tf_outputs.json)
    
    if [[ -z "$FEEDS_TABLE" ]]; then
        print_error "Feeds table name not found in Terraform outputs"
        return 1
    fi
    
    print_status "Using DynamoDB table: $FEEDS_TABLE"
    return 0
}

# Function to validate RSS feed URL
validate_feed_url() {
    local url="$1"
    local name="$2"
    
    if [[ "$VALIDATE_FEEDS" == "false" ]]; then
        return 0
    fi
    
    print_status "  Validating feed: $name"
    
    # Check if URL is accessible
    if curl -s --head --max-time 10 "$url" | head -n 1 | grep -q "200 OK"; then
        if [[ "$VERBOSE" == "true" ]]; then
            print_status "    ✓ Feed URL accessible: $url"
        fi
        return 0
    else
        print_warning "    ✗ Feed URL not accessible: $url"
        return 1
    fi
}

# Function to create RSS feed configuration
create_feed_config() {
    cat > "$CONFIG_DIR/rss_feeds.json" << 'EOF'
{
  "feeds": [
    {
      "feed_id": "cisa-advisories",
      "name": "CISA Cybersecurity Advisories",
      "url": "https://www.cisa.gov/cybersecurity-advisories/rss.xml",
      "category": "advisories",
      "source_type": "government",
      "priority": "high",
      "enabled": true,
      "fetch_interval_minutes": 15,
      "description": "Cybersecurity advisories from the Cybersecurity and Infrastructure Security Agency",
      "tags": ["government", "advisories", "critical-infrastructure"]
    },
    {
      "feed_id": "ncsc-uk-advisories",
      "name": "NCSC UK Advisories",
      "url": "https://www.ncsc.gov.uk/api/1/services/v1/all-rss-feed.xml",
      "category": "advisories",
      "source_type": "government",
      "priority": "high",
      "enabled": true,
      "fetch_interval_minutes": 30,
      "description": "Security advisories from the UK National Cyber Security Centre",
      "tags": ["government", "uk", "advisories"]
    },
    {
      "feed_id": "anssi-advisories",
      "name": "ANSSI Security Advisories",
      "url": "https://www.cert.ssi.gouv.fr/feed/",
      "category": "advisories",
      "source_type": "government",
      "priority": "high",
      "enabled": true,
      "fetch_interval_minutes": 30,
      "description": "Security advisories from the French National Cybersecurity Agency",
      "tags": ["government", "france", "advisories"]
    },
    {
      "feed_id": "cert-eu",
      "name": "CERT-EU Security Bulletins",
      "url": "https://cert.europa.eu/cert/newsletter/en/latest_SecurityBulletins_.rss",
      "category": "advisories",
      "source_type": "government",
      "priority": "high",
      "enabled": true,
      "fetch_interval_minutes": 60,
      "description": "Security bulletins from the Computer Emergency Response Team for EU institutions",
      "tags": ["government", "eu", "bulletins"]
    },
    {
      "feed_id": "us-cert-alerts",
      "name": "US-CERT Alerts",
      "url": "https://us-cert.cisa.gov/ncas/alerts.xml",
      "category": "alerts",
      "source_type": "government",
      "priority": "critical",
      "enabled": true,
      "fetch_interval_minutes": 15,
      "description": "Critical alerts from US Computer Emergency Readiness Team",
      "tags": ["government", "alerts", "critical"]
    },
    {
      "feed_id": "microsoft-security",
      "name": "Microsoft Security Response Center",
      "url": "https://msrc.microsoft.com/blog/feed",
      "category": "updates",
      "source_type": "vendor",
      "priority": "high",
      "enabled": true,
      "fetch_interval_minutes": 30,
      "description": "Security updates and advisories from Microsoft",
      "tags": ["vendor", "microsoft", "updates"]
    },
    {
      "feed_id": "google-tag",
      "name": "Google Threat Analysis Group",
      "url": "https://blog.google/threat-analysis-group/rss/",
      "category": "threat-intel",
      "source_type": "vendor",
      "priority": "high",
      "enabled": true,
      "fetch_interval_minutes": 60,
      "description": "Threat intelligence from Google's Threat Analysis Group",
      "tags": ["vendor", "google", "threat-intel"]
    },
    {
      "feed_id": "apple-security",
      "name": "Apple Security Updates",
      "url": "https://support.apple.com/en-us/HT201222/rss",
      "category": "updates",
      "source_type": "vendor",
      "priority": "medium",
      "enabled": true,
      "fetch_interval_minutes": 60,
      "description": "Security updates from Apple",
      "tags": ["vendor", "apple", "updates"]
    },
    {
      "feed_id": "adobe-security",
      "name": "Adobe Security Bulletins",
      "url": "https://helpx.adobe.com/security.rss",
      "category": "updates",
      "source_type": "vendor",
      "priority": "medium",
      "enabled": true,
      "fetch_interval_minutes": 60,
      "description": "Security bulletins from Adobe",
      "tags": ["vendor", "adobe", "updates"]
    },
    {
      "feed_id": "oracle-security",
      "name": "Oracle Security Alerts",
      "url": "https://blogs.oracle.com/security/rss",
      "category": "updates",
      "source_type": "vendor",
      "priority": "medium",
      "enabled": true,
      "fetch_interval_minutes": 60,
      "description": "Security alerts and updates from Oracle",
      "tags": ["vendor", "oracle", "updates"]
    },
    {
      "feed_id": "fortinet-blog",
      "name": "Fortinet Security Blog",
      "url": "https://www.fortinet.com/blog/rss.xml",
      "category": "threat-intel",
      "source_type": "security-vendor",
      "priority": "medium",
      "enabled": true,
      "fetch_interval_minutes": 120,
      "description": "Threat intelligence and security research from Fortinet",
      "tags": ["security-vendor", "fortinet", "threat-intel"]
    },
    {
      "feed_id": "palo-alto-unit42",
      "name": "Palo Alto Networks Unit 42",
      "url": "https://unit42.paloaltonetworks.com/feed/",
      "category": "threat-intel",
      "source_type": "security-vendor",
      "priority": "high",
      "enabled": true,
      "fetch_interval_minutes": 60,
      "description": "Threat intelligence research from Palo Alto Networks Unit 42",
      "tags": ["security-vendor", "palo-alto", "threat-intel"]
    },
    {
      "feed_id": "crowdstrike-blog",
      "name": "CrowdStrike Blog",
      "url": "https://www.crowdstrike.com/blog/feed/",
      "category": "threat-intel",
      "source_type": "security-vendor",
      "priority": "high",
      "enabled": true,
      "fetch_interval_minutes": 60,
      "description": "Threat intelligence and security research from CrowdStrike",
      "tags": ["security-vendor", "crowdstrike", "threat-intel"]
    },
    {
      "feed_id": "fireeye-blog",
      "name": "FireEye Threat Research",
      "url": "https://www.fireeye.com/blog/feed",
      "category": "threat-intel",
      "source_type": "security-vendor",
      "priority": "high",
      "enabled": true,
      "fetch_interval_minutes": 60,
      "description": "Threat research and intelligence from FireEye",
      "tags": ["security-vendor", "fireeye", "threat-intel"]
    },
    {
      "feed_id": "symantec-blog",
      "name": "Symantec Security Response",
      "url": "https://symantec-enterprise-blogs.security.com/blogs/feed",
      "category": "threat-intel",
      "source_type": "security-vendor",
      "priority": "medium",
      "enabled": true,
      "fetch_interval_minutes": 120,
      "description": "Security research and threat intelligence from Symantec",
      "tags": ["security-vendor", "symantec", "threat-intel"]
    },
    {
      "feed_id": "nvd-vulnerabilities",
      "name": "National Vulnerability Database",
      "url": "https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml",
      "category": "vulnerabilities",
      "source_type": "database",
      "priority": "high",
      "enabled": true,
      "fetch_interval_minutes": 30,
      "description": "Vulnerability information from the National Vulnerability Database",
      "tags": ["database", "vulnerabilities", "cve"]
    },
    {
      "feed_id": "cve-details",
      "name": "CVE Details",
      "url": "https://www.cvedetails.com/rss-feeds/",
      "category": "vulnerabilities",
      "source_type": "database",
      "priority": "medium",
      "enabled": true,
      "fetch_interval_minutes": 60,
      "description": "Detailed vulnerability information and statistics",
      "tags": ["database", "vulnerabilities", "cve"]
    },
    {
      "feed_id": "sans-isc",
      "name": "SANS Internet Storm Center",
      "url": "https://isc.sans.edu/rssfeed.xml",
      "category": "threat-intel",
      "source_type": "research",
      "priority": "medium",
      "enabled": true,
      "fetch_interval_minutes": 60,
      "description": "Threat intelligence and security research from SANS ISC",
      "tags": ["research", "sans", "threat-intel"]
    },
    {
      "feed_id": "krebs-security",
      "name": "Krebs on Security",
      "url": "https://krebsonsecurity.com/feed/",
      "category": "news",
      "source_type": "news",
      "priority": "medium",
      "enabled": true,
      "fetch_interval_minutes": 120,
      "description": "Cybersecurity news and investigative reporting",
      "tags": ["news", "investigative", "cybercrime"]
    },
    {
      "feed_id": "schneier-security",
      "name": "Schneier on Security",
      "url": "https://www.schneier.com/blog/atom.xml",
      "category": "news",
      "source_type": "news",
      "priority": "low",
      "enabled": true,
      "fetch_interval_minutes": 240,
      "description": "Security analysis and commentary from Bruce Schneier",
      "tags": ["news", "analysis", "commentary"]
    },
    {
      "feed_id": "dark-reading",
      "name": "Dark Reading",
      "url": "https://www.darkreading.com/rss_simple.asp",
      "category": "news",
      "source_type": "news",
      "priority": "low",
      "enabled": true,
      "fetch_interval_minutes": 180,
      "description": "Cybersecurity news and analysis",
      "tags": ["news", "analysis", "industry"]
    }
  ]
}
EOF
    
    print_success "RSS feed configuration created: $CONFIG_DIR/rss_feeds.json"
}

# Function to create keyword configuration
create_keyword_config() {
    cat > "$CONFIG_DIR/target_keywords.json" << 'EOF'
{
  "keyword_categories": {
    "cloud_platforms": {
      "description": "Cloud service providers and platforms",
      "priority": "high",
      "keywords": [
        {
          "keyword": "AWS",
          "aliases": ["Amazon Web Services", "Amazon AWS"],
          "weight": 1.0,
          "context_required": false
        },
        {
          "keyword": "Azure",
          "aliases": ["Microsoft Azure", "Azure Cloud"],
          "weight": 1.0,
          "context_required": false
        },
        {
          "keyword": "Google Cloud",
          "aliases": ["GCP", "Google Cloud Platform"],
          "weight": 1.0,
          "context_required": false
        },
        {
          "keyword": "Microsoft 365",
          "aliases": ["Office 365", "O365", "M365"],
          "weight": 0.9,
          "context_required": false
        },
        {
          "keyword": "Salesforce",
          "aliases": ["SFDC"],
          "weight": 0.8,
          "context_required": false
        },
        {
          "keyword": "ServiceNow",
          "aliases": [],
          "weight": 0.7,
          "context_required": false
        }
      ]
    },
    "security_vendors": {
      "description": "Cybersecurity product vendors",
      "priority": "high",
      "keywords": [
        {
          "keyword": "Fortinet",
          "aliases": ["FortiGate", "FortiOS", "FortiAnalyzer"],
          "weight": 1.0,
          "context_required": false
        },
        {
          "keyword": "SentinelOne",
          "aliases": ["Sentinel One"],
          "weight": 1.0,
          "context_required": false
        },
        {
          "keyword": "CrowdStrike",
          "aliases": ["Falcon", "CrowdStrike Falcon"],
          "weight": 1.0,
          "context_required": false
        },
        {
          "keyword": "Palo Alto",
          "aliases": ["Palo Alto Networks", "PAN", "Prisma", "Cortex"],
          "weight": 1.0,
          "context_required": false
        },
        {
          "keyword": "Cisco",
          "aliases": ["Cisco Systems", "ASA", "Firepower"],
          "weight": 0.9,
          "context_required": false
        },
        {
          "keyword": "Symantec",
          "aliases": ["Norton", "Broadcom"],
          "weight": 0.8,
          "context_required": false
        },
        {
          "keyword": "McAfee",
          "aliases": ["Trellix"],
          "weight": 0.8,
          "context_required": false
        },
        {
          "keyword": "Trend Micro",
          "aliases": [],
          "weight": 0.8,
          "context_required": false
        },
        {
          "keyword": "Check Point",
          "aliases": ["CheckPoint"],
          "weight": 0.8,
          "context_required": false
        }
      ]
    },
    "threat_intelligence": {
      "description": "Threat intelligence and security terms",
      "priority": "critical",
      "keywords": [
        {
          "keyword": "vulnerability",
          "aliases": ["vuln", "security flaw"],
          "weight": 1.0,
          "context_required": false
        },
        {
          "keyword": "CVE",
          "aliases": ["Common Vulnerabilities and Exposures"],
          "weight": 1.0,
          "context_required": false
        },
        {
          "keyword": "exploit",
          "aliases": ["exploitation", "exploiting"],
          "weight": 1.0,
          "context_required": false
        },
        {
          "keyword": "malware",
          "aliases": ["malicious software"],
          "weight": 1.0,
          "context_required": false
        },
        {
          "keyword": "ransomware",
          "aliases": ["ransom", "crypto-locker"],
          "weight": 1.0,
          "context_required": false
        },
        {
          "keyword": "phishing",
          "aliases": ["spear phishing", "phish"],
          "weight": 0.9,
          "context_required": false
        },
        {
          "keyword": "zero-day",
          "aliases": ["0-day", "zero day"],
          "weight": 1.0,
          "context_required": false
        },
        {
          "keyword": "threat actor",
          "aliases": ["attacker", "adversary"],
          "weight": 0.8,
          "context_required": true
        },
        {
          "keyword": "APT",
          "aliases": ["Advanced Persistent Threat"],
          "weight": 0.9,
          "context_required": false
        },
        {
          "keyword": "botnet",
          "aliases": ["bot network"],
          "weight": 0.8,
          "context_required": false
        }
      ]
    },
    "enterprise_tools": {
      "description": "Enterprise software and tools",
      "priority": "medium",
      "keywords": [
        {
          "keyword": "Active Directory",
          "aliases": ["AD", "LDAP"],
          "weight": 0.9,
          "context_required": false
        },
        {
          "keyword": "Exchange",
          "aliases": ["Exchange Server", "Microsoft Exchange"],
          "weight": 0.8,
          "context_required": false
        },
        {
          "keyword": "SharePoint",
          "aliases": ["SharePoint Server"],
          "weight": 0.7,
          "context_required": false
        },
        {
          "keyword": "Teams",
          "aliases": ["Microsoft Teams"],
          "weight": 0.6,
          "context_required": true
        },
        {
          "keyword": "Outlook",
          "aliases": ["Microsoft Outlook"],
          "weight": 0.6,
          "context_required": true
        },
        {
          "keyword": "VMware",
          "aliases": ["vSphere", "ESXi", "vCenter"],
          "weight": 0.8,
          "context_required": false
        },
        {
          "keyword": "Citrix",
          "aliases": ["XenApp", "XenDesktop"],
          "weight": 0.7,
          "context_required": false
        },
        {
          "keyword": "Oracle",
          "aliases": ["Oracle Database"],
          "weight": 0.6,
          "context_required": true
        },
        {
          "keyword": "SAP",
          "aliases": ["SAP HANA"],
          "weight": 0.7,
          "context_required": false
        }
      ]
    },
    "attack_techniques": {
      "description": "Attack techniques and methods",
      "priority": "high",
      "keywords": [
        {
          "keyword": "lateral movement",
          "aliases": ["lateral propagation"],
          "weight": 0.9,
          "context_required": false
        },
        {
          "keyword": "privilege escalation",
          "aliases": ["privesc", "elevation"],
          "weight": 0.9,
          "context_required": false
        },
        {
          "keyword": "persistence",
          "aliases": ["persistent access"],
          "weight": 0.8,
          "context_required": true
        },
        {
          "keyword": "defense evasion",
          "aliases": ["evasion technique"],
          "weight": 0.8,
          "context_required": false
        },
        {
          "keyword": "credential access",
          "aliases": ["credential theft", "password dumping"],
          "weight": 0.9,
          "context_required": false
        },
        {
          "keyword": "command and control",
          "aliases": ["C2", "C&C", "command control"],
          "weight": 0.8,
          "context_required": false
        },
        {
          "keyword": "data exfiltration",
          "aliases": ["data theft", "exfiltration"],
          "weight": 0.9,
          "context_required": false
        },
        {
          "keyword": "SQL injection",
          "aliases": ["SQLi", "SQL attack"],
          "weight": 0.8,
          "context_required": false
        },
        {
          "keyword": "cross-site scripting",
          "aliases": ["XSS"],
          "weight": 0.7,
          "context_required": false
        },
        {
          "keyword": "remote code execution",
          "aliases": ["RCE", "code execution"],
          "weight": 0.9,
          "context_required": false
        }
      ]
    }
  },
  "matching_rules": {
    "fuzzy_matching": {
      "enabled": true,
      "threshold": 0.8,
      "max_distance": 2
    },
    "context_analysis": {
      "enabled": true,
      "window_size": 50,
      "required_context_keywords": ["security", "vulnerability", "attack", "threat", "breach"]
    },
    "scoring": {
      "exact_match_bonus": 1.0,
      "alias_match_bonus": 0.8,
      "fuzzy_match_penalty": 0.2,
      "context_bonus": 0.3,
      "frequency_weight": 0.1
    }
  }
}
EOF
    
    print_success "Keyword configuration created: $CONFIG_DIR/target_keywords.json"
}

# Function to load feeds into DynamoDB
load_feeds_to_dynamodb() {
    local feeds_file="$CONFIG_DIR/rss_feeds.json"
    
    if [[ ! -f "$feeds_file" ]]; then
        print_error "RSS feeds configuration file not found: $feeds_file"
        return 1
    fi
    
    print_status "Loading RSS feeds into DynamoDB table: $FEEDS_TABLE"
    
    local feed_count=0
    local success_count=0
    local error_count=0
    
    # Process each feed
    while IFS= read -r feed; do
        ((feed_count++))
        
        local feed_id=$(echo "$feed" | jq -r '.feed_id')
        local name=$(echo "$feed" | jq -r '.name')
        local url=$(echo "$feed" | jq -r '.url')
        
        print_status "  Processing feed: $name ($feed_id)"
        
        # Validate feed URL if requested
        if [[ "$VALIDATE_FEEDS" == "true" ]]; then
            if ! validate_feed_url "$url" "$name"; then
                print_warning "    Skipping feed due to validation failure: $name"
                ((error_count++))
                continue
            fi
        fi
        
        # Check if feed already exists (unless force update)
        if [[ "$FORCE_UPDATE" == "false" ]]; then
            if aws dynamodb get-item \
                --table-name "$FEEDS_TABLE" \
                --key "{\"feed_id\": {\"S\": \"$feed_id\"}}" \
                --query 'Item' \
                --output text &> /dev/null; then
                
                print_status "    Feed already exists, skipping: $feed_id"
                ((success_count++))
                continue
            fi
        fi
        
        # Prepare DynamoDB item
        local dynamodb_item=$(echo "$feed" | jq '{
            feed_id: {S: .feed_id},
            name: {S: .name},
            url: {S: .url},
            category: {S: .category},
            source_type: {S: .source_type},
            priority: {S: .priority},
            enabled: {BOOL: .enabled},
            fetch_interval_minutes: {N: (.fetch_interval_minutes | tostring)},
            description: {S: .description},
            tags: {SS: .tags},
            created_at: {S: "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"},
            updated_at: {S: "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"},
            last_fetched: {S: "never"},
            fetch_count: {N: "0"},
            error_count: {N: "0"},
            status: {S: "active"}
        }')
        
        # Insert into DynamoDB
        if [[ "$DRY_RUN" == "true" ]]; then
            print_status "    [DRY RUN] Would insert feed: $feed_id"
            ((success_count++))
        else
            if aws dynamodb put-item \
                --table-name "$FEEDS_TABLE" \
                --item "$dynamodb_item" &> /dev/null; then
                
                print_success "    ✓ Feed loaded: $feed_id"
                ((success_count++))
            else
                print_error "    ✗ Failed to load feed: $feed_id"
                ((error_count++))
            fi
        fi
        
    done < <(jq -c '.feeds[]' "$feeds_file")
    
    print_status ""
    print_status "Feed loading summary:"
    print_status "  Total feeds: $feed_count"
    print_status "  Successfully loaded: $success_count"
    print_status "  Errors: $error_count"
    
    if [[ $error_count -gt 0 ]]; then
        print_warning "Some feeds failed to load. Check the log for details."
        return 1
    fi
    
    return 0
}

# Function to load keywords into configuration
load_keywords_config() {
    local keywords_file="$CONFIG_DIR/target_keywords.json"
    
    if [[ ! -f "$keywords_file" ]]; then
        print_error "Keywords configuration file not found: $keywords_file"
        return 1
    fi
    
    print_status "Loading keyword configuration..."
    
    # For now, we'll store keywords in S3 for Lambda functions to access
    # In a full implementation, this might go into DynamoDB or Parameter Store
    
    cd "$PROJECT_ROOT/infra"
    local outputs=$(terraform output -json 2>/dev/null || echo '{}')
    local config_bucket=$(echo "$outputs" | jq -r '.artifacts_bucket_name.value // empty')
    
    if [[ -z "$config_bucket" ]]; then
        print_warning "Configuration bucket not found, storing keywords locally only"
        return 0
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_status "  [DRY RUN] Would upload keywords to S3: $config_bucket"
    else
        if aws s3 cp "$keywords_file" "s3://$config_bucket/config/target_keywords.json"; then
            print_success "  ✓ Keywords uploaded to S3: $config_bucket/config/target_keywords.json"
        else
            print_error "  ✗ Failed to upload keywords to S3"
            return 1
        fi
    fi
    
    # Also store in Parameter Store for easy access
    local param_name="/sentinel/$ENVIRONMENT/keywords"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_status "  [DRY RUN] Would store keywords in Parameter Store: $param_name"
    else
        if aws ssm put-parameter \
            --name "$param_name" \
            --value "file://$keywords_file" \
            --type "String" \
            --overwrite &> /dev/null; then
            
            print_success "  ✓ Keywords stored in Parameter Store: $param_name"
        else
            print_error "  ✗ Failed to store keywords in Parameter Store"
            return 1
        fi
    fi
    
    return 0
}

# Function to test feed parsing
test_feed_parsing() {
    print_status "Testing RSS feed parsing..."
    
    local test_feeds=(
        "https://www.cisa.gov/cybersecurity-advisories/rss.xml"
        "https://www.ncsc.gov.uk/api/1/services/v1/all-rss-feed.xml"
        "https://msrc.microsoft.com/blog/feed"
    )
    
    local success_count=0
    local total_count=${#test_feeds[@]}
    
    for feed_url in "${test_feeds[@]}"; do
        print_status "  Testing feed: $feed_url"
        
        # Use Python to parse the feed
        local test_result=$(python3 -c "
import feedparser
import sys
try:
    feed = feedparser.parse('$feed_url')
    if feed.bozo:
        print('MALFORMED')
    elif len(feed.entries) > 0:
        print(f'SUCCESS:{len(feed.entries)}')
    else:
        print('EMPTY')
except Exception as e:
    print(f'ERROR:{e}')
" 2>/dev/null)
        
        case "$test_result" in
            SUCCESS:*)
                local entry_count=$(echo "$test_result" | cut -d':' -f2)
                print_success "    ✓ Feed parsed successfully ($entry_count entries)"
                ((success_count++))
                ;;
            MALFORMED)
                print_warning "    ✗ Feed is malformed but parseable"
                ;;
            EMPTY)
                print_warning "    ✗ Feed is empty"
                ;;
            ERROR:*)
                local error_msg=$(echo "$test_result" | cut -d':' -f2-)
                print_error "    ✗ Feed parsing failed: $error_msg"
                ;;
            *)
                print_error "    ✗ Unknown parsing result: $test_result"
                ;;
        esac
    done
    
    print_status ""
    print_status "Feed parsing test summary:"
    print_status "  Total feeds tested: $total_count"
    print_status "  Successfully parsed: $success_count"
    
    if [[ $success_count -eq $total_count ]]; then
        print_success "All test feeds parsed successfully"
        return 0
    else
        print_warning "Some test feeds failed to parse"
        return 1
    fi
}

# Function to validate keyword matching
test_keyword_matching() {
    print_status "Testing keyword matching functionality..."
    
    local test_content="Microsoft has released a critical security update for Azure Active Directory to address a vulnerability (CVE-2024-1234) that could allow remote code execution. The vulnerability affects Exchange Online and SharePoint services."
    
    local keywords_file="$CONFIG_DIR/target_keywords.json"
    
    if [[ ! -f "$keywords_file" ]]; then
        print_warning "Keywords file not found, skipping keyword matching test"
        return 0
    fi
    
    # Simple keyword matching test using jq and grep
    local matched_keywords=()
    
    # Extract all keywords from the configuration
    while IFS= read -r keyword_data; do
        local keyword=$(echo "$keyword_data" | jq -r '.keyword')
        local aliases=$(echo "$keyword_data" | jq -r '.aliases[]?' 2>/dev/null || echo "")
        
        # Check for exact matches
        if echo "$test_content" | grep -qi "$keyword"; then
            matched_keywords+=("$keyword")
        fi
        
        # Check aliases
        if [[ -n "$aliases" ]]; then
            for alias in $aliases; do
                if echo "$test_content" | grep -qi "$alias"; then
                    matched_keywords+=("$keyword (alias: $alias)")
                    break
                fi
            done
        fi
        
    done < <(jq -c '.keyword_categories[].keywords[]' "$keywords_file")
    
    print_status "  Test content: ${test_content:0:100}..."
    print_status "  Matched keywords:"
    
    if [[ ${#matched_keywords[@]} -gt 0 ]]; then
        for match in "${matched_keywords[@]}"; do
            print_status "    ✓ $match"
        done
        print_success "Keyword matching test passed (${#matched_keywords[@]} matches)"
        return 0
    else
        print_warning "No keywords matched in test content"
        return 1
    fi
}

# Function to generate configuration report
generate_config_report() {
    print_status "Generating configuration report..."
    
    local report_file="$LOG_DIR/feed-config-report-$ENVIRONMENT-$TIMESTAMP.json"
    
    # Count feeds by category
    local feeds_file="$CONFIG_DIR/rss_feeds.json"
    local keywords_file="$CONFIG_DIR/target_keywords.json"
    
    local total_feeds=0
    local enabled_feeds=0
    local total_keywords=0
    
    if [[ -f "$feeds_file" ]]; then
        total_feeds=$(jq '.feeds | length' "$feeds_file")
        enabled_feeds=$(jq '[.feeds[] | select(.enabled == true)] | length' "$feeds_file")
    fi
    
    if [[ -f "$keywords_file" ]]; then
        total_keywords=$(jq '[.keyword_categories[].keywords[]] | length' "$keywords_file")
    fi
    
    # Create report
    cat > "$report_file" << EOF
{
    "configuration_report": {
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "environment": "$ENVIRONMENT",
        "dry_run": $DRY_RUN,
        "force_update": $FORCE_UPDATE,
        "validate_feeds": $VALIDATE_FEEDS
    },
    "feeds_summary": {
        "total_feeds": $total_feeds,
        "enabled_feeds": $enabled_feeds,
        "disabled_feeds": $((total_feeds - enabled_feeds)),
        "categories": $(jq '[.feeds[].category] | unique' "$feeds_file" 2>/dev/null || echo '[]')
    },
    "keywords_summary": {
        "total_keywords": $total_keywords,
        "categories": $(jq '[.keyword_categories | keys[]]' "$keywords_file" 2>/dev/null || echo '[]')
    },
    "database_info": {
        "feeds_table": "$FEEDS_TABLE",
        "articles_table": "$ARTICLES_TABLE"
    }
}
EOF
    
    print_success "Configuration report generated: $report_file"
}

# Main function
main() {
    print_status "RSS Feed and Keyword Configuration"
    print_status "=================================="
    print_status "Environment: $ENVIRONMENT"
    print_status "Dry Run: $DRY_RUN"
    print_status "Force Update: $FORCE_UPDATE"
    print_status "Validate Feeds: $VALIDATE_FEEDS"
    print_status ""
    
    # Get Terraform outputs
    if ! get_terraform_outputs; then
        print_error "Failed to get infrastructure information"
        exit 1
    fi
    
    # Create configuration files
    print_status "Creating configuration files..."
    create_feed_config
    create_keyword_config
    
    # Load feeds into DynamoDB
    if ! load_feeds_to_dynamodb; then
        print_error "Failed to load RSS feeds"
        exit 1
    fi
    
    # Load keywords configuration
    if ! load_keywords_config; then
        print_error "Failed to load keywords configuration"
        exit 1
    fi
    
    # Test feed parsing
    if [[ "$VALIDATE_FEEDS" == "true" ]]; then
        test_feed_parsing
    fi
    
    # Test keyword matching
    test_keyword_matching
    
    # Generate configuration report
    generate_config_report
    
    print_status ""
    print_status "================================"
    print_status "CONFIGURATION SUMMARY"
    print_status "================================"
    print_status "Environment: $ENVIRONMENT"
    print_status "RSS Feeds Configured: $(jq '.feeds | length' "$CONFIG_DIR/rss_feeds.json")"
    print_status "Keywords Configured: $(jq '[.keyword_categories[].keywords[]] | length' "$CONFIG_DIR/target_keywords.json")"
    print_status "DynamoDB Table: $FEEDS_TABLE"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_status "Mode: DRY RUN (no changes made)"
    else
        print_success "Configuration completed successfully!"
    fi
    
    print_status ""
    print_status "Next steps:"
    print_status "  1. Verify feed processing: Check CloudWatch logs for feed ingestion"
    print_status "  2. Test keyword matching: Run end-to-end validation"
    print_status "  3. Monitor system: Check dashboards for feed processing metrics"
    
    print_status ""
    print_status "Log file: $LOG_FILE"
    print_status "Configuration files: $CONFIG_DIR/"
}

# Trap for cleanup
trap 'print_error "Configuration interrupted"; exit 1' INT TERM

# Run main function
main "$@"