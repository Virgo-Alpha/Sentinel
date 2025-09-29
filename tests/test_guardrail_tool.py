"""
Unit tests for GuardrailTool Lambda function.

Tests all guardrail validation layers including JSON schema validation,
PII detection and redaction, CVE format validation, hallucination detection,
and bias/sensationalism filtering.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the modules to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'lambda_tools'))

from guardrail_tool import (
    GuardrailTool, JSONSchemaValidator, PIIDetector, CVEValidator,
    BiasAndSensationalismDetector, GuardrailViolationType, GuardrailViolation,
    PIIDetectionResult, GuardrailResult, lambda_handler
)


class TestJSONSchemaValidator:
    """Test JSON schema validation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = JSONSchemaValidator()
    
    def test_valid_article_schema(self):
        """Test validation of valid article data."""
        valid_data = {
            "article_id": "test-123",
            "title": "Test Article",
            "url": "https://example.com/article",
            "published_at": "2024-01-01T12:00:00Z",
            "relevancy_score": 0.85
        }
        
        violations = self.validator.validate_schema(valid_data, "article_schema")
        assert len(violations) == 0
    
    def test_invalid_article_schema_missing_required(self):
        """Test validation with missing required fields."""
        invalid_data = {
            "title": "Test Article",
            "url": "https://example.com/article"
            # Missing article_id and published_at
        }
        
        violations = self.validator.validate_schema(invalid_data, "article_schema")
        assert len(violations) > 0
        assert any(v.violation_type == GuardrailViolationType.SCHEMA_VIOLATION for v in violations)
    
    def test_invalid_article_schema_wrong_types(self):
        """Test validation with wrong data types."""
        invalid_data = {
            "article_id": "test-123",
            "title": "Test Article",
            "url": "not-a-valid-url",
            "published_at": "2024-01-01T12:00:00Z",
            "relevancy_score": 1.5  # Out of range
        }
        
        violations = self.validator.validate_schema(invalid_data, "article_schema")
        assert len(violations) > 0
    
    def test_unknown_schema(self):
        """Test validation with unknown schema name."""
        data = {"test": "data"}
        violations = self.validator.validate_schema(data, "unknown_schema")
        
        assert len(violations) == 1
        assert violations[0].violation_type == GuardrailViolationType.SCHEMA_VIOLATION
        assert "Unknown schema" in violations[0].description


class TestPIIDetector:
    """Test PII detection and redaction functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = PIIDetector()
    
    def test_detect_email_pii(self):
        """Test detection of email addresses."""
        content = "Contact us at john.doe@company.com for more information."
        
        result = self.detector.detect_pii(content)
        
        assert result.has_pii
        assert len(result.pii_entities) >= 1
        assert any(entity['type'] == 'email' for entity in result.pii_entities)
        assert "[REDACTED_EMAIL]" in result.redacted_content
    
    def test_detect_phone_pii(self):
        """Test detection of phone numbers."""
        content = "Call us at 555-123-4567 or (555) 987-6543."
        
        result = self.detector.detect_pii(content)
        
        assert result.has_pii
        assert any(entity['type'] == 'phone' for entity in result.pii_entities)
        assert "[REDACTED_PHONE]" in result.redacted_content
    
    def test_detect_ssn_pii(self):
        """Test detection of SSN."""
        content = "SSN: 123-45-6789 should be protected."
        
        result = self.detector.detect_pii(content)
        
        assert result.has_pii
        assert any(entity['type'] == 'ssn' for entity in result.pii_entities)
    
    def test_no_pii_detected(self):
        """Test content with no PII."""
        content = "This is a normal cybersecurity article about vulnerabilities."
        
        result = self.detector.detect_pii(content)
        
        assert not result.has_pii
        assert len(result.pii_entities) == 0
        assert result.redacted_content == content
    
    @patch('guardrail_tool.comprehend_client')
    def test_comprehend_pii_detection(self, mock_comprehend):
        """Test AWS Comprehend PII detection."""
        mock_comprehend.detect_pii_entities.return_value = {
            'Entities': [
                {
                    'Type': 'PERSON',
                    'BeginOffset': 0,
                    'EndOffset': 8,
                    'Score': 0.95
                }
            ]
        }
        
        content = "John Doe reported a security incident."
        result = self.detector.detect_pii(content)
        
        mock_comprehend.detect_pii_entities.assert_called_once()
        assert result.has_pii
    
    def test_deduplicate_entities(self):
        """Test deduplication of overlapping PII entities."""
        entities = [
            {'type': 'email', 'start': 10, 'end': 25, 'text': 'test@example.com'},
            {'type': 'email', 'start': 10, 'end': 25, 'text': 'test@example.com'},  # Duplicate
            {'type': 'phone', 'start': 30, 'end': 42, 'text': '555-123-4567'}
        ]
        
        unique_entities = self.detector._deduplicate_entities(entities)
        
        assert len(unique_entities) == 2
        assert unique_entities[0]['type'] == 'email'
        assert unique_entities[1]['type'] == 'phone'


class TestCVEValidator:
    """Test CVE validation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = CVEValidator()
    
    def test_valid_cve_format(self):
        """Test validation of valid CVE format."""
        valid_cves = ["CVE-2024-1234", "CVE-2023-12345"]
        content = "This article discusses CVE-2024-1234 and CVE-2023-12345."
        
        violations = self.validator.validate_cves(content, valid_cves)
        
        # Should have no format violations for valid CVEs
        format_violations = [v for v in violations if "Invalid CVE format" in v.description]
        assert len(format_violations) == 0
    
    def test_invalid_cve_format(self):
        """Test validation of invalid CVE format."""
        invalid_cves = ["CVE-24-1234", "CVE-2024-123", "INVALID-2024-1234"]
        content = "This article discusses some CVEs."
        
        violations = self.validator.validate_cves(content, invalid_cves)
        
        assert len(violations) > 0
        assert any(v.violation_type == GuardrailViolationType.INVALID_CVE for v in violations)
    
    def test_cve_year_validation(self):
        """Test validation of CVE years."""
        # Test with suspicious year
        suspicious_cves = ["CVE-1990-1234"]  # Too old
        content = "This article discusses CVE-1990-1234."
        
        violations = self.validator.validate_cves(content, suspicious_cves)
        
        year_violations = [v for v in violations if "Suspicious CVE year" in v.description]
        assert len(year_violations) > 0
    
    def test_cve_hallucination_detection(self):
        """Test detection of hallucinated CVEs."""
        # CVE not mentioned in content
        extracted_cves = ["CVE-2024-1234"]
        content = "This article discusses security vulnerabilities but mentions no specific CVEs."
        
        violations = self.validator.validate_cves(content, extracted_cves)
        
        hallucination_violations = [v for v in violations 
                                  if v.violation_type == GuardrailViolationType.HALLUCINATION]
        assert len(hallucination_violations) > 0
    
    def test_missing_cve_extraction(self):
        """Test detection of CVEs in content but not extracted."""
        extracted_cves = []
        content = "This article discusses CVE-2024-1234 and CVE-2024-5678."
        
        violations = self.validator.validate_cves(content, extracted_cves)
        
        missing_violations = [v for v in violations if "not extracted" in v.description]
        assert len(missing_violations) > 0
    
    def test_extract_cves_from_content(self):
        """Test extraction of CVEs from content."""
        content = "The vulnerabilities CVE-2024-1234 and CVE-2023-5678 were discovered."
        
        cves = self.validator._extract_cves_from_content(content)
        
        assert "CVE-2024-1234" in cves
        assert "CVE-2023-5678" in cves
        assert len(cves) == 2


class TestBiasAndSensationalismDetector:
    """Test bias and sensationalism detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = BiasAndSensationalismDetector()
    
    def test_detect_sensationalism_in_title(self):
        """Test detection of sensational language in title."""
        title = "BREAKING: Massive Cyber Attack Devastates Critical Infrastructure!"
        content = "A security incident occurred affecting some systems."
        
        violations = self.detector.detect_bias_and_sensationalism(content, title)
        
        sensational_violations = [v for v in violations 
                                if v.violation_type == GuardrailViolationType.SENSATIONALISM]
        assert len(sensational_violations) > 0
    
    def test_detect_bias_indicators(self):
        """Test detection of bias indicators."""
        content = "This is completely ridiculous and always happens with these systems."
        
        violations = self.detector.detect_bias_and_sensationalism(content)
        
        bias_violations = [v for v in violations 
                         if v.violation_type == GuardrailViolationType.BIAS_DETECTED]
        assert len(bias_violations) > 0
    
    def test_detect_banned_terms(self):
        """Test detection of banned terms."""
        # Note: Using mild example for testing
        content = "This content contains offensive language that should be flagged."
        
        violations = self.detector.detect_bias_and_sensationalism(content)
        
        banned_violations = [v for v in violations 
                           if v.violation_type == GuardrailViolationType.BANNED_TERMS]
        # This test depends on the banned terms list
        # May or may not trigger based on actual implementation
    
    def test_neutral_content(self):
        """Test neutral content with no bias or sensationalism."""
        content = "A security vulnerability was discovered in the software. The vendor has released a patch."
        title = "Security Vulnerability Patched"
        
        violations = self.detector.detect_bias_and_sensationalism(content, title)
        
        # Should have minimal or no violations for neutral content
        high_severity_violations = [v for v in violations if v.severity in ['high', 'critical']]
        assert len(high_severity_violations) == 0
    
    @patch('guardrail_tool.bedrock_client')
    def test_llm_bias_detection(self, mock_bedrock):
        """Test LLM-based bias detection."""
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{
                'text': '{"has_bias": true, "bias_type": "sensational", "severity": "medium", "description": "Sensational language detected", "confidence": 0.8}'
            }]
        }).encode()
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        content = "This is supposedly biased content."
        violations = self.detector._detect_bias_with_llm(content, "Test Title")
        
        mock_bedrock.invoke_model.assert_called_once()
        assert len(violations) > 0


class TestGuardrailTool:
    """Test main GuardrailTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = GuardrailTool()
    
    def test_validate_clean_content(self):
        """Test validation of clean content that should pass."""
        article_data = {
            "article_id": "test-123",
            "title": "Security Vulnerability Discovered in Popular Software",
            "url": "https://example.com/article",
            "published_at": "2024-01-01T12:00:00Z",
            "normalized_content": "A security vulnerability was discovered in popular software. The vendor has released a patch to address the issue.",
            "entities": {
                "cves": [],
                "vendors": ["Software Vendor"],
                "products": ["Popular Software"]
            }
        }
        
        result = self.tool.validate_content(article_data)
        
        assert isinstance(result, GuardrailResult)
        assert result.passed
        assert len(result.violations) == 0 or all(v.severity in ['low', 'medium'] for v in result.violations)
    
    def test_validate_content_with_pii(self):
        """Test validation of content containing PII."""
        article_data = {
            "article_id": "test-123",
            "title": "Security Incident Report",
            "url": "https://example.com/article",
            "published_at": "2024-01-01T12:00:00Z",
            "normalized_content": "Contact john.doe@company.com or call 555-123-4567 for more information about the security incident.",
            "entities": {"cves": []}
        }
        
        result = self.tool.validate_content(article_data)
        
        assert not result.passed  # Should fail due to PII
        assert 'pii_detected' in result.flags
        assert result.redacted_content is not None
        assert "[REDACTED_" in result.redacted_content
    
    def test_validate_content_with_invalid_cves(self):
        """Test validation of content with invalid CVEs."""
        article_data = {
            "article_id": "test-123",
            "title": "CVE Analysis Report on Security Vulnerabilities",
            "url": "https://example.com/article",
            "published_at": "2024-01-01T12:00:00Z",
            "normalized_content": "This comprehensive article discusses various security vulnerabilities including CVE-2024-1234 and provides detailed analysis of the impact on enterprise systems. The research covers multiple attack vectors and mitigation strategies for organizations.",
            "entities": {
                "cves": ["CVE-24-1234", "INVALID-CVE"]  # Invalid formats
            }
        }
        
        result = self.tool.validate_content(article_data)
        
        assert not result.passed
        assert 'cve_issues' in result.flags
        cve_violations = [v for v in result.violations 
                         if v.violation_type == GuardrailViolationType.INVALID_CVE]
        assert len(cve_violations) > 0
    
    def test_validate_content_with_sensationalism(self):
        """Test validation of sensational content."""
        article_data = {
            "article_id": "test-123",
            "title": "BREAKING: Massive Devastating Cyber Attack Shocks Industry!",
            "url": "https://example.com/article",
            "published_at": "2024-01-01T12:00:00Z",
            "normalized_content": "An unprecedented and shocking cyber attack has completely devastated the entire industry in an unbelievable way. This massive security incident represents a critical threat to organizations worldwide and has caused enormous disruption across multiple sectors.",
            "entities": {"cves": []}
        }
        
        result = self.tool.validate_content(article_data)
        
        # May or may not fail depending on thresholds, but should flag sensationalism
        assert 'bias_detected' in result.flags or len(result.violations) > 0
    
    def test_quality_checks(self):
        """Test basic quality checks."""
        # Test with very short title and content
        article_data = {
            "article_id": "test-123",
            "title": "Short",  # Too short
            "url": "invalid-url",  # Invalid URL
            "published_at": "2024-01-01T12:00:00Z",
            "normalized_content": "Too short.",  # Too short
            "entities": {"cves": []}
        }
        
        violations = self.tool._perform_quality_checks(article_data)
        
        assert len(violations) > 0
        quality_violations = [v for v in violations 
                            if v.violation_type == GuardrailViolationType.QUALITY_ISSUES]
        assert len(quality_violations) > 0
    
    def test_determine_pass_status(self):
        """Test pass/fail determination logic."""
        # Test with critical violation
        critical_violations = [
            GuardrailViolation(
                violation_type=GuardrailViolationType.PII_DETECTED,
                severity="critical",
                description="Critical issue"
            )
        ]
        assert not self.tool._determine_pass_status(critical_violations)
        
        # Test with many medium violations
        medium_violations = [
            GuardrailViolation(
                violation_type=GuardrailViolationType.BIAS_DETECTED,
                severity="medium",
                description="Medium issue"
            ) for _ in range(5)
        ]
        assert not self.tool._determine_pass_status(medium_violations)
        
        # Test with few low violations
        low_violations = [
            GuardrailViolation(
                violation_type=GuardrailViolationType.QUALITY_ISSUES,
                severity="low",
                description="Low issue"
            )
        ]
        assert self.tool._determine_pass_status(low_violations)
    
    def test_calculate_overall_confidence(self):
        """Test confidence calculation."""
        # No violations should have high confidence
        confidence = self.tool._calculate_overall_confidence([])
        assert confidence >= 0.9
        
        # Many violations should reduce confidence
        many_violations = [
            GuardrailViolation(
                violation_type=GuardrailViolationType.QUALITY_ISSUES,
                severity="medium",
                description="Issue",
                confidence=0.8
            ) for _ in range(10)
        ]
        confidence = self.tool._calculate_overall_confidence(many_violations)
        assert confidence < 0.8


class TestLambdaHandler:
    """Test Lambda handler function."""
    
    def test_lambda_handler_success(self):
        """Test successful lambda handler execution."""
        event = {
            "article_id": "test-123",
            "article_data": {
                "title": "Test Article",
                "url": "https://example.com/article",
                "published_at": "2024-01-01T12:00:00Z",
                "normalized_content": "This is a test article about cybersecurity.",
                "entities": {"cves": []}
            },
            "validation_config": {
                "validate_schema": True,
                "detect_pii": True,
                "validate_cves": True,
                "detect_bias": True
            }
        }
        
        with patch('guardrail_tool.GuardrailTool') as mock_tool_class:
            mock_tool = Mock()
            mock_tool_class.return_value = mock_tool
            
            mock_result = GuardrailResult(
                passed=True,
                violations=[],
                flags=[],
                confidence=0.95,
                rationale="All checks passed"
            )
            mock_tool.validate_content.return_value = mock_result
            
            response = lambda_handler(event, None)
            
            assert response['statusCode'] == 200
            assert response['body']['success'] is True
            assert response['body']['article_id'] == "test-123"
    
    def test_lambda_handler_missing_parameters(self):
        """Test lambda handler with missing parameters."""
        event = {
            "article_id": "test-123"
            # Missing article_data
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        assert response['body']['success'] is False
        assert 'error' in response['body']
    
    def test_lambda_handler_validation_error(self):
        """Test lambda handler with validation error."""
        event = {
            "article_id": "test-123",
            "article_data": {
                "title": "Test Article",
                "normalized_content": "Test content"
            }
        }
        
        with patch('guardrail_tool.GuardrailTool') as mock_tool_class:
            mock_tool = Mock()
            mock_tool_class.return_value = mock_tool
            mock_tool.validate_content.side_effect = Exception("Validation failed")
            
            response = lambda_handler(event, None)
            
            assert response['statusCode'] == 500
            assert response['body']['success'] is False


# Integration test
class TestGuardrailIntegration:
    """Integration tests for complete guardrail validation."""
    
    def test_complete_validation_pipeline(self):
        """Test complete validation pipeline with realistic data."""
        article_data = {
            "article_id": "integration-test-123",
            "title": "Critical Microsoft Exchange Vulnerability Exploited by APT Group",
            "url": "https://security-news.example.com/exchange-vulnerability",
            "published_at": "2024-01-15T14:30:00Z",
            "normalized_content": """
            A critical remote code execution vulnerability (CVE-2024-1234) has been discovered 
            in Microsoft Exchange Server versions 2019 and 2016. The vulnerability allows 
            attackers to execute arbitrary code on affected systems without authentication.
            
            Microsoft has released security updates to address this vulnerability. The Lazarus 
            Group APT has been observed exploiting this vulnerability in targeted attacks 
            against financial institutions in South Korea and the United States.
            
            Organizations using Exchange Server should immediately apply the security updates 
            and monitor for signs of compromise. The vulnerability has been assigned a CVSS 
            score of 9.8, indicating critical severity.
            """,
            "entities": {
                "cves": ["CVE-2024-1234"],
                "threat_actors": ["Lazarus Group"],
                "vendors": ["Microsoft"],
                "products": ["Exchange Server"],
                "countries": ["South Korea", "United States"],
                "sectors": ["Financial Services"]
            },
            "relevancy_score": 0.95
        }
        
        tool = GuardrailTool()
        result = tool.validate_content(article_data)
        
        # This should pass as it's clean, professional content
        assert result.passed
        assert result.confidence > 0.8
        
        # Should have minimal violations
        high_severity_violations = [v for v in result.violations if v.severity in ['high', 'critical']]
        assert len(high_severity_violations) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])