"""
Configuration management for Sentinel cybersecurity triage system.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

from .models import FeedsConfig, KeywordsConfig, FeatureFlags


class SentinelConfig(BaseModel):
    """Main configuration class for Sentinel system."""
    
    # AWS Configuration
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    aws_account_id: Optional[str] = Field(default=None, env="AWS_ACCOUNT_ID")
    
    # Environment
    environment: str = Field(default="dev", env="ENVIRONMENT")
    project_name: str = Field(default="sentinel", env="PROJECT_NAME")
    
    # DynamoDB Tables
    articles_table: str = Field(default="sentinel-articles", env="ARTICLES_TABLE")
    comments_table: str = Field(default="sentinel-comments", env="COMMENTS_TABLE")
    memory_table: str = Field(default="sentinel-memory", env="MEMORY_TABLE")
    
    # S3 Buckets
    content_bucket: str = Field(default="sentinel-content", env="CONTENT_BUCKET")
    artifacts_bucket: str = Field(default="sentinel-artifacts", env="ARTIFACTS_BUCKET")
    traces_bucket: str = Field(default="sentinel-traces", env="TRACES_BUCKET")
    
    # OpenSearch
    opensearch_endpoint: Optional[str] = Field(default=None, env="OPENSEARCH_ENDPOINT")
    opensearch_index_articles: str = Field(default="sentinel-articles", env="OPENSEARCH_INDEX_ARTICLES")
    opensearch_index_vectors: str = Field(default="sentinel-vectors", env="OPENSEARCH_INDEX_VECTORS")
    
    # Bedrock
    bedrock_model_id: str = Field(default="anthropic.claude-3-5-sonnet-20241022-v2:0", env="BEDROCK_MODEL_ID")
    bedrock_embedding_model: str = Field(default="amazon.titan-embed-text-v1", env="BEDROCK_EMBEDDING_MODEL")
    
    # Agent Configuration
    ingestor_agent_id: Optional[str] = Field(default=None, env="INGESTOR_AGENT_ID")
    analyst_agent_id: Optional[str] = Field(default=None, env="ANALYST_AGENT_ID")
    
    # Step Functions
    ingestion_state_machine_arn: Optional[str] = Field(default=None, env="INGESTION_STATE_MACHINE_ARN")
    
    # API Gateway
    api_gateway_url: Optional[str] = Field(default=None, env="API_GATEWAY_URL")
    
    # SES Configuration
    ses_sender_email: str = Field(default="noreply@sentinel.local", env="SES_SENDER_EMAIL")
    ses_reply_to_email: Optional[str] = Field(default=None, env="SES_REPLY_TO_EMAIL")
    
    # Notification Recipients
    escalation_emails: List[str] = Field(default_factory=list, env="ESCALATION_EMAILS")
    digest_emails: List[str] = Field(default_factory=list, env="DIGEST_EMAILS")
    alert_emails: List[str] = Field(default_factory=list, env="ALERT_EMAILS")
    
    # Processing Configuration
    max_concurrent_feeds: int = Field(default=5, env="MAX_CONCURRENT_FEEDS")
    max_articles_per_fetch: int = Field(default=50, env="MAX_ARTICLES_PER_FETCH")
    content_retention_days: int = Field(default=365, env="CONTENT_RETENTION_DAYS")
    
    # Thresholds
    relevance_threshold: float = Field(default=0.7, env="RELEVANCE_THRESHOLD")
    similarity_threshold: float = Field(default=0.85, env="SIMILARITY_THRESHOLD")
    confidence_threshold: float = Field(default=0.8, env="CONFIDENCE_THRESHOLD")
    
    # Rate Limiting
    max_daily_llm_calls: int = Field(default=10000, env="MAX_DAILY_LLM_CALLS")
    max_monthly_cost_usd: float = Field(default=1000.0, env="MAX_MONTHLY_COST_USD")
    
    # Retry Configuration
    max_retry_attempts: int = Field(default=3, env="MAX_RETRY_ATTEMPTS")
    retry_backoff_multiplier: float = Field(default=2.0, env="RETRY_BACKOFF_MULTIPLIER")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    enable_xray_tracing: bool = Field(default=True, env="ENABLE_XRAY_TRACING")
    
    # Configuration file paths
    feeds_config_path: str = Field(default="config/feeds.yaml", env="FEEDS_CONFIG_PATH")
    keywords_config_path: str = Field(default="config/keywords.yaml", env="KEYWORDS_CONFIG_PATH")
    
    class Config:
        case_sensitive = False


class ConfigManager:
    """Configuration manager for loading and managing configurations."""
    
    def __init__(self, config: Optional[SentinelConfig] = None):
        self.config = config or SentinelConfig()
        self._feeds_config: Optional[FeedsConfig] = None
        self._keywords_config: Optional[KeywordsConfig] = None
        self._feature_flags: Optional[FeatureFlags] = None
    
    def load_feeds_config(self) -> FeedsConfig:
        """Load RSS feeds configuration from YAML file."""
        if self._feeds_config is None:
            config_path = Path(self.config.feeds_config_path)
            if not config_path.exists():
                raise FileNotFoundError(f"Feeds configuration file not found: {config_path}")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            self._feeds_config = FeedsConfig(**data)
        
        return self._feeds_config
    
    def load_keywords_config(self) -> KeywordsConfig:
        """Load keywords configuration from YAML file."""
        if self._keywords_config is None:
            config_path = Path(self.config.keywords_config_path)
            if not config_path.exists():
                raise FileNotFoundError(f"Keywords configuration file not found: {config_path}")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            self._keywords_config = KeywordsConfig(**data)
        
        return self._keywords_config
    
    def load_feature_flags(self) -> FeatureFlags:
        """Load feature flags from environment or defaults."""
        if self._feature_flags is None:
            self._feature_flags = FeatureFlags(
                enable_agents=os.getenv("ENABLE_AGENTS", "false").lower() == "true",
                enable_amplify=os.getenv("ENABLE_AMPLIFY", "false").lower() == "true",
                enable_opensearch=os.getenv("ENABLE_OPENSEARCH", "false").lower() == "true",
                enable_semantic_dedup=os.getenv("ENABLE_SEMANTIC_DEDUP", "true").lower() == "true",
                enable_llm_relevance=os.getenv("ENABLE_LLM_RELEVANCE", "true").lower() == "true",
                enable_auto_publish=os.getenv("ENABLE_AUTO_PUBLISH", "false").lower() == "true",
                enable_email_notifications=os.getenv("ENABLE_EMAIL_NOTIFICATIONS", "true").lower() == "true",
                enable_keyword_analysis=os.getenv("ENABLE_KEYWORD_ANALYSIS", "true").lower() == "true",
                max_concurrent_feeds=int(os.getenv("MAX_CONCURRENT_FEEDS", "5")),
                max_articles_per_batch=int(os.getenv("MAX_ARTICLES_PER_BATCH", "50")),
                relevance_threshold=float(os.getenv("RELEVANCE_THRESHOLD", "0.7")),
                similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", "0.85")),
                max_daily_llm_calls=int(os.getenv("MAX_DAILY_LLM_CALLS", "10000")),
                max_monthly_cost_usd=float(os.getenv("MAX_MONTHLY_COST_USD", "1000.0")),
            )
        
        return self._feature_flags
    
    def get_all_keywords(self) -> List[str]:
        """Get all keywords from all categories."""
        keywords_config = self.load_keywords_config()
        all_keywords = []
        
        for category_name in [
            "cloud_platforms", "security_vendors", "enterprise_tools",
            "enterprise_systems", "network_infrastructure", "virtualization",
            "specialized_platforms"
        ]:
            category_keywords = getattr(keywords_config, category_name, [])
            for keyword_config in category_keywords:
                all_keywords.append(keyword_config.keyword)
                all_keywords.extend(keyword_config.variations)
        
        return list(set(all_keywords))  # Remove duplicates
    
    def get_enabled_feeds(self) -> List[Dict]:
        """Get list of enabled RSS feeds."""
        feeds_config = self.load_feeds_config()
        return [
            feed.dict() for feed in feeds_config.feeds 
            if feed.enabled
        ]
    
    def get_feed_by_name(self, name: str) -> Optional[Dict]:
        """Get feed configuration by name."""
        feeds_config = self.load_feeds_config()
        for feed in feeds_config.feeds:
            if feed.name == name:
                return feed.dict()
        return None
    
    def get_keywords_by_category(self, category: str) -> List[Dict]:
        """Get keywords for a specific category."""
        keywords_config = self.load_keywords_config()
        category_keywords = getattr(keywords_config, category, [])
        return [kw.dict() for kw in category_keywords]
    
    def reload_configs(self):
        """Reload all configurations from files."""
        self._feeds_config = None
        self._keywords_config = None
        self._feature_flags = None
    
    def validate_configuration(self) -> Dict[str, bool]:
        """Validate all configuration files and settings."""
        validation_results = {}
        
        try:
            self.load_feeds_config()
            validation_results["feeds_config"] = True
        except Exception as e:
            validation_results["feeds_config"] = False
            validation_results["feeds_error"] = str(e)
        
        try:
            self.load_keywords_config()
            validation_results["keywords_config"] = True
        except Exception as e:
            validation_results["keywords_config"] = False
            validation_results["keywords_error"] = str(e)
        
        try:
            self.load_feature_flags()
            validation_results["feature_flags"] = True
        except Exception as e:
            validation_results["feature_flags"] = False
            validation_results["feature_flags_error"] = str(e)
        
        return validation_results


# Global configuration instance
config_manager = ConfigManager()


def get_config() -> SentinelConfig:
    """Get the global configuration instance."""
    return config_manager.config


def get_feeds_config() -> FeedsConfig:
    """Get the feeds configuration."""
    return config_manager.load_feeds_config()


def get_keywords_config() -> KeywordsConfig:
    """Get the keywords configuration."""
    return config_manager.load_keywords_config()


def get_feature_flags() -> FeatureFlags:
    """Get the feature flags."""
    return config_manager.load_feature_flags()