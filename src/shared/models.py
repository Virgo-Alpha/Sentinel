"""
Shared data models and type definitions for Sentinel cybersecurity triage system.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, validator


class ArticleState(str, Enum):
    """Article processing states."""
    INGESTED = "INGESTED"
    PROCESSED = "PROCESSED"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"
    REVIEW = "REVIEW"


class TriageAction(str, Enum):
    """Triage decision actions."""
    AUTO_PUBLISH = "AUTO_PUBLISH"
    REVIEW = "REVIEW"
    DROP = "DROP"


class FeedCategory(str, Enum):
    """RSS feed categories."""
    ADVISORIES = "Advisories"
    ALERTS = "Alerts"
    VULNERABILITIES = "Vulnerabilities"
    VENDOR = "Vendor"
    THREAT_INTEL = "Threat Intel"
    RESEARCH = "Research"
    NEWS = "News"
    DATA_BREACH = "Data Breach"
    POLICY = "Policy"


class Priority(str, Enum):
    """Priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Configuration Models

class FeedConfig(BaseModel):
    """RSS feed configuration."""
    name: str
    url: HttpUrl
    category: FeedCategory
    enabled: bool = True
    fetch_interval: str = "2h"
    description: Optional[str] = None


class KeywordConfig(BaseModel):
    """Keyword configuration for relevance assessment."""
    keyword: str
    variations: List[str] = Field(default_factory=list)
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    description: Optional[str] = None


class KeywordCategory(BaseModel):
    """Keyword category configuration."""
    name: str
    keywords: List[KeywordConfig]
    priority: Priority = Priority.MEDIUM


# Content Models

class KeywordMatch(BaseModel):
    """Keyword match result."""
    keyword: str
    hit_count: int = Field(ge=0)
    contexts: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class EntityExtraction(BaseModel):
    """Extracted entities from content."""
    cves: List[str] = Field(default_factory=list)
    threat_actors: List[str] = Field(default_factory=list)
    malware: List[str] = Field(default_factory=list)
    vendors: List[str] = Field(default_factory=list)
    products: List[str] = Field(default_factory=list)
    sectors: List[str] = Field(default_factory=list)
    countries: List[str] = Field(default_factory=list)


class Article(BaseModel):
    """Core article data model."""
    article_id: str = Field(default_factory=lambda: str(uuid4()))
    source: str
    feed_id: str
    url: HttpUrl
    canonical_url: Optional[HttpUrl] = None
    title: str
    published_at: datetime
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Processing state
    state: ArticleState = ArticleState.INGESTED
    cluster_id: Optional[str] = None
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    
    # Content analysis
    relevancy_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    keyword_matches: List[KeywordMatch] = Field(default_factory=list)
    triage_action: Optional[TriageAction] = None
    
    # Summaries
    summary_short: Optional[str] = None
    summary_card: Optional[str] = None
    
    # Extracted entities
    entities: EntityExtraction = Field(default_factory=EntityExtraction)
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    guardrail_flags: List[str] = Field(default_factory=list)
    
    # Storage references
    trace_s3_uri: Optional[str] = None
    raw_s3_uri: Optional[str] = None
    normalized_s3_uri: Optional[str] = None
    
    # Audit trail
    created_by_agent_version: Optional[str] = None
    
    @validator('canonical_url', pre=True, always=True)
    def set_canonical_url(cls, v, values):
        """Set canonical URL to main URL if not provided."""
        return v or values.get('url')


class ProcessedArticle(Article):
    """Article with processing results."""
    content_hash: str
    normalized_content: str
    processing_completed_at: datetime = Field(default_factory=datetime.utcnow)


# Tool Response Models

class RelevanceResult(BaseModel):
    """Relevance evaluation result."""
    is_relevant: bool
    relevancy_score: float = Field(ge=0.0, le=1.0)
    keyword_matches: List[KeywordMatch]
    entities: EntityExtraction
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)


class DuplicationResult(BaseModel):
    """Deduplication analysis result."""
    is_duplicate: bool
    cluster_id: Optional[str] = None
    duplicate_of: Optional[str] = None
    similarity_score: float = Field(ge=0.0, le=1.0)
    method: str  # "heuristic" or "semantic"
    rationale: str


class GuardrailResult(BaseModel):
    """Guardrail validation result."""
    passed: bool
    flags: List[str] = Field(default_factory=list)
    violations: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class TriageResult(BaseModel):
    """Triage decision result."""
    action: TriageAction
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    escalation_reason: Optional[str] = None


# Memory and State Models

class AgentMemory(BaseModel):
    """Agent memory for decision tracking."""
    memory_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_type: str
    session_id: str
    article_id: Optional[str] = None
    memory_type: str  # "short_term", "long_term", "a2a"
    content: Dict
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class Comment(BaseModel):
    """User comment on articles."""
    comment_id: str = Field(default_factory=lambda: str(uuid4()))
    article_id: str
    author: str
    content: str
    parent_comment_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class PublishedItem(BaseModel):
    """Published article record."""
    article_id: str
    published_at: datetime = Field(default_factory=datetime.utcnow)
    published_by: str  # agent or user
    decision_trace: Dict
    notification_sent: bool = False


# Query and Reporting Models

class QueryFilter(BaseModel):
    """Query filters for knowledge base search."""
    date_range: Optional[Dict[str, datetime]] = None
    keywords: Optional[List[str]] = None
    categories: Optional[List[FeedCategory]] = None
    sources: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    min_relevancy_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class QueryResult(BaseModel):
    """Query result item."""
    article_id: str
    title: str
    url: HttpUrl
    published_at: datetime
    keyword_matches: List[str]
    hit_count: int
    description: str
    relevancy_score: Optional[float] = None


class ReportExport(BaseModel):
    """Report export configuration."""
    format: str = "xlsx"  # "xlsx", "json", "csv"
    filename: Optional[str] = None
    include_columns: List[str] = Field(default_factory=lambda: [
        "title", "url", "published_at", "keyword", "hit_count", "description"
    ])
    sort_by: str = "published_at"
    sort_order: str = "desc"


# Configuration Schema Models

class FeedsConfig(BaseModel):
    """Complete feeds configuration."""
    feeds: List[FeedConfig]
    categories: List[Dict[str, Union[str, Priority]]]
    settings: Dict[str, Union[str, int]]


class KeywordsConfig(BaseModel):
    """Complete keywords configuration."""
    cloud_platforms: List[KeywordConfig]
    security_vendors: List[KeywordConfig]
    enterprise_tools: List[KeywordConfig]
    enterprise_systems: List[KeywordConfig]
    network_infrastructure: List[KeywordConfig]
    virtualization: List[KeywordConfig]
    specialized_platforms: List[KeywordConfig]
    settings: Dict[str, Union[str, int, float, bool]]
    categories: Dict[str, List[str]]


# Feature Flags Model

class FeatureFlags(BaseModel):
    """Feature flags for gradual rollout."""
    enable_agents: bool = False
    enable_amplify: bool = False
    enable_opensearch: bool = False
    enable_semantic_dedup: bool = True
    enable_llm_relevance: bool = True
    enable_auto_publish: bool = False
    enable_email_notifications: bool = True
    enable_keyword_analysis: bool = True
    
    # Performance settings
    max_concurrent_feeds: int = 5
    max_articles_per_batch: int = 50
    relevance_threshold: float = 0.7
    similarity_threshold: float = 0.85
    
    # Cost controls
    max_daily_llm_calls: int = 10000
    max_monthly_cost_usd: float = 1000.0


# Error and Status Models

class ProcessingError(BaseModel):
    """Processing error information."""
    error_id: str = Field(default_factory=lambda: str(uuid4()))
    article_id: Optional[str] = None
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    retry_count: int = 0
    resolved: bool = False


class SystemStatus(BaseModel):
    """System health and status."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    feeds_healthy: int
    feeds_failing: int
    articles_processed_today: int
    articles_published_today: int
    articles_in_review: int
    avg_processing_time_seconds: float
    error_rate_percent: float
    cost_today_usd: float