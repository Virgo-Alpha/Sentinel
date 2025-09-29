"""
GuardrailTool Lambda tool for comprehensive content validation.

This Lambda function implements multi-layered content validation including JSON schema
validation, PII detection and redaction, CVE format validation, hallucination detection,
and bias/sensationalism filtering to ensure content quality and safety.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

import boto3
from botocore.exceptions import ClientError
import jsonschema
from jsonschema import validate, ValidationError

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# AWS clients
bedrock_client = boto3.client('bedrock-runtime')
comprehend_client = boto3.client('comprehend')


class GuardrailViolationType(str, Enum):
    """Types of guardrail violations."""
    SCHEMA_VIOLATION = "schema_violation"
    PII_DETECTED = "pii_detected"
    INVALID_CVE = "invalid_cve"
    HALLUCINATION = "hallucination"
    BIAS_DETECTED = "bias_detected"
    SENSATIONALISM = "sensationalism"
    BANNED_TERMS = "banned_terms"
    QUALITY_ISSUES = "quality_issues"


@dataclass
class GuardrailViolation:
    """Represents a specific guardrail violation."""
    violation_type: GuardrailViolationType
    severity: str  # "low", "medium", "high", "critical"
    description: str
    location: Optional[str] = None
    suggested_fix: Optional[str] = None
    confidence: float = 1.0


@dataclass
class PIIDetectionResult:
    """PII detection result."""
    has_pii: bool
    pii_entities: List[Dict[str, Any]]
    redacted_content: str
    confidence: float


@dataclass
class GuardrailResult:
    """Complete guardrail validation result."""
    passed: bool
    violations: List[GuardrailViolation]
    flags: List[str]
    confidence: float
    rationale: str
    redacted_content: Optional[str] = None


class GuardrailToolError(Exception):
    """Custom exception for guardrail validation errors."""
    pass


class JSONSchemaValidator:
    """Validates structured outputs against JSON schemas."""
    
    def __init__(self):
        self.schemas = self._load_schemas()
    
    def _load_schemas(self) -> Dict[str, Dict]:
        """Load JSON schemas for validation."""
        return {
            "article_schema": {
                "type": "object",
                "required": ["article_id", "title", "url", "published_at"],
                "properties": {
                    "article_id": {"type": "string", "minLength": 1},
                    "title": {"type": "string", "minLength": 1, "maxLength": 500},
                    "url": {"type": "string", "format": "uri"},
                    "published_at": {"type": "string", "format": "date-time"},
                    "relevancy_score": {"type": "number", "minimum": 0, "maximum": 1},
                    "entities": {
                        "type": "object",
                        "properties": {
                            "cves": {"type": "array", "items": {"type": "string"}},
                            "threat_actors": {"type": "array", "items": {"type": "string"}},
                            "malware": {"type": "array", "items": {"type": "string"}},
                            "vendors": {"type": "array", "items": {"type": "string"}},
                            "products": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            },
            "relevance_result_schema": {
                "type": "object",
                "required": ["is_relevant", "relevancy_score", "rationale"],
                "properties": {
                    "is_relevant": {"type": "boolean"},
                    "relevancy_score": {"type": "number", "minimum": 0, "maximum": 1},
                    "rationale": {"type": "string", "minLength": 10},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                }
            },
            "entity_extraction_schema": {
                "type": "object",
                "properties": {
                    "cves": {"type": "array", "items": {"type": "string", "pattern": "^CVE-\\d{4}-\\d{4,}$"}},
                    "threat_actors": {"type": "array", "items": {"type": "string"}},
                    "malware": {"type": "array", "items": {"type": "string"}},
                    "vendors": {"type": "array", "items": {"type": "string"}},
                    "products": {"type": "array", "items": {"type": "string"}},
                    "sectors": {"type": "array", "items": {"type": "string"}},
                    "countries": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
    
    def validate_schema(self, data: Dict[str, Any], schema_name: str) -> List[GuardrailViolation]:
        """
        Validate data against specified schema.
        
        Args:
            data: Data to validate
            schema_name: Name of schema to use
            
        Returns:
            List of violations found
        """
        violations = []
        
        try:
            if schema_name not in self.schemas:
                violations.append(GuardrailViolation(
                    violation_type=GuardrailViolationType.SCHEMA_VIOLATION,
                    severity="medium",
                    description=f"Unknown schema: {schema_name}",
                    confidence=1.0
                ))
                return violations
            
            schema = self.schemas[schema_name]
            validate(instance=data, schema=schema)
            
            logger.info(f"Schema validation passed for {schema_name}")
            
        except ValidationError as e:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.SCHEMA_VIOLATION,
                severity="high",
                description=f"Schema validation failed: {e.message}",
                location=f"Path: {'.'.join(str(p) for p in e.absolute_path)}",
                suggested_fix="Fix the data structure to match the required schema",
                confidence=1.0
            ))
            
        except Exception as e:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.SCHEMA_VIOLATION,
                severity="medium",
                description=f"Schema validation error: {str(e)}",
                confidence=0.8
            ))
        
        return violations


class PIIDetector:
    """Detects and redacts personally identifiable information."""
    
    def __init__(self):
        self.pii_patterns = self._compile_pii_patterns()
        self.sensitive_entity_types = [
            'PERSON', 'EMAIL', 'PHONE', 'SSN', 'CREDIT_CARD', 'BANK_ACCOUNT',
            'ADDRESS', 'DATE_TIME', 'PASSPORT_NUMBER', 'DRIVER_ID'
        ]
    
    def _compile_pii_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for PII detection."""
        return {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone': re.compile(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),
            'ssn': re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b'),
            'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
            'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
            'api_key': re.compile(r'\b[A-Za-z0-9]{32,}\b'),
            'password_hash': re.compile(r'\$[0-9a-z]+\$[0-9]+\$[A-Za-z0-9+/=.]{22,}'),
        }
    
    def detect_pii(self, content: str, title: str = "") -> PIIDetectionResult:
        """
        Detect PII in content using both regex patterns and AWS Comprehend.
        
        Args:
            content: Text content to analyze
            title: Optional title to analyze
            
        Returns:
            PIIDetectionResult with detection results and redacted content
        """
        try:
            full_text = f"{title}\n\n{content}" if title else content
            
            # Step 1: Pattern-based detection
            pattern_entities = self._detect_with_patterns(full_text)
            
            # Step 2: AWS Comprehend detection (if available)
            comprehend_entities = self._detect_with_comprehend(full_text)
            
            # Combine results
            all_entities = pattern_entities + comprehend_entities
            
            # Remove duplicates and sort by position
            unique_entities = self._deduplicate_entities(all_entities)
            
            # Generate redacted content
            redacted_content = self._redact_content(full_text, unique_entities)
            
            # Calculate confidence
            confidence = self._calculate_pii_confidence(unique_entities)
            
            return PIIDetectionResult(
                has_pii=len(unique_entities) > 0,
                pii_entities=unique_entities,
                redacted_content=redacted_content,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"PII detection failed: {e}")
            # Return safe default
            return PIIDetectionResult(
                has_pii=False,
                pii_entities=[],
                redacted_content=content,
                confidence=0.5
            )
    
    def _detect_with_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Detect PII using regex patterns."""
        entities = []
        
        for pii_type, pattern in self.pii_patterns.items():
            for match in pattern.finditer(text):
                entities.append({
                    'type': pii_type,
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.9,
                    'method': 'pattern'
                })
        
        return entities
    
    def _detect_with_comprehend(self, text: str) -> List[Dict[str, Any]]:
        """Detect PII using AWS Comprehend."""
        entities = []
        
        try:
            # Limit text length for Comprehend API
            if len(text) > 5000:
                text = text[:5000]
            
            response = comprehend_client.detect_pii_entities(
                Text=text,
                LanguageCode='en'
            )
            
            for entity in response.get('Entities', []):
                if entity['Type'] in self.sensitive_entity_types:
                    entities.append({
                        'type': entity['Type'].lower(),
                        'text': text[entity['BeginOffset']:entity['EndOffset']],
                        'start': entity['BeginOffset'],
                        'end': entity['EndOffset'],
                        'confidence': entity['Score'],
                        'method': 'comprehend'
                    })
                    
        except ClientError as e:
            logger.warning(f"Comprehend PII detection failed: {e}")
        except Exception as e:
            logger.warning(f"Comprehend PII detection error: {e}")
        
        return entities
    
    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate PII entities."""
        unique_entities = []
        seen_spans = set()
        
        # Sort by start position
        entities.sort(key=lambda x: x['start'])
        
        for entity in entities:
            span = (entity['start'], entity['end'])
            if span not in seen_spans:
                unique_entities.append(entity)
                seen_spans.add(span)
        
        return unique_entities
    
    def _redact_content(self, text: str, entities: List[Dict[str, Any]]) -> str:
        """Redact PII from content."""
        if not entities:
            return text
        
        # Sort entities by start position in reverse order
        entities.sort(key=lambda x: x['start'], reverse=True)
        
        redacted_text = text
        for entity in entities:
            redaction = f"[REDACTED_{entity['type'].upper()}]"
            redacted_text = (redacted_text[:entity['start']] + 
                           redaction + 
                           redacted_text[entity['end']:])
        
        return redacted_text
    
    def _calculate_pii_confidence(self, entities: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence in PII detection."""
        if not entities:
            return 1.0
        
        avg_confidence = sum(e['confidence'] for e in entities) / len(entities)
        return avg_confidence


class CVEValidator:
    """Validates CVE references and detects potential hallucinations."""
    
    def __init__(self):
        self.cve_pattern = re.compile(r'CVE-(\d{4})-(\d{4,})')
        self.known_cve_years = set(range(1999, datetime.now().year + 2))  # Allow next year
    
    def validate_cves(self, content: str, extracted_cves: List[str]) -> List[GuardrailViolation]:
        """
        Validate CVE references for format and potential hallucinations.
        
        Args:
            content: Original content to check
            extracted_cves: List of extracted CVE identifiers
            
        Returns:
            List of violations found
        """
        violations = []
        
        try:
            # Check format of extracted CVEs
            for cve in extracted_cves:
                format_violations = self._validate_cve_format(cve)
                violations.extend(format_violations)
            
            # Check for CVEs mentioned in content but not extracted
            content_cves = self._extract_cves_from_content(content)
            missing_cves = set(content_cves) - set(extracted_cves)
            
            if missing_cves:
                violations.append(GuardrailViolation(
                    violation_type=GuardrailViolationType.INVALID_CVE,
                    severity="medium",
                    description=f"CVEs found in content but not extracted: {list(missing_cves)}",
                    suggested_fix="Ensure all CVEs mentioned in content are properly extracted",
                    confidence=0.8
                ))
            
            # Check for potential hallucinated CVEs
            hallucination_violations = self._detect_cve_hallucinations(extracted_cves, content)
            violations.extend(hallucination_violations)
            
        except Exception as e:
            logger.error(f"CVE validation failed: {e}")
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.INVALID_CVE,
                severity="low",
                description=f"CVE validation error: {str(e)}",
                confidence=0.5
            ))
        
        return violations
    
    def _validate_cve_format(self, cve: str) -> List[GuardrailViolation]:
        """Validate CVE format."""
        violations = []
        
        match = self.cve_pattern.match(cve)
        if not match:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.INVALID_CVE,
                severity="high",
                description=f"Invalid CVE format: {cve}",
                suggested_fix="Use format CVE-YYYY-NNNN",
                confidence=1.0
            ))
            return violations
        
        year, number = match.groups()
        year = int(year)
        
        # Check year validity
        if year not in self.known_cve_years:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.INVALID_CVE,
                severity="medium",
                description=f"Suspicious CVE year: {cve} (year {year})",
                confidence=0.9
            ))
        
        # Check number format
        if len(number) < 4:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.INVALID_CVE,
                severity="medium",
                description=f"CVE number too short: {cve}",
                confidence=0.8
            ))
        
        return violations
    
    def _extract_cves_from_content(self, content: str) -> List[str]:
        """Extract CVE references from content."""
        matches = self.cve_pattern.findall(content)
        return [f"CVE-{year}-{number}" for year, number in matches]
    
    def _detect_cve_hallucinations(self, extracted_cves: List[str], content: str) -> List[GuardrailViolation]:
        """Detect potential CVE hallucinations."""
        violations = []
        
        for cve in extracted_cves:
            if cve not in content:
                violations.append(GuardrailViolation(
                    violation_type=GuardrailViolationType.HALLUCINATION,
                    severity="high",
                    description=f"Extracted CVE not found in content: {cve}",
                    suggested_fix="Verify CVE exists in source content",
                    confidence=0.9
                ))
        
        return violations


class BiasAndSensationalismDetector:
    """Detects bias and sensationalism in content."""
    
    def __init__(self):
        self.sensational_words = {
            'critical', 'urgent', 'breaking', 'shocking', 'devastating', 'catastrophic',
            'unprecedented', 'massive', 'huge', 'enormous', 'incredible', 'unbelievable',
            'exclusive', 'bombshell', 'explosive', 'alarming', 'terrifying'
        }
        
        self.bias_indicators = {
            'political': ['democrat', 'republican', 'liberal', 'conservative', 'leftist', 'rightist'],
            'emotional': ['outrageous', 'ridiculous', 'absurd', 'insane', 'crazy', 'stupid'],
            'absolute': ['always happens', 'never works', 'completely wrong', 'totally false', 'absolutely impossible']
        }
        
        self.banned_terms = {
            'offensive', 'discriminatory', 'hate speech', 'profanity'
        }
    
    def detect_bias_and_sensationalism(self, content: str, title: str = "") -> List[GuardrailViolation]:
        """
        Detect bias and sensationalism in content.
        
        Args:
            content: Text content to analyze
            title: Optional title to analyze
            
        Returns:
            List of violations found
        """
        violations = []
        full_text = f"{title}\n\n{content}" if title else content
        
        try:
            # Check for sensationalism
            sensational_violations = self._detect_sensationalism(full_text, title)
            violations.extend(sensational_violations)
            
            # Check for bias indicators
            bias_violations = self._detect_bias(full_text)
            violations.extend(bias_violations)
            
            # Check for banned terms
            banned_violations = self._detect_banned_terms(full_text)
            violations.extend(banned_violations)
            
            # Use LLM for advanced bias detection
            llm_violations = self._detect_bias_with_llm(content, title)
            violations.extend(llm_violations)
            
        except Exception as e:
            logger.error(f"Bias/sensationalism detection failed: {e}")
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.QUALITY_ISSUES,
                severity="low",
                description=f"Bias detection error: {str(e)}",
                confidence=0.5
            ))
        
        return violations
    
    def _detect_sensationalism(self, text: str, title: str) -> List[GuardrailViolation]:
        """Detect sensational language."""
        violations = []
        text_lower = text.lower()
        
        # Count sensational words in full text
        sensational_count = sum(1 for word in self.sensational_words if word in text_lower)
        
        # Check density in title (more critical)
        if title:
            title_words = len(title.split())
            title_lower = title.lower()
            title_sensational = sum(1 for word in self.sensational_words if word in title_lower)
            
            if title_words > 0 and title_sensational / title_words > 0.15:  # Lowered threshold
                violations.append(GuardrailViolation(
                    violation_type=GuardrailViolationType.SENSATIONALISM,
                    severity="medium",
                    description=f"High sensational word density in title: {title_sensational}/{title_words}",
                    suggested_fix="Use more neutral language in title",
                    confidence=0.8
                ))
        
        # Check overall density
        total_words = len(text.split())
        if total_words > 0 and sensational_count / total_words > 0.03:  # Lowered threshold
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.SENSATIONALISM,
                severity="low",
                description=f"High sensational word density: {sensational_count}/{total_words}",
                suggested_fix="Reduce use of sensational language",
                confidence=0.7
            ))
        
        return violations
    
    def _detect_bias(self, text: str) -> List[GuardrailViolation]:
        """Detect bias indicators."""
        violations = []
        text_lower = text.lower()
        
        for bias_type, indicators in self.bias_indicators.items():
            found_indicators = [word for word in indicators if word in text_lower]
            
            if found_indicators:
                violations.append(GuardrailViolation(
                    violation_type=GuardrailViolationType.BIAS_DETECTED,
                    severity="medium",
                    description=f"{bias_type.title()} bias indicators found: {found_indicators}",
                    suggested_fix="Use more neutral language",
                    confidence=0.6
                ))
        
        return violations
    
    def _detect_banned_terms(self, text: str) -> List[GuardrailViolation]:
        """Detect banned terms."""
        violations = []
        text_lower = text.lower()
        
        found_terms = [term for term in self.banned_terms if term in text_lower]
        
        if found_terms:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.BANNED_TERMS,
                severity="high",
                description=f"Banned terms found: {found_terms}",
                suggested_fix="Remove or replace banned terms",
                confidence=0.9
            ))
        
        return violations
    
    def _detect_bias_with_llm(self, content: str, title: str) -> List[GuardrailViolation]:
        """Use LLM for advanced bias detection."""
        violations = []
        
        try:
            prompt = f"""
Analyze the following cybersecurity article for bias, sensationalism, or inappropriate content.

Title: {title}

Content: {content[:2000]}

Check for:
1. Political or ideological bias
2. Sensational or exaggerated language
3. Emotional manipulation
4. Factual accuracy concerns
5. Professional tone appropriateness

Return your assessment in JSON format:
{{
    "has_bias": true/false,
    "bias_type": "political/emotional/sensational/none",
    "severity": "low/medium/high",
    "description": "Brief explanation",
    "confidence": 0.85
}}
"""
            
            response = bedrock_client.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                })
            )
            
            response_body = json.loads(response['body'].read())
            result_text = response_body['content'][0]['text']
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                
                if result.get('has_bias', False):
                    violations.append(GuardrailViolation(
                        violation_type=GuardrailViolationType.BIAS_DETECTED,
                        severity=result.get('severity', 'medium'),
                        description=f"LLM detected {result.get('bias_type', 'unknown')} bias: {result.get('description', '')}",
                        confidence=result.get('confidence', 0.7)
                    ))
                    
        except Exception as e:
            logger.warning(f"LLM bias detection failed: {e}")
        
        return violations


class GuardrailTool:
    """Main guardrail validation tool."""
    
    def __init__(self):
        self.schema_validator = JSONSchemaValidator()
        self.pii_detector = PIIDetector()
        self.cve_validator = CVEValidator()
        self.bias_detector = BiasAndSensationalismDetector()
    
    def validate_content(self, article_data: Dict[str, Any], 
                        validation_config: Optional[Dict[str, Any]] = None) -> GuardrailResult:
        """
        Perform comprehensive content validation.
        
        Args:
            article_data: Article data to validate
            validation_config: Optional validation configuration
            
        Returns:
            GuardrailResult with validation results
        """
        try:
            logger.info(f"Starting guardrail validation for article: {article_data.get('article_id')}")
            
            all_violations = []
            flags = []
            
            # Set default validation config if not provided
            if validation_config is None:
                validation_config = {
                    'validate_schema': True,
                    'detect_pii': True,
                    'validate_cves': True,
                    'detect_bias': True
                }
            
            # Extract content for validation
            content = article_data.get('normalized_content', '')
            title = article_data.get('title', '')
            
            # 1. JSON Schema Validation
            if validation_config.get('validate_schema', True):
                schema_violations = self.schema_validator.validate_schema(
                    article_data, 'article_schema'
                )
                all_violations.extend(schema_violations)
                if schema_violations:
                    flags.append('schema_issues')
            
            # 2. PII Detection and Redaction
            if validation_config.get('detect_pii', True):
                pii_result = self.pii_detector.detect_pii(content, title)
                if pii_result.has_pii:
                    all_violations.append(GuardrailViolation(
                        violation_type=GuardrailViolationType.PII_DETECTED,
                        severity="high",
                        description=f"PII detected: {len(pii_result.pii_entities)} entities",
                        suggested_fix="Review and redact PII before publication",
                        confidence=pii_result.confidence
                    ))
                    flags.append('pii_detected')
            
            # 3. CVE Validation
            if validation_config.get('validate_cves', True):
                extracted_cves = []
                entities = article_data.get('entities', {})
                if isinstance(entities, dict):
                    extracted_cves = entities.get('cves', [])
                
                cve_violations = self.cve_validator.validate_cves(content, extracted_cves)
                all_violations.extend(cve_violations)
                if cve_violations:
                    flags.append('cve_issues')
            
            # 4. Bias and Sensationalism Detection
            if validation_config.get('detect_bias', True):
                bias_violations = self.bias_detector.detect_bias_and_sensationalism(content, title)
                all_violations.extend(bias_violations)
                if bias_violations:
                    flags.append('bias_detected')
            
            # 5. Quality Checks
            quality_violations = self._perform_quality_checks(article_data)
            all_violations.extend(quality_violations)
            if quality_violations:
                flags.append('quality_issues')
            
            # Determine overall result
            passed = self._determine_pass_status(all_violations)
            confidence = self._calculate_overall_confidence(all_violations)
            rationale = self._generate_rationale(all_violations, passed)
            
            # Generate redacted content if PII was detected
            redacted_content = None
            if any(v.violation_type == GuardrailViolationType.PII_DETECTED for v in all_violations):
                pii_result = self.pii_detector.detect_pii(content, title)
                redacted_content = pii_result.redacted_content
            
            result = GuardrailResult(
                passed=passed,
                violations=all_violations,
                flags=flags,
                confidence=confidence,
                rationale=rationale,
                redacted_content=redacted_content
            )
            
            logger.info(f"Guardrail validation complete: passed={passed}, "
                       f"violations={len(all_violations)}, flags={flags}")
            
            return result
            
        except Exception as e:
            logger.error(f"Guardrail validation failed: {e}")
            raise GuardrailToolError(f"Validation failed: {e}")
    
    def _perform_quality_checks(self, article_data: Dict[str, Any]) -> List[GuardrailViolation]:
        """Perform basic quality checks."""
        violations = []
        
        # Check title length
        title = article_data.get('title', '')
        if len(title) < 10:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.QUALITY_ISSUES,
                severity="medium",
                description="Title too short",
                confidence=1.0
            ))
        elif len(title) > 200:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.QUALITY_ISSUES,
                severity="low",
                description="Title very long",
                confidence=0.8
            ))
        
        # Check content length
        content = article_data.get('normalized_content', '')
        if len(content) < 50:
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.QUALITY_ISSUES,
                severity="high",
                description="Content too short for meaningful analysis",
                confidence=1.0
            ))
        
        # Check URL validity
        url = article_data.get('url', '')
        if not url or not url.startswith(('http://', 'https://')):
            violations.append(GuardrailViolation(
                violation_type=GuardrailViolationType.QUALITY_ISSUES,
                severity="high",
                description="Invalid or missing URL",
                confidence=1.0
            ))
        
        return violations
    
    def _determine_pass_status(self, violations: List[GuardrailViolation]) -> bool:
        """Determine if content passes guardrail validation."""
        # Fail if any critical or high severity violations
        critical_violations = [v for v in violations if v.severity in ['critical', 'high']]
        
        # Allow some medium/low violations but not too many
        medium_violations = [v for v in violations if v.severity == 'medium']
        
        if critical_violations:
            return False
        
        if len(medium_violations) > 3:
            return False
        
        return True
    
    def _calculate_overall_confidence(self, violations: List[GuardrailViolation]) -> float:
        """Calculate overall confidence in validation."""
        if not violations:
            return 0.95
        
        # Average confidence of all violations
        avg_confidence = sum(v.confidence for v in violations) / len(violations)
        
        # Adjust based on number of violations
        confidence_penalty = min(0.3, len(violations) * 0.05)
        
        return max(0.5, avg_confidence - confidence_penalty)
    
    def _generate_rationale(self, violations: List[GuardrailViolation], passed: bool) -> str:
        """Generate rationale for validation result."""
        if not violations:
            return "Content passed all guardrail validations"
        
        violation_summary = {}
        for violation in violations:
            vtype = violation.violation_type.value
            if vtype not in violation_summary:
                violation_summary[vtype] = 0
            violation_summary[vtype] += 1
        
        summary_parts = [f"{count} {vtype}" for vtype, count in violation_summary.items()]
        
        if passed:
            return f"Content passed with minor issues: {', '.join(summary_parts)}"
        else:
            return f"Content failed validation due to: {', '.join(summary_parts)}"


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for guardrail validation.
    
    Expected event format:
    {
        "article_id": "string",
        "article_data": {
            "title": "string",
            "normalized_content": "string",
            "url": "string",
            "entities": {...},
            ...
        },
        "validation_config": {
            "validate_schema": true,
            "detect_pii": true,
            "validate_cves": true,
            "detect_bias": true
        }
    }
    """
    try:
        # Extract parameters
        article_id = event.get('article_id')
        article_data = event.get('article_data', {})
        validation_config = event.get('validation_config', {
            'validate_schema': True,
            'detect_pii': True,
            'validate_cves': True,
            'detect_bias': True
        })
        
        if not article_id or not article_data:
            raise ValueError("article_id and article_data are required")
        
        # Initialize guardrail tool and perform validation
        guardrail_tool = GuardrailTool()
        result = guardrail_tool.validate_content(article_data, validation_config)
        
        # Convert result to dictionary
        result_dict = {
            'passed': result.passed,
            'violations': [asdict(v) for v in result.violations],
            'flags': result.flags,
            'confidence': result.confidence,
            'rationale': result.rationale,
            'redacted_content': result.redacted_content
        }
        
        return {
            'statusCode': 200,
            'body': {
                'success': True,
                'article_id': article_id,
                'result': result_dict
            }
        }
        
    except Exception as e:
        logger.error(f"Guardrail validation failed: {e}")
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
        "article_data": {
            "title": "Critical Exchange Server Vulnerability Exploited by APT Group",
            "normalized_content": """
            A critical vulnerability (CVE-2024-1234) has been discovered in Microsoft Exchange Server 
            that allows remote code execution. The vulnerability affects Exchange Server 2019 and 2016. 
            Microsoft has released security updates to address this issue. The Lazarus Group APT has 
            been observed exploiting this vulnerability in targeted attacks against financial institutions.
            
            Contact john.doe@company.com for more information or call 555-123-4567.
            """,
            "url": "https://example.com/article",
            "entities": {
                "cves": ["CVE-2024-1234"],
                "threat_actors": ["Lazarus Group"],
                "vendors": ["Microsoft"],
                "products": ["Exchange Server"]
            }
        },
        "validation_config": {
            "validate_schema": True,
            "detect_pii": True,
            "validate_cves": True,
            "detect_bias": True
        }
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))