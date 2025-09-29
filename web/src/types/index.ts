// User types
export interface User {
  id: string;
  email: string;
  given_name?: string;
  family_name?: string;
  groups: string[];
}

// Article types
export interface Article {
  article_id: string;
  source: string;
  feed_id: string;
  url: string;
  canonical_url: string;
  title: string;
  published_at: string;
  ingested_at: string;
  state: 'INGESTED' | 'PROCESSED' | 'PUBLISHED' | 'ARCHIVED' | 'REVIEW';
  cluster_id?: string;
  is_duplicate: boolean;
  duplicate_of?: string;
  relevancy_score: number;
  keyword_matches: KeywordMatch[];
  triage_action: 'AUTO_PUBLISH' | 'REVIEW' | 'DROP';
  summary_short?: string;
  summary_card?: string;
  entities: EntityExtraction;
  tags: string[];
  confidence: number;
  guardrail_flags: string[];
  trace_s3_uri?: string;
  raw_s3_uri?: string;
  normalized_s3_uri?: string;
  created_by_agent_version?: string;
}

export interface KeywordMatch {
  keyword: string;
  hit_count: number;
  contexts: string[];
}

export interface EntityExtraction {
  cves: string[];
  threat_actors: string[];
  malware: string[];
  vendors: string[];
  products: string[];
  sectors: string[];
  countries: string[];
}

// Comment types
export interface Comment {
  comment_id: string;
  article_id: string;
  parent_id?: string;
  author: string;
  content: string;
  created_at: string;
  updated_at?: string;
  replies?: Comment[];
}

// Chat types
export interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: string;
  sources?: ChatSource[];
  feedback?: 'up' | 'down';
}

export interface ChatSource {
  title: string;
  url: string;
  snippet: string;
}

export interface ChatSession {
  sessionId: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

// Query types
export interface QueryFilters {
  date_range?: {
    start: string;
    end: string;
  };
  keywords?: string[];
  categories?: string[];
  sources?: string[];
  state?: string[];
}

export interface QueryResult {
  articles: Article[];
  total: number;
  export_url?: string;
}

// API Response types
export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
}

// Dashboard metrics
export interface DashboardMetrics {
  total_articles: number;
  published_today: number;
  pending_review: number;
  keyword_hits: number;
  recent_articles: Article[];
}

// Review decision
export interface ReviewDecision {
  article_id: string;
  decision: 'approve' | 'reject';
  reason?: string;
  reviewer: string;
  timestamp: string;
}