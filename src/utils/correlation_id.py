"""
Correlation ID utilities for distributed tracing in Sentinel.
Provides correlation ID generation, propagation, and X-Ray integration.
"""

import uuid
import json
import logging
import functools
from typing import Optional, Dict, Any, Callable
from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.core.context import Context
from aws_xray_sdk.core.models.trace_header import TraceHeader

# Patch AWS SDK calls for automatic tracing
patch_all()

logger = logging.getLogger(__name__)

# Global correlation ID context
_correlation_context = {}

class CorrelationIDManager:
    """Manages correlation IDs for distributed tracing across Lambda functions."""
    
    CORRELATION_ID_HEADER = "X-Correlation-ID"
    TRACE_ID_HEADER = "X-Amzn-Trace-Id"
    
    @staticmethod
    def generate_correlation_id() -> str:
        """Generate a new correlation ID."""
        return str(uuid.uuid4())
    
    @staticmethod
    def extract_correlation_id(event: Dict[str, Any]) -> Optional[str]:
        """Extract correlation ID from Lambda event."""
        # Try different sources for correlation ID
        sources = [
            # API Gateway
            lambda e: e.get("headers", {}).get(CorrelationIDManager.CORRELATION_ID_HEADER),
            lambda e: e.get("headers", {}).get(CorrelationIDManager.CORRELATION_ID_HEADER.lower()),
            # SQS
            lambda e: e.get("Records", [{}])[0].get("messageAttributes", {}).get("correlationId", {}).get("stringValue"),
            # Step Functions
            lambda e: e.get("correlationId"),
            # EventBridge
            lambda e: e.get("detail", {}).get("correlationId"),
            # Direct invocation
            lambda e: e.get("correlation_id"),
        ]
        
        for source in sources:
            try:
                correlation_id = source(event)
                if correlation_id:
                    return correlation_id
            except (KeyError, IndexError, TypeError):
                continue
        
        return None
    
    @staticmethod
    def set_correlation_id(correlation_id: str) -> None:
        """Set correlation ID in global context."""
        global _correlation_context
        _correlation_context["correlation_id"] = correlation_id
        
        # Add to X-Ray segment
        try:
            segment = xray_recorder.current_segment()
            if segment:
                segment.put_annotation("correlation_id", correlation_id)
                segment.put_metadata("correlation", {"id": correlation_id})
        except Exception as e:
            logger.warning(f"Failed to add correlation ID to X-Ray segment: {e}")
    
    @staticmethod
    def get_correlation_id() -> Optional[str]:
        """Get current correlation ID from context."""
        return _correlation_context.get("correlation_id")
    
    @staticmethod
    def clear_correlation_id() -> None:
        """Clear correlation ID from context."""
        global _correlation_context
        _correlation_context.pop("correlation_id", None)

def with_correlation_id(func: Callable) -> Callable:
    """
    Decorator to automatically manage correlation IDs in Lambda functions.
    
    Usage:
        @with_correlation_id
        def lambda_handler(event, context):
            # correlation ID is automatically available
            correlation_id = CorrelationIDManager.get_correlation_id()
            return {"statusCode": 200}
    """
    @functools.wraps(func)
    def wrapper(event: Dict[str, Any], context: Any) -> Any:
        # Extract or generate correlation ID
        correlation_id = CorrelationIDManager.extract_correlation_id(event)
        if not correlation_id:
            correlation_id = CorrelationIDManager.generate_correlation_id()
            logger.info(f"Generated new correlation ID: {correlation_id}")
        else:
            logger.info(f"Using existing correlation ID: {correlation_id}")
        
        # Set correlation ID in context
        CorrelationIDManager.set_correlation_id(correlation_id)
        
        # Add to structured logging
        logger = logging.getLogger()
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.correlation_id = correlation_id
            return record
        
        logging.setLogRecordFactory(record_factory)
        
        try:
            # Execute the function
            result = func(event, context)
            
            # Add correlation ID to response if it's a dict
            if isinstance(result, dict):
                if "headers" not in result:
                    result["headers"] = {}
                result["headers"][CorrelationIDManager.CORRELATION_ID_HEADER] = correlation_id
            
            return result
        
        finally:
            # Restore original log record factory
            logging.setLogRecordFactory(old_factory)
            # Clear correlation ID
            CorrelationIDManager.clear_correlation_id()
    
    return wrapper

def trace_operation(operation_name: str, metadata: Optional[Dict[str, Any]] = None):
    """
    Decorator to trace specific operations within Lambda functions.
    
    Usage:
        @trace_operation("parse_feed", {"feed_type": "RSS"})
        def parse_rss_feed(feed_url):
            # operation is automatically traced
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            correlation_id = CorrelationIDManager.get_correlation_id()
            
            with xray_recorder.in_subsegment(operation_name) as subsegment:
                if subsegment:
                    # Add correlation ID
                    if correlation_id:
                        subsegment.put_annotation("correlation_id", correlation_id)
                    
                    # Add operation metadata
                    if metadata:
                        subsegment.put_metadata("operation", metadata)
                    
                    # Add function arguments (be careful with sensitive data)
                    safe_args = {
                        "arg_count": len(args),
                        "kwarg_keys": list(kwargs.keys()) if kwargs else []
                    }
                    subsegment.put_metadata("arguments", safe_args)
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Add success metadata
                    if subsegment:
                        subsegment.put_annotation("success", True)
                        if isinstance(result, dict) and "statusCode" in result:
                            subsegment.put_annotation("status_code", result["statusCode"])
                    
                    return result
                
                except Exception as e:
                    # Add error metadata
                    if subsegment:
                        subsegment.put_annotation("success", False)
                        subsegment.put_annotation("error_type", type(e).__name__)
                        subsegment.add_exception(e)
                    
                    logger.error(f"Operation {operation_name} failed: {e}", 
                               extra={"correlation_id": correlation_id})
                    raise
        
        return wrapper
    return decorator

def log_with_correlation(message: str, level: str = "info", **kwargs) -> None:
    """
    Log message with correlation ID.
    
    Args:
        message: Log message
        level: Log level (debug, info, warning, error, critical)
        **kwargs: Additional log context
    """
    correlation_id = CorrelationIDManager.get_correlation_id()
    
    log_data = {
        "message": message,
        "correlation_id": correlation_id,
        **kwargs
    }
    
    getattr(logger, level.lower())(json.dumps(log_data))

def create_downstream_event(base_event: Dict[str, Any], additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create an event for downstream Lambda invocation with correlation ID propagation.
    
    Args:
        base_event: Base event data
        additional_data: Additional data to include
    
    Returns:
        Event with correlation ID included
    """
    correlation_id = CorrelationIDManager.get_correlation_id()
    
    event = {
        **base_event,
        "correlation_id": correlation_id,
        **(additional_data or {})
    }
    
    # Add to headers if present
    if "headers" in event:
        event["headers"][CorrelationIDManager.CORRELATION_ID_HEADER] = correlation_id
    
    return event

def get_trace_context() -> Dict[str, Any]:
    """
    Get current trace context for debugging and monitoring.
    
    Returns:
        Dictionary with trace information
    """
    correlation_id = CorrelationIDManager.get_correlation_id()
    
    context = {
        "correlation_id": correlation_id,
        "timestamp": str(uuid.uuid1().time),
    }
    
    try:
        segment = xray_recorder.current_segment()
        if segment:
            context.update({
                "trace_id": segment.trace_id,
                "segment_id": segment.id,
                "sampled": segment.sampled
            })
    except Exception:
        pass
    
    return context

# Structured logging formatter that includes correlation ID
class CorrelationIDFormatter(logging.Formatter):
    """Custom log formatter that includes correlation ID."""
    
    def format(self, record):
        # Add correlation ID to log record
        correlation_id = CorrelationIDManager.get_correlation_id()
        if correlation_id:
            record.correlation_id = correlation_id
        else:
            record.correlation_id = "N/A"
        
        return super().format(record)

# Configure structured logging
def setup_correlation_logging():
    """Set up logging with correlation ID support."""
    formatter = CorrelationIDFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s'
    )
    
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

# Example usage patterns
if __name__ == "__main__":
    # Example Lambda handler
    @with_correlation_id
    def example_lambda_handler(event, context):
        log_with_correlation("Processing started", "info", event_type="example")
        
        @trace_operation("example_operation", {"operation_type": "test"})
        def do_work():
            return {"result": "success"}
        
        result = do_work()
        
        log_with_correlation("Processing completed", "info", result=result)
        
        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }