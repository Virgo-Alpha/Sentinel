"""
RelevancyEvaluator Lambda tool for assessing content relevance and extracting entities.

This Lambda function uses AWS Bedrock to assess cybersecurity content relevance,
perform keyword matching with hit counting and context extraction, and extract
structured entities like CVEs, threat actors, malware, vendors, and products.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# AWS clients
bedrock_client = boto3.client('bedrock-runtime')


@dataclass
class KeywordMatch:
    """Represents a keyword match with context."""
    keyword: str
    hit_count: int
    contexts: List[str]
    confidence: float


@dataclass
class EntityExtractionResult:
    """Represents extracted entities from content."""
    cves: List[str]
    threat_actors: List[str]
    malware: List[str]
    vendors: List[str]
    products: List[str]
    sectors: List[str]
    countries: List[str]


@dataclass
class RelevanceResult:
    """Represents the complete relevance assessment result."""
    is_relevant: bool
    relevancy_score: float
    keyword_matches: List[KeywordMatch]
    entities: EntityExtractionResult
    rationale: str
    confidence: float


class RelevancyEvaluatorError(Exception):
    """Custom exception for relevancy evaluation errors."""
    pass


class KeywordMatcher:
    """Handles keyword matching with context extraction."""
    
    def __init__(self):
        self.context_window = 50  # Characters around keyword match
    
    def find_keyword_matches(self, content: str, target_keywords: List[str]) -> List[KeywordMatch]:
        """
        Find keyword matches in content with context extraction.
        
        Args:
            content: Text content to search
            target_keywords: List of keywords to search for
            
        Returns:
            List of KeywordMatch objects
        """
        matches = []
        content_lower = content.lower()
        
        for keyword in target_keywords:
            keyword_lower = keyword.lower()
            
            # Find all occurrences
            hit_count = 0
            contexts = []
            start = 0
            
            while True:
                pos = content_lower.find(keyword_lower, start)
                if pos == -1:
                    break
                
                hit_count += 1
                
                # Extract context around the match
                context_start = max(0, pos - self.context_window)
                context_end = min(len(content), pos + len(keyword) + self.context_window)
                context = content[context_start:context_end].strip()
                
                # Clean up context
                context = re.sub(r'\s+', ' ', context)
                if context not in contexts:
                    contexts.append(context)
                
                start = pos + 1
            
            if hit_count > 0:
                # Calculate confidence based on exact vs fuzzy matching
                confidence = self._calculate_match_confidence(keyword, content, hit_count)
                
                matches.append(KeywordMatch(
                    keyword=keyword,
                    hit_count=hit_count,
                    contexts=contexts[:5],  # Limit to 5 contexts
                    confidence=confidence
                ))
        
        return matches
    
    def _calculate_match_confidence(self, keyword: str, content: str, hit_count: int) -> float:
        """Calculate confidence score for keyword match."""
        base_confidence = 0.8
        
        # Boost confidence for exact case matches
        if keyword in content:
            base_confidence += 0.1
        
        # Boost confidence for multiple hits
        if hit_count > 1:
            base_confidence += min(0.1, hit_count * 0.02)
        
        # Check for word boundaries (more precise matches)
        word_pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        if re.search(word_pattern, content.lower()):
            base_confidence += 0.05
        
        return min(1.0, base_confidence)


class BedrockEntityExtractor:
    """Uses AWS Bedrock to extract structured entities from content."""
    
    def __init__(self, model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"):
        self.model_id = model_id
        self.max_tokens = 4000
    
    def extract_entities(self, content: str, title: str = "") -> EntityExtractionResult:
        """
        Extract structured entities using Bedrock.
        
        Args:
            content: Text content to analyze
            title: Optional article title for context
            
        Returns:
            EntityExtractionResult with extracted entities
        """
        try:
            prompt = self._build_entity_extraction_prompt(content, title)
            
            response = bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.max_tokens,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.1,
                    "top_p": 0.9
                })
            )
            
            response_body = json.loads(response['body'].read())
            result_text = response_body['content'][0]['text']
            
            # Parse the structured response
            return self._parse_entity_response(result_text)
            
        except ClientError as e:
            logger.error(f"Bedrock API error: {e}")
            raise RelevancyEvaluatorError(f"Entity extraction failed: {e}")
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            raise RelevancyEvaluatorError(f"Entity extraction failed: {e}")
    
    def _build_entity_extraction_prompt(self, content: str, title: str) -> str:
        """Build prompt for entity extraction."""
        return f"""
You are a cybersecurity analyst tasked with extracting structured entities from cybersecurity news articles.

Article Title: {title}

Article Content:
{content[:3000]}  # Limit content to avoid token limits

Please extract the following entities from this cybersecurity article and return them in JSON format:

1. CVEs: Common Vulnerabilities and Exposures (format: CVE-YYYY-NNNN)
2. Threat Actors: Named threat groups, APT groups, or cybercriminal organizations
3. Malware: Named malware families, ransomware, trojans, etc.
4. Vendors: Technology vendors, security companies mentioned
5. Products: Specific software products, platforms, or services mentioned
6. Sectors: Industry sectors affected (e.g., healthcare, finance, government)
7. Countries: Countries mentioned in relation to threats or incidents

Return ONLY a JSON object with this exact structure:
{{
    "cves": ["CVE-2024-1234", "CVE-2024-5678"],
    "threat_actors": ["APT29", "Lazarus Group"],
    "malware": ["Emotet", "Cobalt Strike"],
    "vendors": ["Microsoft", "Cisco", "VMware"],
    "products": ["Windows", "Exchange Server", "vSphere"],
    "sectors": ["Healthcare", "Financial Services"],
    "countries": ["United States", "China", "Russia"]
}}

Important guidelines:
- Only include entities that are explicitly mentioned in the content
- Use proper capitalization and official names when possible
- For CVEs, ensure they follow the CVE-YYYY-NNNN format
- Do not include generic terms or categories
- If no entities are found for a category, use an empty array
- Be conservative - only include entities you are confident about
"""
    
    def _parse_entity_response(self, response_text: str) -> EntityExtractionResult:
        """Parse the JSON response from Bedrock."""
        try:
            # Extract JSON from response (handle potential markdown formatting)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                entities_dict = json.loads(json_str)
            else:
                # Fallback: try to parse the entire response as JSON
                entities_dict = json.loads(response_text)
            
            return EntityExtractionResult(
                cves=entities_dict.get('cves', []),
                threat_actors=entities_dict.get('threat_actors', []),
                malware=entities_dict.get('malware', []),
                vendors=entities_dict.get('vendors', []),
                products=entities_dict.get('products', []),
                sectors=entities_dict.get('sectors', []),
                countries=entities_dict.get('countries', [])
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse entity response as JSON: {e}")
            logger.warning(f"Response text: {response_text}")
            # Return empty result on parse failure
            return EntityExtractionResult([], [], [], [], [], [], [])
        except Exception as e:
            logger.error(f"Error parsing entity response: {e}")
            return EntityExtractionResult([], [], [], [], [], [], [])


class BedrockRelevanceAssessor:
    """Uses AWS Bedrock to assess content relevance to cybersecurity topics."""
    
    def __init__(self, model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"):
        self.model_id = model_id
        self.max_tokens = 2000
    
    def assess_relevance(self, content: str, title: str = "", 
                        keyword_matches: List[KeywordMatch] = None) -> Tuple[bool, float, str]:
        """
        Assess content relevance to cybersecurity topics.
        
        Args:
            content: Text content to analyze
            title: Optional article title
            keyword_matches: Optional keyword matches for context
            
        Returns:
            Tuple of (is_relevant, relevancy_score, rationale)
        """
        try:
            prompt = self._build_relevance_prompt(content, title, keyword_matches)
            
            response = bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.max_tokens,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.1,
                    "top_p": 0.9
                })
            )
            
            response_body = json.loads(response['body'].read())
            result_text = response_body['content'][0]['text']
            
            return self._parse_relevance_response(result_text)
            
        except ClientError as e:
            logger.error(f"Bedrock API error: {e}")
            raise RelevancyEvaluatorError(f"Relevance assessment failed: {e}")
        except Exception as e:
            logger.error(f"Relevance assessment error: {e}")
            raise RelevancyEvaluatorError(f"Relevance assessment failed: {e}")
    
    def _build_relevance_prompt(self, content: str, title: str, 
                               keyword_matches: List[KeywordMatch]) -> str:
        """Build prompt for relevance assessment."""
        keyword_info = ""
        if keyword_matches:
            keyword_info = f"\nKeyword Matches Found: {[m.keyword for m in keyword_matches]}"
        
        return f"""
You are a cybersecurity analyst tasked with determining if news articles are relevant to cybersecurity topics.

Article Title: {title}
{keyword_info}

Article Content:
{content[:2500]}  # Limit content to avoid token limits

Please assess whether this article is relevant to cybersecurity topics including:
- Data breaches and security incidents
- Vulnerabilities and CVEs
- Malware and ransomware
- Threat actors and APT groups
- Security tools and technologies
- Cybersecurity policies and regulations
- Security research and analysis

Return your assessment in this exact JSON format:
{{
    "is_relevant": true/false,
    "relevancy_score": 0.85,
    "rationale": "Brief explanation of why this article is or isn't relevant to cybersecurity"
}}

Guidelines:
- relevancy_score should be between 0.0 and 1.0
- Score 0.8+ for highly relevant cybersecurity content
- Score 0.6-0.8 for moderately relevant content
- Score 0.4-0.6 for tangentially related content
- Score below 0.4 for irrelevant content
- Consider keyword matches as positive indicators
- Be conservative but not overly restrictive
"""
    
    def _parse_relevance_response(self, response_text: str) -> Tuple[bool, float, str]:
        """Parse the relevance assessment response."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result_dict = json.loads(json_str)
            else:
                result_dict = json.loads(response_text)
            
            is_relevant = result_dict.get('is_relevant', False)
            relevancy_score = float(result_dict.get('relevancy_score', 0.0))
            rationale = result_dict.get('rationale', 'No rationale provided')
            
            # Ensure score is within valid range
            relevancy_score = max(0.0, min(1.0, relevancy_score))
            
            return is_relevant, relevancy_score, rationale
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse relevance response: {e}")
            logger.warning(f"Response text: {response_text}")
            # Return conservative default
            return False, 0.0, "Failed to parse relevance assessment"


class RelevancyEvaluator:
    """Main relevancy evaluator class."""
    
    def __init__(self):
        self.keyword_matcher = KeywordMatcher()
        self.entity_extractor = BedrockEntityExtractor()
        self.relevance_assessor = BedrockRelevanceAssessor()
    
    def evaluate_relevance(self, content: str, title: str = "", 
                          target_keywords: List[str] = None) -> RelevanceResult:
        """
        Perform comprehensive relevance evaluation.
        
        Args:
            content: Article content to evaluate
            title: Article title
            target_keywords: List of target keywords to match
            
        Returns:
            RelevanceResult with complete assessment
        """
        try:
            logger.info(f"Evaluating relevance for article: {title[:100]}...")
            
            # Step 1: Keyword matching
            keyword_matches = []
            if target_keywords:
                keyword_matches = self.keyword_matcher.find_keyword_matches(content, target_keywords)
                logger.info(f"Found {len(keyword_matches)} keyword matches")
            
            # Step 2: Entity extraction
            entities = self.entity_extractor.extract_entities(content, title)
            logger.info(f"Extracted entities: CVEs={len(entities.cves)}, "
                       f"Actors={len(entities.threat_actors)}, Malware={len(entities.malware)}")
            
            # Step 3: Relevance assessment
            is_relevant, relevancy_score, rationale = self.relevance_assessor.assess_relevance(
                content, title, keyword_matches
            )
            
            # Step 4: Calculate overall confidence
            confidence = self._calculate_overall_confidence(
                keyword_matches, entities, relevancy_score
            )
            
            # Step 5: Adjust relevancy score based on keyword matches
            adjusted_score = self._adjust_score_for_keywords(relevancy_score, keyword_matches)
            
            result = RelevanceResult(
                is_relevant=is_relevant,
                relevancy_score=adjusted_score,
                keyword_matches=keyword_matches,
                entities=entities,
                rationale=rationale,
                confidence=confidence
            )
            
            logger.info(f"Relevance evaluation complete: relevant={is_relevant}, "
                       f"score={adjusted_score:.2f}, confidence={confidence:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Relevance evaluation failed: {e}")
            raise RelevancyEvaluatorError(f"Evaluation failed: {e}")
    
    def _calculate_overall_confidence(self, keyword_matches: List[KeywordMatch], 
                                    entities: EntityExtractionResult, 
                                    relevancy_score: float) -> float:
        """Calculate overall confidence in the assessment."""
        base_confidence = 0.7
        
        # Boost confidence for keyword matches
        if keyword_matches:
            avg_keyword_confidence = sum(m.confidence for m in keyword_matches) / len(keyword_matches)
            base_confidence += avg_keyword_confidence * 0.1
        
        # Boost confidence for entity extraction
        total_entities = (len(entities.cves) + len(entities.threat_actors) + 
                         len(entities.malware) + len(entities.vendors) + len(entities.products))
        if total_entities > 0:
            base_confidence += min(0.15, total_entities * 0.03)
        
        # Boost confidence for high relevancy scores
        if relevancy_score > 0.8:
            base_confidence += 0.1
        elif relevancy_score > 0.6:
            base_confidence += 0.05
        
        return min(1.0, base_confidence)
    
    def _adjust_score_for_keywords(self, base_score: float, 
                                  keyword_matches: List[KeywordMatch]) -> float:
        """Adjust relevancy score based on keyword matches."""
        if not keyword_matches:
            return base_score
        
        # Calculate keyword boost
        total_hits = sum(m.hit_count for m in keyword_matches)
        keyword_boost = min(0.2, total_hits * 0.05)  # Max boost of 0.2
        
        # Apply boost
        adjusted_score = base_score + keyword_boost
        
        return min(1.0, adjusted_score)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for relevancy evaluation.
    
    Expected event format:
    {
        "article_id": "string",
        "content": "string",
        "title": "string (optional)",
        "target_keywords": ["string"] (optional)
    }
    """
    try:
        # Extract parameters
        article_id = event.get('article_id')
        content = event.get('content')
        title = event.get('title', '')
        target_keywords = event.get('target_keywords', [])
        
        if not article_id or not content:
            raise ValueError("article_id and content are required")
        
        # Initialize evaluator and perform assessment
        evaluator = RelevancyEvaluator()
        result = evaluator.evaluate_relevance(content, title, target_keywords)
        
        # Convert result to dictionary
        result_dict = asdict(result)
        
        return {
            'statusCode': 200,
            'body': {
                'success': True,
                'article_id': article_id,
                'result': result_dict
            }
        }
        
    except Exception as e:
        logger.error(f"Relevancy evaluation failed: {e}")
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
        "content": """
        A critical vulnerability (CVE-2024-1234) has been discovered in Microsoft Exchange Server 
        that allows remote code execution. The vulnerability affects Exchange Server 2019 and 2016. 
        Microsoft has released security updates to address this issue. The Lazarus Group APT has 
        been observed exploiting this vulnerability in targeted attacks against financial institutions.
        """,
        "title": "Critical Exchange Server Vulnerability Exploited by APT Group",
        "target_keywords": ["Microsoft", "Exchange Server", "CVE", "APT", "vulnerability"]
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))