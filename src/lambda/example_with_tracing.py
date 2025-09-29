"""
Example Lambda function demonstrating X-Ray tracing with correlation IDs.
This shows how to use the correlation ID utilities in Sentinel Lambda functions.
"""

import json
import logging
import boto3
from typing import Dict, Any

# Import correlation ID utilities from the Lambda layer
from sentinel_utils.correlation_id import (
    with_correlation_id,
    trace_operation,
    log_with_correlation,
    create_downstream_event,
    get_trace_context,
    setup_correlation_logging
)

# Set up structured logging with correlation ID support
setup_correlation_logging()

# AWS clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')

logger = logging.getLogger(__name__)

@with_correlation_id
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Example Lambda handler with correlation ID tracing.
    
    This function demonstrates:
    - Automatic correlation ID management
    - Operation tracing with X-Ray
    - Structured logging with correlation context
    - Downstream service invocation with correlation propagation
    """
    
    log_with_correlation("Lambda execution started", "info", 
                        event_type=event.get("eventType", "unknown"))
    
    try:
        # Example: Process an article ingestion event
        if event.get("eventType") == "article_ingestion":
            result = process_article_ingestion(event)
        
        # Example: Process a relevancy evaluation event
        elif event.get("eventType") == "relevancy_evaluation":
            result = process_relevancy_evaluation(event)
        
        # Example: Process a deduplication event
        elif event.get("eventType") == "deduplication":
            result = process_deduplication(event)
        
        else:
            result = {"status": "unknown_event_type", "event_type": event.get("eventType")}
        
        log_with_correlation("Lambda execution completed successfully", "info", 
                           result=result)
        
        return {
            "statusCode": 200,
            "body": json.dumps(result),
            "headers": {
                "Content-Type": "application/json"
            }
        }
    
    except Exception as e:
        log_with_correlation("Lambda execution failed", "error", 
                           error=str(e), error_type=type(e).__name__)
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "trace_context": get_trace_context()
            }),
            "headers": {
                "Content-Type": "application/json"
            }
        }

@trace_operation("article_ingestion", {"operation_type": "feed_processing"})
def process_article_ingestion(event: Dict[str, Any]) -> Dict[str, Any]:
    """Process article ingestion with tracing."""
    
    article_data = event.get("article", {})
    feed_source = event.get("feed_source", "unknown")
    
    log_with_correlation("ARTICLE_INGESTED", "info", 
                        feed=feed_source, 
                        article_id=article_data.get("id"))
    
    # Simulate article processing
    processed_article = {
        "id": article_data.get("id"),
        "title": article_data.get("title"),
        "source": feed_source,
        "processed_at": context.aws_request_id,
        "correlation_id": get_trace_context().get("correlation_id")
    }
    
    # Store in DynamoDB (example)
    store_article_metadata(processed_article)
    
    # Trigger downstream processing
    trigger_relevancy_evaluation(processed_article)
    
    return {
        "status": "ingested",
        "article_id": processed_article["id"],
        "next_stage": "relevancy_evaluation"
    }

@trace_operation("relevancy_evaluation", {"operation_type": "llm_processing"})
def process_relevancy_evaluation(event: Dict[str, Any]) -> Dict[str, Any]:
    """Process relevancy evaluation with tracing."""
    
    article_id = event.get("article_id")
    content = event.get("content", "")
    
    # Simulate LLM call for relevancy assessment
    relevancy_score = simulate_llm_relevancy_check(content)
    is_relevant = relevancy_score > 0.6
    
    log_with_correlation("RELEVANCY_ASSESSED", "info",
                        article_id=article_id,
                        score=relevancy_score,
                        is_relevant=int(is_relevant))
    
    # Update article with relevancy data
    update_article_relevancy(article_id, relevancy_score, is_relevant)
    
    # Trigger next stage if relevant
    if is_relevant:
        trigger_deduplication(article_id)
    
    return {
        "status": "evaluated",
        "article_id": article_id,
        "relevancy_score": relevancy_score,
        "is_relevant": is_relevant,
        "next_stage": "deduplication" if is_relevant else "archived"
    }

@trace_operation("deduplication", {"operation_type": "similarity_analysis"})
def process_deduplication(event: Dict[str, Any]) -> Dict[str, Any]:
    """Process deduplication with tracing."""
    
    article_id = event.get("article_id")
    
    # Simulate deduplication logic
    duplicate_check = simulate_duplicate_detection(article_id)
    is_duplicate = duplicate_check.get("is_duplicate", False)
    cluster_id = duplicate_check.get("cluster_id")
    
    log_with_correlation("DEDUPLICATION_COMPLETED", "info",
                        article_id=article_id,
                        is_duplicate=int(is_duplicate),
                        cluster_id=cluster_id)
    
    # Update article with deduplication data
    update_article_deduplication(article_id, is_duplicate, cluster_id)
    
    return {
        "status": "deduplicated",
        "article_id": article_id,
        "is_duplicate": is_duplicate,
        "cluster_id": cluster_id,
        "next_stage": "triage" if not is_duplicate else "archived"
    }

@trace_operation("store_metadata", {"storage_type": "dynamodb"})
def store_article_metadata(article_data: Dict[str, Any]) -> None:
    """Store article metadata in DynamoDB."""
    
    table_name = "sentinel-articles"  # This would come from environment
    
    try:
        table = dynamodb.Table(table_name)
        table.put_item(Item=article_data)
        
        log_with_correlation("Article metadata stored", "info",
                           article_id=article_data.get("id"),
                           table=table_name)
    
    except Exception as e:
        log_with_correlation("Failed to store article metadata", "error",
                           article_id=article_data.get("id"),
                           error=str(e))
        raise

@trace_operation("llm_relevancy_check", {"model": "claude-3-sonnet"})
def simulate_llm_relevancy_check(content: str) -> float:
    """Simulate LLM relevancy check (replace with actual Bedrock call)."""
    
    # This would be replaced with actual Bedrock API call
    # For demonstration, return a mock score based on content length
    import random
    
    base_score = min(len(content) / 1000, 1.0)  # Longer content = higher relevance
    noise = random.uniform(-0.2, 0.2)
    
    return max(0.0, min(1.0, base_score + noise))

def simulate_duplicate_detection(article_id: str) -> Dict[str, Any]:
    """Simulate duplicate detection logic."""
    
    import random
    
    # Mock duplicate detection
    is_duplicate = random.random() < 0.15  # 15% chance of duplicate
    cluster_id = f"cluster_{random.randint(1, 100)}" if is_duplicate else None
    
    return {
        "is_duplicate": is_duplicate,
        "cluster_id": cluster_id,
        "similarity_score": random.uniform(0.8, 0.95) if is_duplicate else random.uniform(0.0, 0.3)
    }

def trigger_relevancy_evaluation(article_data: Dict[str, Any]) -> None:
    """Trigger downstream relevancy evaluation."""
    
    downstream_event = create_downstream_event({
        "eventType": "relevancy_evaluation",
        "article_id": article_data["id"],
        "content": article_data.get("content", "")
    })
    
    # In real implementation, this would invoke the relevancy evaluator Lambda
    log_with_correlation("Triggered relevancy evaluation", "info",
                        article_id=article_data["id"],
                        downstream_event_size=len(json.dumps(downstream_event)))

def trigger_deduplication(article_id: str) -> None:
    """Trigger downstream deduplication."""
    
    downstream_event = create_downstream_event({
        "eventType": "deduplication",
        "article_id": article_id
    })
    
    # In real implementation, this would invoke the deduplication Lambda
    log_with_correlation("Triggered deduplication", "info",
                        article_id=article_id)

def update_article_relevancy(article_id: str, score: float, is_relevant: bool) -> None:
    """Update article with relevancy assessment."""
    
    log_with_correlation("Updated article relevancy", "info",
                        article_id=article_id,
                        relevancy_score=score,
                        is_relevant=is_relevant)

def update_article_deduplication(article_id: str, is_duplicate: bool, cluster_id: str) -> None:
    """Update article with deduplication results."""
    
    log_with_correlation("Updated article deduplication", "info",
                        article_id=article_id,
                        is_duplicate=is_duplicate,
                        cluster_id=cluster_id)

# Example of how to use the tracing utilities in other functions
@trace_operation("keyword_analysis", {"analysis_type": "target_keywords"})
def analyze_keywords(content: str, target_keywords: list) -> Dict[str, Any]:
    """Analyze keyword matches in content."""
    
    matches = []
    for keyword in target_keywords:
        hit_count = content.lower().count(keyword.lower())
        if hit_count > 0:
            matches.append({
                "keyword": keyword,
                "hit_count": hit_count,
                "category": "target"  # This would be determined by keyword categorization
            })
            
            log_with_correlation("KEYWORD_HIT", "info",
                               keyword=keyword,
                               category="target",
                               hit_count=hit_count)
    
    return {
        "total_matches": len(matches),
        "total_hits": sum(m["hit_count"] for m in matches),
        "matches": matches
    }

# Example of processing latency tracking
@trace_operation("processing_stage", {"stage": "complete"})
def track_processing_completion(article_id: str, stage: str, start_time: float) -> None:
    """Track processing stage completion."""
    
    import time
    
    end_time = time.time()
    latency_ms = int((end_time - start_time) * 1000)
    
    log_with_correlation("PROCESSING_COMPLETED", "info",
                        article_id=article_id,
                        stage=stage,
                        latency_ms=latency_ms)

# Example of A/B testing metrics
def log_ab_test_metric(variant: str, metric_name: str, metric_value: float) -> None:
    """Log A/B testing metrics."""
    
    log_with_correlation("AB_TEST", "info",
                        variant=variant,
                        metric_name=metric_name,
                        metric_value=metric_value)

# Example usage for different A/B test scenarios
def example_ab_testing():
    """Example of A/B testing integration."""
    
    # Example: Test different prompt variants
    log_ab_test_metric("A", "PromptPrecision", 0.85)
    log_ab_test_metric("A", "PromptLatency", 1200)
    
    log_ab_test_metric("B", "PromptPrecision", 0.88)
    log_ab_test_metric("B", "PromptLatency", 1350)