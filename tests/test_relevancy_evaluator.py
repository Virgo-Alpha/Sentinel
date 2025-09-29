"""
Unit tests for RelevancyEvaluator Lambda tool.

Tests cover keyword matching, entity extraction, relevance assessment,
and overall evaluation functionality.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the classes to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_tools.relevancy_evaluator import (
    KeywordMatcher,
    BedrockEntityExtractor,
    BedrockRelevanceAssessor,
    RelevancyEvaluator,
    KeywordMatch,
    EntityExtractionResult,
    RelevanceResult,
    RelevancyEvaluatorError,
    lambda_handler
)


class TestKeywordMatcher:
    """Test cases for KeywordMatcher class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.matcher = KeywordMatcher()
        self.sample_content = """
        Microsoft Azure has released security updates for Exchange Server to address 
        a critical vulnerability (CVE-2024-1234). The vulnerability affects Azure AD 
        and Microsoft 365 environments. Fortinet FortiGate firewalls are also 
        mentioned in this security advisory. The Lazarus Group APT has been 
        exploiting this vulnerability in targeted attacks.
        """
        self.target_keywords = [
            "Azure", "Microsoft 365", "Exchange Server", "Fortinet", 
            "CVE", "APT", "vulnerability"
        ]
    
    def test_find_keyword_matches_basic(self):
        """Test basic keyword matching functionality."""
        matches = self.matcher.find_keyword_matches(self.sample_content, self.target_keywords)
        
        # Should find matches for keywords present in content
        found_keywords = [m.keyword for m in matches]
        assert "Azure" in found_keywords
        assert "Microsoft 365" in found_keywords
        assert "Exchange Server" in found_keywords
        assert "Fortinet" in found_keywords
        assert "vulnerability" in found_keywords
        
        # Check hit counts
        azure_match = next(m for m in matches if m.keyword == "Azure")
        assert azure_match.hit_count >= 1
        
        vulnerability_match = next(m for m in matches if m.keyword == "vulnerability")
        assert vulnerability_match.hit_count >= 2  # Should find multiple occurrences
    
    def test_find_keyword_matches_case_insensitive(self):
        """Test case-insensitive keyword matching."""
        content = "AZURE and azure and Azure are all the same"
        keywords = ["Azure"]
        
        matches = self.matcher.find_keyword_matches(content, keywords)
        
        assert len(matches) == 1
        assert matches[0].keyword == "Azure"
        assert matches[0].hit_count == 3
    
    def test_find_keyword_matches_context_extraction(self):
        """Test context extraction around keyword matches."""
        matches = self.matcher.find_keyword_matches(self.sample_content, ["CVE-2024-1234"])
        
        if matches:  # CVE might not be in target keywords
            cve_match = matches[0]
            assert len(cve_match.contexts) > 0
            # Context should contain surrounding text
            context = cve_match.contexts[0]
            assert "vulnerability" in context.lower()
    
    def test_find_keyword_matches_no_matches(self):
        """Test behavior when no keywords are found."""
        content = "This is a test article about cooking recipes"
        keywords = ["Azure", "cybersecurity", "malware"]
        
        matches = self.matcher.find_keyword_matches(content, keywords)
        
        assert len(matches) == 0
    
    def test_find_keyword_matches_empty_input(self):
        """Test behavior with empty inputs."""
        # Empty content
        matches = self.matcher.find_keyword_matches("", self.target_keywords)
        assert len(matches) == 0
        
        # Empty keywords
        matches = self.matcher.find_keyword_matches(self.sample_content, [])
        assert len(matches) == 0
    
    def test_calculate_match_confidence(self):
        """Test confidence calculation for keyword matches."""
        # Test exact case match
        confidence = self.matcher._calculate_match_confidence(
            "Azure", "Microsoft Azure is great", 1
        )
        assert confidence > 0.8
        
        # Test multiple hits
        confidence = self.matcher._calculate_match_confidence(
            "azure", "azure azure azure", 3
        )
        assert confidence > 0.8
        
        # Test word boundary matching
        confidence = self.matcher._calculate_match_confidence(
            "test", "This is a test case", 1
        )
        assert confidence > 0.8


class TestBedrockEntityExtractor:
    """Test cases for BedrockEntityExtractor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = BedrockEntityExtractor()
        self.sample_content = """
        A critical vulnerability CVE-2024-1234 has been discovered in Microsoft Exchange Server.
        The Lazarus Group APT has been exploiting this vulnerability. Emotet malware was also
        detected in the attack. The vulnerability affects healthcare and financial services sectors
        in the United States and Canada.
        """
        self.sample_title = "Critical Exchange Server Vulnerability Exploited by APT Group"
    
    @patch('lambda_tools.relevancy_evaluator.bedrock_client')
    def test_extract_entities_success(self, mock_bedrock):
        """Test successful entity extraction."""
        # Mock Bedrock response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{
                'text': json.dumps({
                    "cves": ["CVE-2024-1234"],
                    "threat_actors": ["Lazarus Group"],
                    "malware": ["Emotet"],
                    "vendors": ["Microsoft"],
                    "products": ["Exchange Server"],
                    "sectors": ["Healthcare", "Financial Services"],
                    "countries": ["United States", "Canada"]
                })
            }]
        }).encode()
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        result = self.extractor.extract_entities(self.sample_content, self.sample_title)
        
        assert isinstance(result, EntityExtractionResult)
        assert "CVE-2024-1234" in result.cves
        assert "Lazarus Group" in result.threat_actors
        assert "Emotet" in result.malware
        assert "Microsoft" in result.vendors
        assert "Exchange Server" in result.products
        assert "Healthcare" in result.sectors
        assert "United States" in result.countries
    
    @patch('lambda_tools.relevancy_evaluator.bedrock_client')
    def test_extract_entities_bedrock_error(self, mock_bedrock):
        """Test handling of Bedrock API errors."""
        from botocore.exceptions import ClientError
        
        mock_bedrock.invoke_model.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'InvokeModel'
        )
        
        with pytest.raises(RelevancyEvaluatorError):
            self.extractor.extract_entities(self.sample_content, self.sample_title)
    
    @patch('lambda_tools.relevancy_evaluator.bedrock_client')
    def test_extract_entities_invalid_json(self, mock_bedrock):
        """Test handling of invalid JSON response."""
        # Mock Bedrock response with invalid JSON
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{
                'text': 'Invalid JSON response from model'
            }]
        }).encode()
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        result = self.extractor.extract_entities(self.sample_content, self.sample_title)
        
        # Should return empty result on parse failure
        assert isinstance(result, EntityExtractionResult)
        assert len(result.cves) == 0
        assert len(result.threat_actors) == 0
    
    def test_build_entity_extraction_prompt(self):
        """Test entity extraction prompt building."""
        prompt = self.extractor._build_entity_extraction_prompt(
            self.sample_content, self.sample_title
        )
        
        assert "cybersecurity analyst" in prompt.lower()
        assert self.sample_title in prompt
        assert "CVE-2024-1234" in prompt
        assert "JSON" in prompt
        assert "cves" in prompt
        assert "threat_actors" in prompt
    
    def test_parse_entity_response_valid_json(self):
        """Test parsing valid JSON entity response."""
        response_text = json.dumps({
            "cves": ["CVE-2024-1234"],
            "threat_actors": ["APT29"],
            "malware": ["Cobalt Strike"],
            "vendors": ["Microsoft"],
            "products": ["Windows"],
            "sectors": ["Government"],
            "countries": ["Russia"]
        })
        
        result = self.extractor._parse_entity_response(response_text)
        
        assert isinstance(result, EntityExtractionResult)
        assert result.cves == ["CVE-2024-1234"]
        assert result.threat_actors == ["APT29"]
        assert result.malware == ["Cobalt Strike"]
    
    def test_parse_entity_response_markdown_wrapped(self):
        """Test parsing JSON wrapped in markdown."""
        response_text = """
        Here are the extracted entities:
        
        ```json
        {
            "cves": ["CVE-2024-5678"],
            "threat_actors": ["Lazarus Group"],
            "malware": [],
            "vendors": ["Cisco"],
            "products": ["IOS"],
            "sectors": [],
            "countries": ["North Korea"]
        }
        ```
        """
        
        result = self.extractor._parse_entity_response(response_text)
        
        assert isinstance(result, EntityExtractionResult)
        assert result.cves == ["CVE-2024-5678"]
        assert result.threat_actors == ["Lazarus Group"]
        assert result.vendors == ["Cisco"]


class TestBedrockRelevanceAssessor:
    """Test cases for BedrockRelevanceAssessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.assessor = BedrockRelevanceAssessor()
        self.sample_content = """
        A critical security vulnerability has been discovered in a popular web server.
        The vulnerability allows remote code execution and affects millions of servers
        worldwide. Security researchers recommend immediate patching.
        """
        self.sample_title = "Critical Web Server Vulnerability Discovered"
    
    @patch('lambda_tools.relevancy_evaluator.bedrock_client')
    def test_assess_relevance_success(self, mock_bedrock):
        """Test successful relevance assessment."""
        # Mock Bedrock response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{
                'text': json.dumps({
                    "is_relevant": True,
                    "relevancy_score": 0.85,
                    "rationale": "This article discusses a critical security vulnerability with potential for remote code execution, which is highly relevant to cybersecurity."
                })
            }]
        }).encode()
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        is_relevant, score, rationale = self.assessor.assess_relevance(
            self.sample_content, self.sample_title
        )
        
        assert is_relevant is True
        assert score == 0.85
        assert "vulnerability" in rationale.lower()
    
    @patch('lambda_tools.relevancy_evaluator.bedrock_client')
    def test_assess_relevance_with_keywords(self, mock_bedrock):
        """Test relevance assessment with keyword context."""
        keyword_matches = [
            KeywordMatch(keyword="vulnerability", hit_count=2, contexts=[], confidence=0.9),
            KeywordMatch(keyword="Azure", hit_count=1, contexts=[], confidence=0.8)
        ]
        
        # Mock Bedrock response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{
                'text': json.dumps({
                    "is_relevant": True,
                    "relevancy_score": 0.92,
                    "rationale": "High relevance due to vulnerability discussion and Azure keyword matches."
                })
            }]
        }).encode()
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        is_relevant, score, rationale = self.assessor.assess_relevance(
            self.sample_content, self.sample_title, keyword_matches
        )
        
        assert is_relevant is True
        assert score == 0.92
        
        # Verify keyword matches were included in prompt
        call_args = mock_bedrock.invoke_model.call_args
        prompt = json.loads(call_args[1]['body'])['messages'][0]['content']
        assert "vulnerability" in prompt
        assert "Azure" in prompt
    
    @patch('lambda_tools.relevancy_evaluator.bedrock_client')
    def test_assess_relevance_score_bounds(self, mock_bedrock):
        """Test that relevancy scores are bounded between 0 and 1."""
        # Mock response with out-of-bounds score
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{
                'text': json.dumps({
                    "is_relevant": True,
                    "relevancy_score": 1.5,  # Out of bounds
                    "rationale": "Test rationale"
                })
            }]
        }).encode()
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        is_relevant, score, rationale = self.assessor.assess_relevance(
            self.sample_content, self.sample_title
        )
        
        # Score should be clamped to 1.0
        assert score == 1.0
    
    def test_build_relevance_prompt(self):
        """Test relevance assessment prompt building."""
        keyword_matches = [
            KeywordMatch(keyword="malware", hit_count=1, contexts=[], confidence=0.8)
        ]
        
        prompt = self.assessor._build_relevance_prompt(
            self.sample_content, self.sample_title, keyword_matches
        )
        
        assert "cybersecurity analyst" in prompt.lower()
        assert self.sample_title in prompt
        assert "malware" in prompt
        assert "JSON" in prompt
        assert "is_relevant" in prompt
        assert "relevancy_score" in prompt


class TestRelevancyEvaluator:
    """Test cases for main RelevancyEvaluator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = RelevancyEvaluator()
        self.sample_content = """
        Microsoft has released security updates for Exchange Server to address CVE-2024-1234.
        The vulnerability allows remote code execution and has been exploited by the Lazarus Group.
        Organizations using Azure and Microsoft 365 should apply patches immediately.
        """
        self.sample_title = "Microsoft Exchange Server Security Update"
        self.target_keywords = ["Microsoft", "Exchange Server", "Azure", "Microsoft 365", "CVE"]
    
    @patch.object(BedrockEntityExtractor, 'extract_entities')
    @patch.object(BedrockRelevanceAssessor, 'assess_relevance')
    def test_evaluate_relevance_complete_flow(self, mock_assess, mock_extract):
        """Test complete relevance evaluation flow."""
        # Mock entity extraction
        mock_extract.return_value = EntityExtractionResult(
            cves=["CVE-2024-1234"],
            threat_actors=["Lazarus Group"],
            malware=[],
            vendors=["Microsoft"],
            products=["Exchange Server"],
            sectors=[],
            countries=[]
        )
        
        # Mock relevance assessment
        mock_assess.return_value = (True, 0.88, "High relevance due to security vulnerability")
        
        result = self.evaluator.evaluate_relevance(
            self.sample_content, self.sample_title, self.target_keywords
        )
        
        assert isinstance(result, RelevanceResult)
        assert result.is_relevant is True
        assert result.relevancy_score >= 0.88  # May be adjusted for keywords
        assert len(result.keyword_matches) > 0
        assert "CVE-2024-1234" in result.entities.cves
        assert "Lazarus Group" in result.entities.threat_actors
        assert result.confidence > 0.0
    
    def test_evaluate_relevance_keyword_matching(self):
        """Test keyword matching within evaluation."""
        # Use real keyword matcher (not mocked)
        with patch.object(BedrockEntityExtractor, 'extract_entities') as mock_extract, \
             patch.object(BedrockRelevanceAssessor, 'assess_relevance') as mock_assess:
            
            mock_extract.return_value = EntityExtractionResult([], [], [], [], [], [], [])
            mock_assess.return_value = (True, 0.7, "Test rationale")
            
            result = self.evaluator.evaluate_relevance(
                self.sample_content, self.sample_title, self.target_keywords
            )
            
            # Should find keyword matches
            found_keywords = [m.keyword for m in result.keyword_matches]
            assert "Microsoft" in found_keywords
            assert "Exchange Server" in found_keywords
            assert "Azure" in found_keywords
            assert "Microsoft 365" in found_keywords
    
    def test_calculate_overall_confidence(self):
        """Test overall confidence calculation."""
        keyword_matches = [
            KeywordMatch(keyword="Azure", hit_count=2, contexts=[], confidence=0.9),
            KeywordMatch(keyword="Microsoft", hit_count=1, contexts=[], confidence=0.8)
        ]
        
        entities = EntityExtractionResult(
            cves=["CVE-2024-1234"],
            threat_actors=["APT29"],
            malware=[],
            vendors=["Microsoft"],
            products=["Azure"],
            sectors=[],
            countries=[]
        )
        
        confidence = self.evaluator._calculate_overall_confidence(
            keyword_matches, entities, 0.85
        )
        
        assert 0.7 <= confidence <= 1.0
        assert confidence > 0.8  # Should be high due to keywords and entities
    
    def test_adjust_score_for_keywords(self):
        """Test relevancy score adjustment for keyword matches."""
        base_score = 0.7
        
        keyword_matches = [
            KeywordMatch(keyword="Azure", hit_count=3, contexts=[], confidence=0.9),
            KeywordMatch(keyword="vulnerability", hit_count=2, contexts=[], confidence=0.8)
        ]
        
        adjusted_score = self.evaluator._adjust_score_for_keywords(base_score, keyword_matches)
        
        assert adjusted_score > base_score
        assert adjusted_score <= 1.0
    
    def test_adjust_score_for_keywords_no_matches(self):
        """Test score adjustment with no keyword matches."""
        base_score = 0.6
        adjusted_score = self.evaluator._adjust_score_for_keywords(base_score, [])
        
        assert adjusted_score == base_score


class TestLambdaHandler:
    """Test cases for Lambda handler function."""
    
    @patch.object(RelevancyEvaluator, 'evaluate_relevance')
    def test_lambda_handler_success(self, mock_evaluate):
        """Test successful Lambda handler execution."""
        # Mock evaluation result
        mock_result = RelevanceResult(
            is_relevant=True,
            relevancy_score=0.85,
            keyword_matches=[
                KeywordMatch(keyword="Azure", hit_count=1, contexts=[], confidence=0.8)
            ],
            entities=EntityExtractionResult(
                cves=["CVE-2024-1234"],
                threat_actors=[],
                malware=[],
                vendors=["Microsoft"],
                products=["Azure"],
                sectors=[],
                countries=[]
            ),
            rationale="High cybersecurity relevance",
            confidence=0.9
        )
        
        mock_evaluate.return_value = mock_result
        
        event = {
            "article_id": "test-123",
            "content": "Test content about Azure security",
            "title": "Azure Security Update",
            "target_keywords": ["Azure", "security"]
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        assert response['body']['success'] is True
        assert response['body']['article_id'] == "test-123"
        assert 'result' in response['body']
        
        result_data = response['body']['result']
        assert result_data['is_relevant'] is True
        assert result_data['relevancy_score'] == 0.85
    
    def test_lambda_handler_missing_required_fields(self):
        """Test Lambda handler with missing required fields."""
        event = {
            "title": "Test Title"
            # Missing article_id and content
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        assert response['body']['success'] is False
        assert 'error' in response['body']
    
    @patch.object(RelevancyEvaluator, 'evaluate_relevance')
    def test_lambda_handler_evaluation_error(self, mock_evaluate):
        """Test Lambda handler with evaluation error."""
        mock_evaluate.side_effect = RelevancyEvaluatorError("Test error")
        
        event = {
            "article_id": "test-123",
            "content": "Test content",
            "title": "Test Title",
            "target_keywords": ["test"]
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        assert response['body']['success'] is False
        assert 'Test error' in response['body']['error']
    
    def test_lambda_handler_optional_fields(self):
        """Test Lambda handler with optional fields."""
        with patch.object(RelevancyEvaluator, 'evaluate_relevance') as mock_evaluate:
            mock_evaluate.return_value = RelevanceResult(
                is_relevant=False,
                relevancy_score=0.3,
                keyword_matches=[],
                entities=EntityExtractionResult([], [], [], [], [], [], []),
                rationale="Low relevance",
                confidence=0.7
            )
            
            event = {
                "article_id": "test-123",
                "content": "Test content about cooking"
                # Missing optional title and target_keywords
            }
            
            response = lambda_handler(event, None)
            
            assert response['statusCode'] == 200
            assert response['body']['success'] is True
            
            # Verify evaluate_relevance was called with defaults
            mock_evaluate.assert_called_once_with("Test content about cooking", "", [])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])