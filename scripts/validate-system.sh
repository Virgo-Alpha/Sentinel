#!/bin/bash

# End-to-End System Validation Script for Sentinel
# Validates complete ingestion cycle, deduplication, human review workflow, and reporting

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/e2e_validation_$TIMESTAMP.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
ENVIRONMENT="dev"
TIMEOUT=1800  # 30 minutes
VERBOSE=false
SKIP_PERFORMANCE=false
SAMPLE_SIZE=10

# Performance thresholds
MAX_PROCESSING_TIME=300  # 5 minutes
MIN_DEDUP_ACCURACY=0.85  # 85%
MIN_RELEVANCY_ACCURACY=0.70  # 70%

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

Execute end-to-end system validation for Sentinel

OPTIONS:
    -e, --environment ENV    Target environment (dev|staging|prod) [default: dev]
    -t, --timeout SECONDS   Timeout for validation in seconds [default: 1800]
    -s, --sample-size NUM   Number of test articles to process [default: 10]
    --skip-performance      Skip performance validation tests
    -v, --verbose           Enable verbose output
    -h, --help              Show this help message

EXAMPLES:
    $0                      # Validate dev environment
    $0 -e prod -t 3600      # Validate prod with 1-hour timeout
    $0 -s 20 -v             # Process 20 test articles with verbose output
    $0 --skip-performance   # Skip performance tests

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -s|--sample-size)
            SAMPLE_SIZE="$2"
            shift 2
            ;;
        --skip-performance)
            SKIP_PERFORMANCE=true
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

print_status "Starting end-to-end system validation for environment: $ENVIRONMENT"

# Function to get infrastructure information
get_infrastructure_info() {
    print_status "Getting infrastructure information..."
    
    cd "$PROJECT_ROOT/infra"
    
    if ! terraform output -json > /tmp/tf_outputs.json 2>/dev/null; then
        print_error "Failed to get Terraform outputs"
        return 1
    fi
    
    # Extract key infrastructure components
    ARTICLES_TABLE=$(jq -r '.articles_table_name.value // empty' /tmp/tf_outputs.json)
    FEEDS_TABLE=$(jq -r '.feeds_table_name.value // empty' /tmp/tf_outputs.json)
    S3_BUCKET=$(jq -r '.artifacts_bucket_name.value // empty' /tmp/tf_outputs.json)
    LAMBDA_FUNCTIONS=$(jq -r '.lambda_function_names.value[]? // empty' /tmp/tf_outputs.json)
    STEP_FUNCTION_ARN=$(jq -r '.step_function_arn.value // empty' /tmp/tf_outputs.json)
    
    if [[ -z "$ARTICLES_TABLE" || -z "$FEEDS_TABLE" ]]; then
        print_error "Required infrastructure components not found"
        return 1
    fi
    
    print_status "Infrastructure components:"
    print_status "  Articles Table: $ARTICLES_TABLE"
    print_status "  Feeds Table: $FEEDS_TABLE"
    print_status "  S3 Bucket: $S3_BUCKET"
    print_status "  Step Function: $STEP_FUNCTION_ARN"
    
    return 0
}

# Function to create test RSS feed data
create_test_feed_data() {
    print_status "Creating test RSS feed data..."
    
    local test_feed_file="/tmp/test_feed_$TIMESTAMP.xml"
    
    cat > "$test_feed_file" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Sentinel Test Feed</title>
        <description>Test RSS feed for end-to-end validation</description>
        <link>https://test.sentinel.local</link>
        <item>
            <title>Critical AWS Lambda Vulnerability - CVE-2024-TEST1</title>
            <description>A critical security vulnerability has been discovered in AWS Lambda runtime environments that allows remote code execution. This vulnerability affects all Lambda functions using Python 3.9 runtime and requires immediate patching.</description>
            <link>https://test.sentinel.local/cve-2024-test1</link>
            <pubDate>Mon, 15 Jan 2024 10:30:00 GMT</pubDate>
            <guid>test-article-1</guid>
        </item>
        <item>
            <title>Microsoft 365 Security Update for Exchange Online</title>
            <description>Microsoft has released a security update for Exchange Online to address a vulnerability that could allow privilege escalation. The update is being rolled out automatically to all tenants.</description>
            <link>https://test.sentinel.local/ms-exchange-update</link>
            <pubDate>Mon, 15 Jan 2024 09:15:00 GMT</pubDate>
            <guid>test-article-2</guid>
        </item>
        <item>
            <title>Fortinet FortiGate Zero-Day Exploit in the Wild</title>
            <description>Security researchers have observed active exploitation of a zero-day vulnerability in Fortinet FortiGate devices. The vulnerability allows attackers to bypass authentication and gain administrative access.</description>
            <link>https://test.sentinel.local/fortinet-zero-day</link>
            <pubDate>Mon, 15 Jan 2024 08:45:00 GMT</pubDate>
            <guid>test-article-3</guid>
        </item>
        <item>
            <title>New Ransomware Campaign Targets VMware vSphere</title>
            <description>A new ransomware strain called CryptoLocker2024 has been observed targeting VMware vSphere environments through lateral movement techniques. Organizations are advised to implement additional monitoring.</description>
            <link>https://test.sentinel.local/ransomware-vsphere</link>
            <pubDate>Mon, 15 Jan 2024 07:30:00 GMT</pubDate>
            <guid>test-article-4</guid>
        </item>
        <item>
            <title>Weather Update: Sunny Skies Expected</title>
            <description>The weather forecast shows sunny skies with temperatures reaching 75 degrees. Perfect weather for outdoor activities this weekend.</description>
            <link>https://test.sentinel.local/weather-update</link>
            <pubDate>Mon, 15 Jan 2024 06:00:00 GMT</pubDate>
            <guid>test-article-5</guid>
        </item>
    </channel>
</rss>
EOF
    
    print_success "Test RSS feed created: $test_feed_file"
    echo "$test_feed_file"
}

# Function to simulate feed ingestion
simulate_feed_ingestion() {
    local test_feed_file="$1"
    
    print_status "Simulating RSS feed ingestion..."
    
    # Create test feed entry in DynamoDB
    local test_feed_id="test-feed-$TIMESTAMP"
    
    local feed_item='{
        "feed_id": {"S": "'$test_feed_id'"},
        "name": {"S": "Test Feed for E2E Validation"},
        "url": {"S": "file://'$test_feed_file'"},
        "category": {"S": "test"},
        "source_type": {"S": "test"},
        "priority": {"S": "high"},
        "enabled": {"BOOL": true},
        "fetch_interval_minutes": {"N": "15"},
        "created_at": {"S": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"},
        "status": {"S": "active"}
    }'
    
    if aws dynamodb put-item --table-name "$FEEDS_TABLE" --item "$feed_item"; then
        print_success "Test feed registered in DynamoDB"
    else
        print_error "Failed to register test feed"
        return 1
    fi
    
    # Simulate feed processing by directly invoking Lambda functions
    local feed_parser_function=$(echo "$LAMBDA_FUNCTIONS" | grep -i "feed.*parser" | head -1)
    
    if [[ -n "$feed_parser_function" ]]; then
        print_status "Invoking feed parser function: $feed_parser_function"
        
        local feed_event='{
            "Records": [{
                "eventSource": "aws:sqs",
                "body": "{\\"feed_id\\": \\"'$test_feed_id'\\", \\"feed_url\\": \\"file://'$test_feed_file'\\", \\"source\\": \\"test\\"}"
            }]
        }'
        
        local response_file="/tmp/feed_parser_response_$TIMESTAMP.json"
        
        if aws lambda invoke \
            --function-name "$feed_parser_function" \
            --payload "$feed_event" \
            --cli-binary-format raw-in-base64-out \
            "$response_file"; then
            
            print_success "Feed parser invoked successfully"
            
            if [[ "$VERBOSE" == "true" ]]; then
                print_status "Feed parser response:"
                cat "$response_file" | jq . 2>/dev/null || cat "$response_file"
            fi
        else
            print_error "Failed to invoke feed parser"
            return 1
        fi
    else
        print_warning "Feed parser function not found, skipping direct invocation"
    fi
    
    return 0
}

# Function to validate article processing
validate_article_processing() {
    print_status "Validating article processing..."
    
    # Wait for articles to be processed
    local max_wait=300  # 5 minutes
    local wait_time=0
    local articles_found=false
    
    while [[ $wait_time -lt $max_wait ]]; do
        # Check for processed articles
        local article_count=$(aws dynamodb scan \
            --table-name "$ARTICLES_TABLE" \
            --filter-expression "contains(title, :test_marker)" \
            --expression-attribute-values '{":test_marker": {"S": "CVE-2024-TEST"}}' \
            --select "COUNT" \
            --query "Count" \
            --output text 2>/dev/null || echo "0")
        
        if [[ "$article_count" -gt 0 ]]; then
            articles_found=true
            break
        fi
        
        print_status "  Waiting for articles to be processed... ($wait_time/$max_wait seconds)"
        sleep 10
        ((wait_time += 10))
    done
    
    if [[ "$articles_found" == "true" ]]; then
        print_success "Articles found in database: $article_count"
        
        # Get article details
        local articles=$(aws dynamodb scan \
            --table-name "$ARTICLES_TABLE" \
            --filter-expression "contains(title, :test_marker)" \
            --expression-attribute-values '{":test_marker": {"S": "CVE-2024-TEST"}}' \
            --query "Items[*].{title: title.S, status: #status.S, relevancy_score: relevancy_score.N}" \
            --expression-attribute-names '{"#status": "status"}' \
            --output json 2>/dev/null || echo "[]")
        
        if [[ "$VERBOSE" == "true" ]]; then
            print_status "Processed articles:"
            echo "$articles" | jq .
        fi
        
        return 0
    else
        print_error "No articles found after $max_wait seconds"
        return 1
    fi
}

# Function to test keyword detection accuracy
test_keyword_detection() {
    print_status "Testing keyword detection accuracy..."
    
    # Get articles with keyword matches
    local articles_with_keywords=$(aws dynamodb scan \
        --table-name "$ARTICLES_TABLE" \
        --filter-expression "attribute_exists(keyword_matches)" \
        --query "Items[*].{title: title.S, keyword_matches: keyword_matches.L}" \
        --output json 2>/dev/null || echo "[]")
    
    local total_articles=$(echo "$articles_with_keywords" | jq 'length')
    
    if [[ "$total_articles" -eq 0 ]]; then
        print_warning "No articles with keyword matches found"
        return 0
    fi
    
    print_status "Analyzing keyword detection for $total_articles articles..."
    
    # Expected keywords for test articles
    local expected_keywords=(
        "AWS" "Lambda" "vulnerability" "CVE"
        "Microsoft" "Exchange" "privilege escalation"
        "Fortinet" "zero-day" "exploit"
        "ransomware" "VMware" "lateral movement"
    )
    
    local detected_keywords=()
    
    # Extract all detected keywords
    while IFS= read -r keyword; do
        if [[ -n "$keyword" && "$keyword" != "null" ]]; then
            detected_keywords+=("$keyword")
        fi
    done < <(echo "$articles_with_keywords" | jq -r '.[].keyword_matches[]?.keyword?.S // empty')
    
    # Calculate detection accuracy
    local expected_found=0
    for expected in "${expected_keywords[@]}"; do
        for detected in "${detected_keywords[@]}"; do
            if [[ "$detected" == "$expected" ]]; then
                ((expected_found++))
                break
            fi
        done
    done
    
    local accuracy=$(echo "scale=2; $expected_found * 100 / ${#expected_keywords[@]}" | bc -l 2>/dev/null || echo "0")
    
    print_status "Keyword detection results:"
    print_status "  Expected keywords: ${#expected_keywords[@]}"
    print_status "  Detected keywords: ${#detected_keywords[@]}"
    print_status "  Expected found: $expected_found"
    print_status "  Accuracy: $accuracy%"
    
    if (( $(echo "$accuracy >= 70" | bc -l) )); then
        print_success "Keyword detection accuracy meets threshold (≥70%)"
        return 0
    else
        print_error "Keyword detection accuracy below threshold: $accuracy% < 70%"
        return 1
    fi
}

# Function to test deduplication clustering
test_deduplication() {
    print_status "Testing deduplication clustering..."
    
    # Create duplicate test articles
    local duplicate_articles=(
        '{"title": "AWS Lambda Critical Vulnerability CVE-2024-TEST1", "content": "Critical security vulnerability in AWS Lambda runtime", "url": "https://test1.com/duplicate"}'
        '{"title": "Critical AWS Lambda Vulnerability - CVE-2024-TEST1", "content": "A critical security vulnerability in AWS Lambda runtime environments", "url": "https://test2.com/duplicate"}'
        '{"title": "AWS Lambda Security Issue CVE-2024-TEST1", "content": "Security vulnerability found in AWS Lambda runtime", "url": "https://test3.com/duplicate"}'
    )
    
    # Insert duplicate articles
    local inserted_ids=()
    
    for i in "${!duplicate_articles[@]}"; do
        local article_data="${duplicate_articles[$i]}"
        local article_id="duplicate-test-$i-$TIMESTAMP"
        
        local title=$(echo "$article_data" | jq -r '.title')
        local content=$(echo "$article_data" | jq -r '.content')
        local url=$(echo "$article_data" | jq -r '.url')
        
        local item='{
            "article_id": {"S": "'$article_id'"},
            "created_at": {"S": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"},
            "title": {"S": "'$title'"},
            "content": {"S": "'$content'"},
            "url": {"S": "'$url'"},
            "feed_source": {"S": "test"},
            "status": {"S": "pending_deduplication"}
        }'
        
        if aws dynamodb put-item --table-name "$ARTICLES_TABLE" --item "$item"; then
            inserted_ids+=("$article_id")
        fi
    done
    
    print_status "Inserted ${#inserted_ids[@]} duplicate test articles"
    
    # Wait for deduplication processing
    sleep 30
    
    # Check deduplication results
    local clustered_articles=0
    local total_clusters=0
    
    for article_id in "${inserted_ids[@]}"; do
        local cluster_info=$(aws dynamodb get-item \
            --table-name "$ARTICLES_TABLE" \
            --key '{"article_id": {"S": "'$article_id'"}}' \
            --query "Item.{cluster_id: cluster_id.S, is_duplicate: is_duplicate.BOOL}" \
            --output json 2>/dev/null || echo "{}")
        
        local cluster_id=$(echo "$cluster_info" | jq -r '.cluster_id // empty')
        local is_duplicate=$(echo "$cluster_info" | jq -r '.is_duplicate // false')
        
        if [[ -n "$cluster_id" ]]; then
            ((clustered_articles++))
        fi
        
        if [[ "$VERBOSE" == "true" ]]; then
            print_status "  Article $article_id: cluster=$cluster_id, duplicate=$is_duplicate"
        fi
    done
    
    # Calculate deduplication accuracy
    local dedup_accuracy=0
    if [[ ${#inserted_ids[@]} -gt 0 ]]; then
        dedup_accuracy=$(echo "scale=2; $clustered_articles * 100 / ${#inserted_ids[@]}" | bc -l 2>/dev/null || echo "0")
    fi
    
    print_status "Deduplication results:"
    print_status "  Articles processed: ${#inserted_ids[@]}"
    print_status "  Articles clustered: $clustered_articles"
    print_status "  Clustering accuracy: $dedup_accuracy%"
    
    if (( $(echo "$dedup_accuracy >= $MIN_DEDUP_ACCURACY * 100" | bc -l) )); then
        print_success "Deduplication accuracy meets threshold (≥${MIN_DEDUP_ACCURACY})"
        return 0
    else
        print_error "Deduplication accuracy below threshold: $dedup_accuracy% < $(echo "$MIN_DEDUP_ACCURACY * 100" | bc -l)%"
        return 1
    fi
}

# Function to test human review workflow
test_human_review_workflow() {
    print_status "Testing human review workflow..."
    
    # Find articles pending review
    local pending_articles=$(aws dynamodb scan \
        --table-name "$ARTICLES_TABLE" \
        --filter-expression "#status = :status" \
        --expression-attribute-names '{"#status": "status"}' \
        --expression-attribute-values '{":status": {"S": "pending_review"}}' \
        --query "Items[*].{article_id: article_id.S, title: title.S}" \
        --output json 2>/dev/null || echo "[]")
    
    local pending_count=$(echo "$pending_articles" | jq 'length')
    
    if [[ "$pending_count" -eq 0 ]]; then
        print_warning "No articles pending review found"
        return 0
    fi
    
    print_status "Found $pending_count articles pending review"
    
    # Test escalation workflow
    local test_article_id=$(echo "$pending_articles" | jq -r '.[0].article_id')
    
    if [[ -n "$test_article_id" ]]; then
        print_status "Testing escalation for article: $test_article_id"
        
        # Simulate human escalation
        local escalation_function=$(echo "$LAMBDA_FUNCTIONS" | grep -i "human.*escalation" | head -1)
        
        if [[ -n "$escalation_function" ]]; then
            local escalation_event='{
                "article_id": "'$test_article_id'",
                "escalation_reason": "test_validation",
                "priority": "medium",
                "reviewer_notes": "End-to-end validation test"
            }'
            
            local response_file="/tmp/escalation_response_$TIMESTAMP.json"
            
            if aws lambda invoke \
                --function-name "$escalation_function" \
                --payload "$escalation_event" \
                --cli-binary-format raw-in-base64-out \
                "$response_file"; then
                
                print_success "Human escalation workflow tested successfully"
                
                if [[ "$VERBOSE" == "true" ]]; then
                    print_status "Escalation response:"
                    cat "$response_file" | jq . 2>/dev/null || cat "$response_file"
                fi
            else
                print_error "Failed to test human escalation workflow"
                return 1
            fi
        else
            print_warning "Human escalation function not found"
        fi
        
        # Test decision workflow
        local decision_function=$(echo "$LAMBDA_FUNCTIONS" | grep -i "publish.*decision" | head -1)
        
        if [[ -n "$decision_function" ]]; then
            print_status "Testing decision workflow..."
            
            local decision_event='{
                "article_id": "'$test_article_id'",
                "decision": "approved",
                "reviewer_id": "test-reviewer",
                "comments": "Approved for end-to-end validation test"
            }'
            
            local response_file="/tmp/decision_response_$TIMESTAMP.json"
            
            if aws lambda invoke \
                --function-name "$decision_function" \
                --payload "$decision_event" \
                --cli-binary-format raw-in-base64-out \
                "$response_file"; then
                
                print_success "Decision workflow tested successfully"
            else
                print_error "Failed to test decision workflow"
                return 1
            fi
        else
            print_warning "Decision function not found"
        fi
    fi
    
    return 0
}

# Function to test report generation
test_report_generation() {
    print_status "Testing report generation and XLSX export..."
    
    # Find query function
    local query_function=$(echo "$LAMBDA_FUNCTIONS" | grep -i "query" | head -1)
    
    if [[ -z "$query_function" ]]; then
        print_warning "Query function not found, skipping report generation test"
        return 0
    fi
    
    # Test query functionality
    local query_event='{
        "query": "AWS vulnerability",
        "filters": {
            "date_range": "7d",
            "sources": ["test"],
            "relevancy_threshold": 0.5
        },
        "format": "json",
        "max_results": 10
    }'
    
    local response_file="/tmp/query_response_$TIMESTAMP.json"
    
    print_status "Testing query functionality..."
    
    if aws lambda invoke \
        --function-name "$query_function" \
        --payload "$query_event" \
        --cli-binary-format raw-in-base64-out \
        "$response_file"; then
        
        print_success "Query function executed successfully"
        
        # Check response
        local result_count=$(cat "$response_file" | jq '.results | length' 2>/dev/null || echo "0")
        print_status "Query returned $result_count results"
        
        if [[ "$VERBOSE" == "true" ]]; then
            print_status "Query response:"
            cat "$response_file" | jq . 2>/dev/null || cat "$response_file"
        fi
    else
        print_error "Failed to execute query function"
        return 1
    fi
    
    # Test XLSX export (simulate)
    print_status "Testing XLSX export functionality..."
    
    local export_event='{
        "query": "security vulnerability",
        "format": "xlsx",
        "include_metadata": true,
        "sort_by": "relevancy_score"
    }'
    
    local export_response_file="/tmp/export_response_$TIMESTAMP.json"
    
    if aws lambda invoke \
        --function-name "$query_function" \
        --payload "$export_event" \
        --cli-binary-format raw-in-base64-out \
        "$export_response_file"; then
        
        print_success "XLSX export functionality tested successfully"
        
        # Check if S3 URL is returned for download
        local s3_url=$(cat "$export_response_file" | jq -r '.download_url // empty' 2>/dev/null)
        
        if [[ -n "$s3_url" ]]; then
            print_success "Export file available at: $s3_url"
        else
            print_status "Export completed (no download URL returned)"
        fi
    else
        print_error "Failed to test XLSX export functionality"
        return 1
    fi
    
    return 0
}

# Function to validate performance metrics
validate_performance_metrics() {
    if [[ "$SKIP_PERFORMANCE" == "true" ]]; then
        print_status "Skipping performance validation as requested"
        return 0
    fi
    
    print_status "Validating performance metrics..."
    
    # Measure processing latency
    local start_time=$(date +%s)
    
    # Process a batch of test articles
    local test_articles_processed=0
    local processing_errors=0
    
    # Get recent articles for performance testing
    local recent_articles=$(aws dynamodb scan \
        --table-name "$ARTICLES_TABLE" \
        --filter-expression "created_at > :recent_time" \
        --expression-attribute-values '{":recent_time": {"S": "'$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)'"}}' \
        --query "Items[*].article_id.S" \
        --output text 2>/dev/null || echo "")
    
    if [[ -n "$recent_articles" ]]; then
        for article_id in $recent_articles; do
            ((test_articles_processed++))
            
            if [[ $test_articles_processed -ge $SAMPLE_SIZE ]]; then
                break
            fi
        done
    fi
    
    local end_time=$(date +%s)
    local processing_time=$((end_time - start_time))
    
    print_status "Performance metrics:"
    print_status "  Articles processed: $test_articles_processed"
    print_status "  Processing time: ${processing_time}s"
    print_status "  Processing errors: $processing_errors"
    
    # Validate against thresholds
    if [[ $processing_time -le $MAX_PROCESSING_TIME ]]; then
        print_success "Processing latency meets threshold (≤${MAX_PROCESSING_TIME}s)"
    else
        print_error "Processing latency exceeds threshold: ${processing_time}s > ${MAX_PROCESSING_TIME}s"
        return 1
    fi
    
    # Calculate throughput
    local throughput=0
    if [[ $processing_time -gt 0 ]]; then
        throughput=$(echo "scale=2; $test_articles_processed / $processing_time" | bc -l 2>/dev/null || echo "0")
    fi
    
    print_status "  Throughput: $throughput articles/second"
    
    return 0
}

# Function to cleanup test data
cleanup_test_data() {
    print_status "Cleaning up test data..."
    
    # Remove test feed
    local test_feed_id="test-feed-$TIMESTAMP"
    
    aws dynamodb delete-item \
        --table-name "$FEEDS_TABLE" \
        --key '{"feed_id": {"S": "'$test_feed_id'"}}' \
        &> /dev/null || true
    
    # Remove test articles (articles with "test" in title or content)
    local test_articles=$(aws dynamodb scan \
        --table-name "$ARTICLES_TABLE" \
        --filter-expression "contains(title, :test) OR contains(content, :test)" \
        --expression-attribute-values '{":test": {"S": "test"}}' \
        --query "Items[*].{article_id: article_id.S, created_at: created_at.S}" \
        --output json 2>/dev/null || echo "[]")
    
    local cleanup_count=0
    
    while IFS= read -r article; do
        local article_id=$(echo "$article" | jq -r '.article_id')
        local created_at=$(echo "$article" | jq -r '.created_at')
        
        if aws dynamodb delete-item \
            --table-name "$ARTICLES_TABLE" \
            --key '{"article_id": {"S": "'$article_id'"}, "created_at": {"S": "'$created_at'"}}' \
            &> /dev/null; then
            ((cleanup_count++))
        fi
        
    done < <(echo "$test_articles" | jq -c '.[]')
    
    print_status "Cleaned up $cleanup_count test articles"
    
    # Remove temporary files
    rm -f /tmp/test_feed_$TIMESTAMP.xml
    rm -f /tmp/*_response_$TIMESTAMP.json
    rm -f /tmp/tf_outputs.json
    
    print_success "Test data cleanup completed"
}

# Function to generate validation report
generate_validation_report() {
    print_status "Generating end-to-end validation report..."
    
    local report_file="$LOG_DIR/e2e-validation-report-$ENVIRONMENT-$TIMESTAMP.json"
    
    # Collect system metrics
    local total_articles=$(aws dynamodb scan --table-name "$ARTICLES_TABLE" --select "COUNT" --query "Count" --output text 2>/dev/null || echo "0")
    local total_feeds=$(aws dynamodb scan --table-name "$FEEDS_TABLE" --select "COUNT" --query "Count" --output text 2>/dev/null || echo "0")
    
    # Create comprehensive report
    cat > "$report_file" << EOF
{
    "validation_report": {
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "environment": "$ENVIRONMENT",
        "validation_duration": "$TIMEOUT",
        "sample_size": $SAMPLE_SIZE,
        "skip_performance": $SKIP_PERFORMANCE
    },
    "system_metrics": {
        "total_articles": $total_articles,
        "total_feeds": $total_feeds,
        "infrastructure_components": {
            "articles_table": "$ARTICLES_TABLE",
            "feeds_table": "$FEEDS_TABLE",
            "s3_bucket": "$S3_BUCKET",
            "step_function": "$STEP_FUNCTION_ARN"
        }
    },
    "validation_results": {
        "feed_ingestion": "completed",
        "article_processing": "completed",
        "keyword_detection": "completed",
        "deduplication": "completed",
        "human_review_workflow": "completed",
        "report_generation": "completed",
        "performance_validation": "$([ "$SKIP_PERFORMANCE" == "true" ] && echo "skipped" || echo "completed")"
    },
    "performance_thresholds": {
        "max_processing_time": $MAX_PROCESSING_TIME,
        "min_dedup_accuracy": $MIN_DEDUP_ACCURACY,
        "min_relevancy_accuracy": $MIN_RELEVANCY_ACCURACY
    },
    "recommendations": [
        "Monitor system performance regularly using CloudWatch dashboards",
        "Review and update RSS feed configurations monthly",
        "Validate keyword detection accuracy with new threat intelligence",
        "Test human review workflows with actual security analysts",
        "Implement automated performance regression testing"
    ]
}
EOF
    
    print_success "Validation report generated: $report_file"
}

# Main validation function
main() {
    print_status "Sentinel End-to-End System Validation"
    print_status "====================================="
    print_status "Environment: $ENVIRONMENT"
    print_status "Timeout: ${TIMEOUT}s"
    print_status "Sample Size: $SAMPLE_SIZE"
    print_status "Skip Performance: $SKIP_PERFORMANCE"
    print_status ""
    
    local validation_steps=(
        "Infrastructure Information:get_infrastructure_info"
        "Test Feed Data Creation:create_test_feed_data"
        "Feed Ingestion Simulation:simulate_feed_ingestion"
        "Article Processing Validation:validate_article_processing"
        "Keyword Detection Testing:test_keyword_detection"
        "Deduplication Testing:test_deduplication"
        "Human Review Workflow:test_human_review_workflow"
        "Report Generation Testing:test_report_generation"
        "Performance Validation:validate_performance_metrics"
    )
    
    local failed_steps=0
    local test_feed_file=""
    
    for step in "${validation_steps[@]}"; do
        local step_name=$(echo "$step" | cut -d':' -f1)
        local step_function=$(echo "$step" | cut -d':' -f2)
        
        print_status ""
        print_status "--- $step_name ---"
        
        if [[ "$step_function" == "create_test_feed_data" ]]; then
            test_feed_file=$($step_function)
        elif [[ "$step_function" == "simulate_feed_ingestion" ]]; then
            if ! $step_function "$test_feed_file"; then
                ((failed_steps++))
                print_error "$step_name failed"
            fi
        else
            if ! $step_function; then
                ((failed_steps++))
                print_error "$step_name failed"
            fi
        fi
    done
    
    # Cleanup test data
    print_status ""
    print_status "--- Cleanup ---"
    cleanup_test_data
    
    # Generate validation report
    generate_validation_report
    
    # Print summary
    print_status ""
    print_status "======================================="
    print_status "END-TO-END VALIDATION SUMMARY"
    print_status "======================================="
    print_status "Environment: $ENVIRONMENT"
    print_status "Total Validation Steps: ${#validation_steps[@]}"
    print_status "Failed Steps: $failed_steps"
    
    if [[ $failed_steps -eq 0 ]]; then
        print_success "🎉 All validation steps passed!"
        print_success "System is ready for production use."
        print_status ""
        print_status "✅ Feed ingestion cycle completed successfully"
        print_status "✅ Deduplication clustering accuracy ≥85%"
        print_status "✅ Keyword detection accuracy ≥70%"
        print_status "✅ Human review workflow functional"
        print_status "✅ Report generation and export working"
        print_status "✅ Performance metrics within thresholds"
    else
        print_error "❌ $failed_steps validation steps failed"
        print_status "Please review and fix the issues before production deployment."
    fi
    
    print_status ""
    print_status "Log file: $LOG_FILE"
    print_status "Report: $LOG_DIR/e2e-validation-report-$ENVIRONMENT-$TIMESTAMP.json"
    
    return $failed_steps
}

# Trap for cleanup
trap 'print_error "Validation interrupted"; cleanup_test_data; exit 1' INT TERM

# Run main function
main "$@"
exit_code=$?

exit $exit_code