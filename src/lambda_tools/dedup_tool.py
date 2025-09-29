"""
DedupTool Lambda tool for multi-layered deduplication.

This Lambda function implements both heuristic and semantic deduplication using
URL comparison, title similarity, domain clustering, Bedrock embeddings, and
OpenSearch k-NN search for comprehensive duplicate detection and cluster management.
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
from difflib import SequenceMatcher

import boto3
from botocore.exceptions import ClientError
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# AWS clients
bedrock_client = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')


@dataclass
class DuplicationResult:
    """Represents the result of deduplication analysis."""
    is_duplicate: bool
    cluster_id: Optional[str] = None
    duplicate_of: Optional[str] = None
    similarity_score: float = 0.0
    method: str = "heuristic"  # "heuristic" or "semantic"
    rationale: str = ""
    similar_articles: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.similar_articles is None:
            self.similar_articles = []


@dataclass
class ArticleFingerprint:
    """Represents key identifying features of an article for deduplication."""
    article_id: str
    url: str
    canonical_url: str
    title: str
    normalized_title: str
    domain: str
    published_at: datetime
    content_hash: str
    title_hash: str
    url_hash: str


class DedupToolError(Exception):
    """Custom exception for deduplication errors."""
    pass


class HeuristicDeduplicator:
    """Handles heuristic-based deduplication using URL, title, and domain comparison."""
    
    def __init__(self):
        self.title_similarity_threshold = 0.85
        self.url_similarity_threshold = 0.90
        self.time_window_hours = 72  # Consider articles within 72 hours for deduplication
    
    def find_heuristic_duplicates(self, article: ArticleFingerprint, 
                                 existing_articles: List[ArticleFingerprint]) -> DuplicationResult:
        """
        Find duplicates using heuristic methods.
        
        Args:
            article: Article to check for duplicates
            existing_articles: List of existing articles to compare against
            
        Returns:
            DuplicationResult with heuristic analysis
        """
        try:
            logger.info(f"Running heuristic deduplication for article: {article.article_id}")
            
            # Filter articles within time window
            time_filtered = self._filter_by_time_window(article, existing_articles)
            logger.info(f"Checking against {len(time_filtered)} articles within time window")
            
            # Check for exact URL matches
            url_duplicates = self._find_url_duplicates(article, time_filtered)
            if url_duplicates:
                return self._create_duplicate_result(
                    article, url_duplicates[0], 1.0, "exact_url_match",
                    "Exact URL match found"
                )
            
            # Check for canonical URL matches
            canonical_duplicates = self._find_canonical_url_duplicates(article, time_filtered)
            if canonical_duplicates:
                return self._create_duplicate_result(
                    article, canonical_duplicates[0], 0.95, "canonical_url_match",
                    "Canonical URL match found"
                )
            
            # Check for title similarity within same domain
            title_duplicates = self._find_title_duplicates(article, time_filtered)
            if title_duplicates:
                best_match = max(title_duplicates, key=lambda x: x['similarity'])
                if best_match['similarity'] >= self.title_similarity_threshold:
                    return self._create_duplicate_result(
                        article, best_match['article'], best_match['similarity'], 
                        "title_similarity",
                        f"High title similarity ({best_match['similarity']:.2f}) within same domain"
                    )
            
            # Check for URL pattern similarity
            url_pattern_duplicates = self._find_url_pattern_duplicates(article, time_filtered)
            if url_pattern_duplicates:
                best_match = max(url_pattern_duplicates, key=lambda x: x['similarity'])
                if best_match['similarity'] >= self.url_similarity_threshold:
                    return self._create_duplicate_result(
                        article, best_match['article'], best_match['similarity'],
                        "url_pattern_similarity",
                        f"High URL pattern similarity ({best_match['similarity']:.2f})"
                    )
            
            # No duplicates found
            return DuplicationResult(
                is_duplicate=False,
                similarity_score=0.0,
                method="heuristic",
                rationale="No heuristic duplicates found"
            )
            
        except Exception as e:
            logger.error(f"Heuristic deduplication failed: {e}")
            raise DedupToolError(f"Heuristic deduplication failed: {e}")
    
    def _filter_by_time_window(self, article: ArticleFingerprint, 
                              existing_articles: List[ArticleFingerprint]) -> List[ArticleFingerprint]:
        """Filter articles within the time window."""
        time_threshold = article.published_at - timedelta(hours=self.time_window_hours)
        return [
            a for a in existing_articles 
            if a.published_at >= time_threshold and a.article_id != article.article_id
        ]
    
    def _find_url_duplicates(self, article: ArticleFingerprint, 
                           candidates: List[ArticleFingerprint]) -> List[ArticleFingerprint]:
        """Find exact URL duplicates."""
        return [a for a in candidates if a.url == article.url]
    
    def _find_canonical_url_duplicates(self, article: ArticleFingerprint,
                                     candidates: List[ArticleFingerprint]) -> List[ArticleFingerprint]:
        """Find canonical URL duplicates."""
        return [a for a in candidates if a.canonical_url == article.canonical_url]
    
    def _find_title_duplicates(self, article: ArticleFingerprint,
                             candidates: List[ArticleFingerprint]) -> List[Dict[str, Any]]:
        """Find title-based duplicates within the same domain."""
        duplicates = []
        
        # Only check articles from the same domain
        same_domain_articles = [a for a in candidates if a.domain == article.domain]
        
        for candidate in same_domain_articles:
            similarity = self._calculate_title_similarity(article.normalized_title, 
                                                        candidate.normalized_title)
            if similarity >= self.title_similarity_threshold:
                duplicates.append({
                    'article': candidate,
                    'similarity': similarity
                })
        
        return duplicates
    
    def _find_url_pattern_duplicates(self, article: ArticleFingerprint,
                                   candidates: List[ArticleFingerprint]) -> List[Dict[str, Any]]:
        """Find URL pattern-based duplicates."""
        duplicates = []
        article_path = self._normalize_url_path(article.url)
        
        for candidate in candidates:
            candidate_path = self._normalize_url_path(candidate.url)
            similarity = SequenceMatcher(None, article_path, candidate_path).ratio()
            
            if similarity >= self.url_similarity_threshold:
                duplicates.append({
                    'article': candidate,
                    'similarity': similarity
                })
        
        return duplicates
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two normalized titles."""
        return SequenceMatcher(None, title1, title2).ratio()
    
    def _normalize_url_path(self, url: str) -> str:
        """Normalize URL path for comparison."""
        try:
            parsed = urlparse(url)
            # Remove query parameters and fragments, normalize path
            path = parsed.path.lower().strip('/')
            # Remove common tracking parameters patterns
            path = re.sub(r'/\d{4}/\d{2}/\d{2}/', '/DATE/', path)  # Date patterns
            path = re.sub(r'/\d+/', '/ID/', path)  # Numeric IDs
            return path
        except:
            return url.lower()
    
    def _create_duplicate_result(self, article: ArticleFingerprint, 
                               duplicate_article: ArticleFingerprint,
                               similarity: float, method: str, rationale: str) -> DuplicationResult:
        """Create a duplicate result."""
        return DuplicationResult(
            is_duplicate=True,
            duplicate_of=duplicate_article.article_id,
            similarity_score=similarity,
            method=f"heuristic_{method}",
            rationale=rationale,
            similar_articles=[{
                'article_id': duplicate_article.article_id,
                'title': duplicate_article.title,
                'url': duplicate_article.url,
                'similarity': similarity,
                'published_at': duplicate_article.published_at.isoformat()
            }]
        )


class SemanticDeduplicator:
    """Handles semantic deduplication using Bedrock embeddings and OpenSearch k-NN."""
    
    def __init__(self, opensearch_endpoint: str, opensearch_index: str,
                 embedding_model: str = "amazon.titan-embed-text-v1"):
        self.opensearch_endpoint = opensearch_endpoint
        self.opensearch_index = opensearch_index
        self.embedding_model = embedding_model
        self.semantic_similarity_threshold = 0.85
        self.max_search_results = 10
        
        # Initialize OpenSearch client
        self.opensearch_client = self._create_opensearch_client()
    
    def _create_opensearch_client(self) -> OpenSearch:
        """Create OpenSearch client with AWS authentication."""
        try:
            import os
            region = os.environ.get('AWS_REGION', 'us-east-1')
            
            # Parse endpoint to get host and port
            if self.opensearch_endpoint.startswith('https://'):
                host = self.opensearch_endpoint[8:]
                port = 443
                use_ssl = True
            else:
                host = self.opensearch_endpoint
                port = 9200
                use_ssl = False
            
            # Create AWS auth
            credentials = boto3.Session().get_credentials()
            awsauth = AWSRequestsAuth(credentials, region, 'es')
            
            return OpenSearch(
                hosts=[{'host': host, 'port': port}],
                http_auth=awsauth,
                use_ssl=use_ssl,
                verify_certs=True,
                connection_class=RequestsHttpConnection
            )
            
        except Exception as e:
            logger.error(f"Failed to create OpenSearch client: {e}")
            raise DedupToolError(f"OpenSearch client creation failed: {e}")
    
    def find_semantic_duplicates(self, article_content: str, article_title: str,
                               article_id: str) -> DuplicationResult:
        """
        Find semantic duplicates using embeddings and k-NN search.
        
        Args:
            article_content: Article content for embedding
            article_title: Article title
            article_id: Article ID to exclude from results
            
        Returns:
            DuplicationResult with semantic analysis
        """
        try:
            logger.info(f"Running semantic deduplication for article: {article_id}")
            
            # Generate embedding for the article
            embedding = self._generate_embedding(article_content, article_title)
            
            # Search for similar articles using k-NN
            similar_articles = self._search_similar_articles(embedding, article_id)
            
            if not similar_articles:
                return DuplicationResult(
                    is_duplicate=False,
                    similarity_score=0.0,
                    method="semantic",
                    rationale="No semantically similar articles found"
                )
            
            # Find the best match
            best_match = similar_articles[0]
            similarity_score = best_match['_score']
            
            if similarity_score >= self.semantic_similarity_threshold:
                return DuplicationResult(
                    is_duplicate=True,
                    duplicate_of=best_match['_source']['article_id'],
                    similarity_score=similarity_score,
                    method="semantic",
                    rationale=f"High semantic similarity ({similarity_score:.3f}) found",
                    similar_articles=[{
                        'article_id': hit['_source']['article_id'],
                        'title': hit['_source']['title'],
                        'url': hit['_source']['url'],
                        'similarity': hit['_score'],
                        'published_at': hit['_source']['published_at']
                    } for hit in similar_articles[:5]]
                )
            else:
                return DuplicationResult(
                    is_duplicate=False,
                    similarity_score=similarity_score,
                    method="semantic",
                    rationale=f"Semantic similarity ({similarity_score:.3f}) below threshold",
                    similar_articles=[{
                        'article_id': hit['_source']['article_id'],
                        'title': hit['_source']['title'],
                        'url': hit['_source']['url'],
                        'similarity': hit['_score'],
                        'published_at': hit['_source']['published_at']
                    } for hit in similar_articles[:3]]
                )
                
        except Exception as e:
            logger.error(f"Semantic deduplication failed: {e}")
            # Return non-duplicate result on failure to avoid blocking pipeline
            return DuplicationResult(
                is_duplicate=False,
                similarity_score=0.0,
                method="semantic",
                rationale=f"Semantic analysis failed: {str(e)}"
            )
    
    def _generate_embedding(self, content: str, title: str) -> List[float]:
        """Generate embedding using Bedrock."""
        try:
            # Combine title and content for embedding
            text_to_embed = f"{title}\n\n{content[:2000]}"  # Limit content length
            
            response = bedrock_client.invoke_model(
                modelId=self.embedding_model,
                body=json.dumps({
                    "inputText": text_to_embed
                })
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['embedding']
            
        except ClientError as e:
            logger.error(f"Bedrock embedding generation failed: {e}")
            raise DedupToolError(f"Embedding generation failed: {e}")
    
    def _search_similar_articles(self, embedding: List[float], 
                               exclude_article_id: str) -> List[Dict[str, Any]]:
        """Search for similar articles using k-NN."""
        try:
            query = {
                "size": self.max_search_results,
                "query": {
                    "bool": {
                        "must": [
                            {
                                "knn": {
                                    "embedding": {
                                        "vector": embedding,
                                        "k": self.max_search_results
                                    }
                                }
                            }
                        ],
                        "must_not": [
                            {
                                "term": {
                                    "article_id": exclude_article_id
                                }
                            }
                        ]
                    }
                },
                "_source": ["article_id", "title", "url", "published_at"]
            }
            
            response = self.opensearch_client.search(
                index=self.opensearch_index,
                body=query
            )
            
            return response['hits']['hits']
            
        except Exception as e:
            logger.error(f"OpenSearch k-NN search failed: {e}")
            raise DedupToolError(f"Semantic search failed: {e}")
    
    def store_article_embedding(self, article_id: str, title: str, content: str,
                              url: str, published_at: str) -> bool:
        """Store article embedding in OpenSearch for future comparisons."""
        try:
            # Generate embedding
            embedding = self._generate_embedding(content, title)
            
            # Store in OpenSearch
            doc = {
                "article_id": article_id,
                "title": title,
                "url": url,
                "published_at": published_at,
                "embedding": embedding,
                "indexed_at": datetime.utcnow().isoformat()
            }
            
            response = self.opensearch_client.index(
                index=self.opensearch_index,
                id=article_id,
                body=doc
            )
            
            logger.info(f"Stored embedding for article {article_id}")
            return response['result'] in ['created', 'updated']
            
        except Exception as e:
            logger.error(f"Failed to store article embedding: {e}")
            return False


class ClusterManager:
    """Manages article clusters and duplicate relationships."""
    
    def __init__(self, articles_table_name: str):
        self.articles_table = dynamodb.Table(articles_table_name)
    
    def assign_cluster(self, article_id: str, duplicate_result: DuplicationResult) -> str:
        """
        Assign article to a cluster based on duplication result.
        
        Args:
            article_id: ID of the article to cluster
            duplicate_result: Result of deduplication analysis
            
        Returns:
            Cluster ID assigned to the article
        """
        try:
            if duplicate_result.is_duplicate and duplicate_result.duplicate_of:
                # Get cluster ID from the duplicate article
                cluster_id = self._get_article_cluster(duplicate_result.duplicate_of)
                if not cluster_id:
                    # Create new cluster with the original article as canonical
                    cluster_id = self._create_cluster(duplicate_result.duplicate_of)
                
                # Update current article with cluster assignment
                self._update_article_cluster(article_id, cluster_id, duplicate_result.duplicate_of)
                
                logger.info(f"Assigned article {article_id} to cluster {cluster_id}")
                return cluster_id
            else:
                # Create new cluster for non-duplicate article
                cluster_id = self._create_cluster(article_id)
                logger.info(f"Created new cluster {cluster_id} for article {article_id}")
                return cluster_id
                
        except Exception as e:
            logger.error(f"Cluster assignment failed: {e}")
            raise DedupToolError(f"Cluster assignment failed: {e}")
    
    def _get_article_cluster(self, article_id: str) -> Optional[str]:
        """Get cluster ID for an article."""
        try:
            response = self.articles_table.get_item(
                Key={'article_id': article_id},
                ProjectionExpression='cluster_id'
            )
            
            if 'Item' in response:
                return response['Item'].get('cluster_id')
            return None
            
        except ClientError as e:
            logger.error(f"Failed to get article cluster: {e}")
            return None
    
    def _create_cluster(self, canonical_article_id: str) -> str:
        """Create a new cluster with the given article as canonical."""
        cluster_id = f"cluster_{canonical_article_id}"
        
        # Update the canonical article with cluster ID
        self._update_article_cluster(canonical_article_id, cluster_id, None)
        
        return cluster_id
    
    def _update_article_cluster(self, article_id: str, cluster_id: str, 
                              duplicate_of: Optional[str]) -> None:
        """Update article with cluster information."""
        try:
            update_expression = "SET cluster_id = :cluster_id, is_duplicate = :is_duplicate"
            expression_values = {
                ':cluster_id': cluster_id,
                ':is_duplicate': duplicate_of is not None
            }
            
            if duplicate_of:
                update_expression += ", duplicate_of = :duplicate_of"
                expression_values[':duplicate_of'] = duplicate_of
            
            self.articles_table.update_item(
                Key={'article_id': article_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
        except ClientError as e:
            logger.error(f"Failed to update article cluster: {e}")
            raise DedupToolError(f"Article cluster update failed: {e}")


class DedupTool:
    """Main deduplication tool orchestrating heuristic and semantic methods."""
    
    def __init__(self, articles_table_name: str, opensearch_endpoint: str, 
                 opensearch_index: str):
        self.heuristic_deduplicator = HeuristicDeduplicator()
        self.semantic_deduplicator = SemanticDeduplicator(opensearch_endpoint, opensearch_index)
        self.cluster_manager = ClusterManager(articles_table_name)
        self.articles_table = dynamodb.Table(articles_table_name)
    
    def find_duplicates(self, article_data: Dict[str, Any]) -> DuplicationResult:
        """
        Perform comprehensive deduplication analysis.
        
        Args:
            article_data: Dictionary containing article information
            
        Returns:
            DuplicationResult with comprehensive analysis
        """
        try:
            article_id = article_data['article_id']
            logger.info(f"Starting deduplication analysis for article: {article_id}")
            
            # Create article fingerprint
            fingerprint = self._create_article_fingerprint(article_data)
            
            # Get existing articles for comparison
            existing_articles = self._get_existing_articles(fingerprint.published_at)
            
            # Step 1: Heuristic deduplication
            heuristic_result = self.heuristic_deduplicator.find_heuristic_duplicates(
                fingerprint, existing_articles
            )
            
            if heuristic_result.is_duplicate:
                logger.info(f"Heuristic duplicate found: {heuristic_result.duplicate_of}")
                return heuristic_result
            
            # Step 2: Semantic deduplication (if enabled and heuristic didn't find duplicates)
            try:
                semantic_result = self.semantic_deduplicator.find_semantic_duplicates(
                    article_data.get('normalized_content', ''),
                    article_data.get('title', ''),
                    article_id
                )
                
                if semantic_result.is_duplicate:
                    logger.info(f"Semantic duplicate found: {semantic_result.duplicate_of}")
                    return semantic_result
                
                # Store embedding for future comparisons
                self.semantic_deduplicator.store_article_embedding(
                    article_id,
                    article_data.get('title', ''),
                    article_data.get('normalized_content', ''),
                    article_data.get('url', ''),
                    article_data.get('published_at', '')
                )
                
                return semantic_result
                
            except Exception as e:
                logger.warning(f"Semantic deduplication failed, using heuristic result: {e}")
                return heuristic_result
            
        except Exception as e:
            logger.error(f"Deduplication analysis failed: {e}")
            raise DedupToolError(f"Deduplication failed: {e}")
    
    def assign_cluster(self, article_id: str, duplicate_result: DuplicationResult) -> str:
        """Assign article to appropriate cluster."""
        return self.cluster_manager.assign_cluster(article_id, duplicate_result)
    
    def _create_article_fingerprint(self, article_data: Dict[str, Any]) -> ArticleFingerprint:
        """Create article fingerprint for deduplication."""
        url = article_data.get('url', '')
        title = article_data.get('title', '')
        
        # Normalize title for comparison
        normalized_title = self._normalize_title(title)
        
        # Extract domain
        domain = self._extract_domain(url)
        
        # Parse publication date
        published_at = datetime.fromisoformat(
            article_data.get('published_at', datetime.utcnow().isoformat()).replace('Z', '+00:00')
        )
        
        # Generate hashes
        content_hash = article_data.get('content_hash', '')
        title_hash = hashlib.md5(normalized_title.encode()).hexdigest()
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        return ArticleFingerprint(
            article_id=article_data['article_id'],
            url=url,
            canonical_url=article_data.get('canonical_url', url),
            title=title,
            normalized_title=normalized_title,
            domain=domain,
            published_at=published_at,
            content_hash=content_hash,
            title_hash=title_hash,
            url_hash=url_hash
        )
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison."""
        # Convert to lowercase
        normalized = title.lower()
        
        # Remove common prefixes/suffixes
        prefixes = ['breaking:', 'urgent:', 'alert:', 'update:', 'exclusive:']
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
        
        # Remove punctuation and extra whitespace
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return ''
    
    def _get_existing_articles(self, published_at: datetime, 
                             days_back: int = 7) -> List[ArticleFingerprint]:
        """Get existing articles for comparison."""
        try:
            # Calculate time range
            start_time = published_at - timedelta(days=days_back)
            
            # Query DynamoDB for recent articles
            response = self.articles_table.scan(
                FilterExpression='published_at BETWEEN :start_time AND :end_time',
                ExpressionAttributeValues={
                    ':start_time': start_time.isoformat(),
                    ':end_time': published_at.isoformat()
                },
                ProjectionExpression='article_id, #url, canonical_url, title, published_at, content_hash'
            )
            
            articles = []
            for item in response.get('Items', []):
                try:
                    fingerprint = ArticleFingerprint(
                        article_id=item['article_id'],
                        url=item.get('url', ''),
                        canonical_url=item.get('canonical_url', item.get('url', '')),
                        title=item.get('title', ''),
                        normalized_title=self._normalize_title(item.get('title', '')),
                        domain=self._extract_domain(item.get('url', '')),
                        published_at=datetime.fromisoformat(item['published_at'].replace('Z', '+00:00')),
                        content_hash=item.get('content_hash', ''),
                        title_hash='',
                        url_hash=''
                    )
                    articles.append(fingerprint)
                except Exception as e:
                    logger.warning(f"Failed to process article {item.get('article_id')}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(articles)} existing articles for comparison")
            return articles
            
        except ClientError as e:
            logger.error(f"Failed to retrieve existing articles: {e}")
            return []


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for deduplication analysis.
    
    Expected event format:
    {
        "article_id": "string",
        "url": "string",
        "canonical_url": "string (optional)",
        "title": "string",
        "published_at": "ISO8601 datetime",
        "content_hash": "string",
        "normalized_content": "string"
    }
    """
    try:
        # Validate required parameters
        required_fields = ['article_id', 'url', 'title', 'published_at']
        for field in required_fields:
            if not event.get(field):
                raise ValueError(f"Required field '{field}' is missing")
        
        # Get configuration from environment
        import os
        articles_table_name = os.environ.get('ARTICLES_TABLE')
        opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        opensearch_index = os.environ.get('OPENSEARCH_INDEX_VECTORS', 'sentinel-vectors')
        
        if not articles_table_name:
            raise ValueError("ARTICLES_TABLE environment variable is required")
        
        if not opensearch_endpoint:
            logger.warning("OPENSEARCH_ENDPOINT not configured, semantic deduplication disabled")
            # Use dummy values for semantic deduplicator (it will handle the error gracefully)
            opensearch_endpoint = "dummy"
        
        # Initialize deduplication tool
        dedup_tool = DedupTool(articles_table_name, opensearch_endpoint, opensearch_index)
        
        # Perform deduplication analysis
        result = dedup_tool.find_duplicates(event)
        
        # Assign cluster if needed
        cluster_id = None
        if result.is_duplicate or not result.is_duplicate:  # Always assign cluster
            cluster_id = dedup_tool.assign_cluster(event['article_id'], result)
            result.cluster_id = cluster_id
        
        # Convert result to dictionary
        result_dict = asdict(result)
        
        return {
            'statusCode': 200,
            'body': {
                'success': True,
                'article_id': event['article_id'],
                'cluster_id': cluster_id,
                'result': result_dict
            }
        }
        
    except Exception as e:
        logger.error(f"Deduplication analysis failed: {e}")
        return {
            'statusCode': 500,
            'body': {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
        }


# For testing
if __name__ == "__main__":
    # Test event
    test_event = {
        "article_id": "test-article-123",
        "url": "https://example.com/security-breach-2024",
        "canonical_url": "https://example.com/security-breach-2024",
        "title": "Major Security Breach Affects Thousands of Users",
        "published_at": "2024-01-15T10:30:00Z",
        "content_hash": "abc123def456",
        "normalized_content": "A major security breach has been discovered affecting thousands of users..."
    }
    
    import os
    os.environ['ARTICLES_TABLE'] = 'test-articles'
    os.environ['OPENSEARCH_ENDPOINT'] = 'https://test-opensearch.us-east-1.es.amazonaws.com'
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))