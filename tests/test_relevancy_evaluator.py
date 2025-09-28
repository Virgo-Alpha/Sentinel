"""
Unit tests for RelevancyEvaluator Lambda tool.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from src.lambda_tools.relevancy_evaluator import (
    RelevancyEvaluator,
    KeywordMatcher,
    BedrockEntityExtractor,
    BedrockRelevanceAssessor,
    KeywordMatch,
    EntityExtractionResult,
    RelevanceResult,
    RelevancyEvaluatorError,
    lambda_handler
)


class TestKeywordMatcher:
    """Test cases for KeywordMatcher class."""
    
    def setup_method(self):
        self.matcher = KeywordMatcher()
    
    def test_find_keyword_matches_basic(self):
        """Test basic keyword matching."""
        content = "Microsoft Exchange Server has a critical vulnerability CVE-2024-1234."
        keywords = ["Microsoft", "Exchange Server", "vulnerability"]
        
        matches = self.matcher.find_keyword_matches(content, keywords)
        
        assert len(matches) == 3
        
        # Check Microsoft match
        microsoft_match = next(m for m in matches if m.keyword == "Microsoft")
        assert microsoft_match.hit_count == 1
        assert microsoft_match.confidence > 0.8
        assert len(microsoft_match.contexts) == 1
        
        # Check Exchange Server match
        exchange_match = next(m for m in matches if m.keyword == "Exchange Server")
        assert exchange_match.hit_count == 1
        assert "Microsoft Exchange Server" in exchange_match.contexts[0]
    
    def test_find_keyword_matches_case_insensitive(self):
        """Test case-insensitive keyword matching."""
        content = "MICROSOFT exchange server vulnerability"
        keywords = ["Microsoft", "Exchange Server"]
        
        matches = self.matcher.find_keyword_matches(content, keywords)
        
        assert len(matches) == 2
        microsoft_match = next(m for m in matches if m.keyword == "Microsoft")
        assert microsoft_match.hit_count == 1
    
    def test_find_keyword_matches_multiple_hits(self):
        """Test keyword matching with multiple occurrences."""
        content = "Microsoft Azure and Microsoft 365 are Microsoft products."
        keywords = ["Microsoft"]
        
        matches = self.matcher.find_keyword_matches(content, keywords)
        
        assert len(matches) == 1
        match = matches[0]
        assert match.hit_count == 3
        assert match.confidence > 0.8
        assert len(match.contexts) >= 1
    
    def test_find_keyword_matches_no_matches(self):
        """Test keyword matching with no matches."""
        content = "This is about something completely different."
        keywords = ["Microsoft", "Exchange Server"]
        
        matches = self.matcher.find_keyword_matches(content, keywords)
        
        assert len(matches) == 0
    
    def test_find_keyword_matches_context_extraction(self):
        """Test context extraction around keyword matches."""
        content = "The Microsoft Exchange Server vulnerability affects many organizations worldwide."
        keywords = ["Exchange Server"]
        
        matches = self.matcher.find_keyword_matches(content, keywords)
        
        assert len(matches) == 1
        match = matches[0]
        assert "Microsoft Exchange Server vulnerability" in match.contexts[0]
    
    def test_calculate_match_confidence(self):
        """Test confidence calculation for keyword matches."""
        content = "Microsoft Azure and Microsoft 365"
        
        # Test exact case match
        confidence = self.matcher._calculate_match_confidence("Microsoft", content, 2)
        assert confidence > 0.8
        
        # Test case insensitive match
        confidence = self.matcher._calculate_match_confidence("microsoft", content, 2)
        assert confidence > 0.7


class TestBedrockEntityExtractor:
    """Test cases for BedrockEntityExtractor class."""
    
    def setup_method(self):
        self.extractor = BedrockEntityExtractor()
    
    @patch('src.lambda_tools.relevancy_evaluator.bedrock_client')
    def test_extract_entities_success(self, mock_bedrock):
        """Test successful entity extraction."""
        # Mock Bedrock response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{
                'text': json.dumps({
                    'cves': ['CVE-2024-1234'],
                    'threat_actors': ['APT29'],
                    'malware': ['Emotet'],
                    'vendors': ['Microsoft'],
                    'products': ['Exchange Server'],
                    'sectors': ['Healthcare'],
                    'countries': ['United States']
                })
            }]
        }).encode()
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        content = "CVE-2024-1234 affects Microsoft Exchange Server used by APT29 with Emotet malware."
        result = self.extractor.extract_entities(content, "Test Article")
        
        assert isinstance(result, EntityExtractionResult)
        assert result.cves == ['CVE-2024-1234']
        assert result.threat_actors == ['APT29']
        assert result.malware == ['Emotet']
        assert result.vendors == ['Microsoft']
        assert result.products == ['Exchange Server']
        assert result.sectors == ['Healthcare']
        assert result.countries == ['United States']
    
    @patch('src.lambda_tools.relevancy_evaluator.bedrock_client')
    def test_extract_entities_bedrock_error(self, mock_bedrock):
        """Test entity extraction with Bedrock API error."""
        mock_bedrock.invoke_model.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'InvokeModel'
        )
        
        with pytest.raises(RelevancyEvaluatorError):
            self.extractor.extract_entities("test content", "test title")
    
    @patch('src.lambda_tools.relevancy_evaluator.bedrock_client')
    def test_extract_entities_invalid_json(self, mock_bedrock):
        """Test entity extraction with invalid JSON response."""
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'invalid json response'}]
        }).encode()
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        result = self.extractor.extract_entities("test content", "test title")
        
        # Should return empty result on parse failure
        assert isinstance(result, EntityExtractionResult)
        assert result.cves == []
        assert result.threat_actors == []
    
    def test_build_entity_extraction_prompt(self):
        """Test entity extraction prompt building."""
        content = "Test content with CVE-2024-1234"
        title = "Test Article"
        
        prompt = self.extractor._build_entity_extraction_prompt(content, title)
        
        assert "Test Article" in prompt
        assert "Test content with CVE-2024-1234" in prompt
        assert "CVE-YYYY-NNNN" in prompt
        assert "JSON" in prompt
    
    def test_parse_entity_response_valid_json(self):
        """Test parsing valid JSON entity response."""
        response_text = json.dumps({
            'cves': ['CVE-2024-1234'],
            'threat_actors': ['APT29'],
            'malware': [],
            'vendors': ['Microsoft'],
            'products': ['Exchange'],
            'sectors': [],
            'countries': ['US']
        })
        
        result = self.extractor._parse_entity_response(response_text)
        
        assert result.cves == ['CVE-2024-1234']
        assert result.threat_actors == ['APT29']
        assert result.vendors == ['Microsoft']
    
    def test_parse_entity_response_with_markdown(self):
        """Test parsing entity response with markdown formatting."""
        response_text = '''Here is the analysis:

```json
{
    "cves": ["CVE-2024-1234"],
    "threat_actors": ["APT29"],
    "malware": [],
    "vendors": ["Microsoft"],
    "products": ["Exchange"],
    "sectors": [],
    "countries": []
}
```

This completes the analysis.'''
        
        result = self.extractor._parse_entity_response(response_text)
        
        assert result.cves == ['CVE-2024-1234']
        assert result.threat_actors == ['APT29']


class TestBedrockRelevanceAssessor:
    """Test cases for BedrockRelevanceAssessor class."""
    
    def setup_method(self):
        self.assessor = BedrockRelevanceAssessor()
    
    @patch('src.lambda_tools.relevancy_evaluator.bedrock_client')
    def test_assess_relevance_success(self, mock_bedrock):
        """Test successful relevance assessment."""
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{
                'text': json.dumps({
                    'is_relevant': True,
                    'relevancy_score': 0.85,
                    'rationale': 'Article discusses cybersecurity vulnerability'
                })
            }]
        }).encode()
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        content = "Critical vulnerability found in Exchange Server"
        is_relevant, score, rationale = self.assessor.assess_relevance(content, "Test Title")
        
        assert is_relevant is True
        assert score == 0.85
        assert "vulnerability" in rationale
    
    @patch('src.lambda_tools.relevancy_evaluator.bedrock_client')
    def test_assess_relevance_bedrock_error(self, mock_bedrock):
        """Test relevance assessment with Bedrock error."""
        mock_bedrock.invoke_model.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid input'}},
            'InvokeModel'
        )
        
        with pytest.raises(RelevancyEvaluatorError):
            self.assessor.assess_relevance("test content")
    
    def test_build_relevance_prompt(self):
        """Test relevance assessment prompt building."""
        content = "Test cybersecurity content"
        title = "Security Alert"
        keyword_matches = [KeywordMatch(keyword="Microsoft", hit_count=1, contexts=["test"], confidence=0.9)]
        
        prompt = self.assessor._build_relevance_prompt(content, title, keyword_matches)
        
        assert "Security Alert" in prompt
        assert "Test cybersecurity content" in prompt
        assert "Microsoft" in prompt
        assert "JSON" in prompt
    
    def test_parse_relevance_response_valid(self):
        """Test parsing valid relevance response."""
        response_text = json.dumps({
            'is_relevant': True,
            'relevancy_score': 0.75,
            'rationale': 'Contains cybersecurity content'
        })
        
        is_relevant, score, rationale = self.assessor._parse_relevance_response(response_text)
        
        assert is_relevant is True
        assert score == 0.75
        assert rationale == 'Contains cybersecurity content'
    
    def test_parse_relevance_response_invalid(self):
        """Test parsing invalid relevance response."""
        response_text = "invalid json response"
        
        is_relevant, score, rationale = self.assessor._parse_relevance_response(response_text)
        
        # Should return conservative defaults
        assert is_relevant is False
        assert score == 0.0
        assert "Failed to parse" in rationale
    
    def test_parse_relevance_response_score_bounds(self):
        """Test relevance score is bounded between 0 and 1."""
        response_text = json.dumps({
            'is_relevant': True,
            'relevancy_score': 1.5,  # Invalid score > 1
            'rationale': 'Test'
        })
        
        is_relevant, score, rationale = self.assessor._parse_relevance_response(response_text)
        
        assert score == 1.0  # Should be clamped to 1.0


class TestRelevancyEvaluator:
    """Test cases for main RelevancyEvaluator class."""
    
    def setup_method(self):
        self.evaluator = RelevancyEvaluator()
    
    @patch.object(BedrockRelevanceAssessor, 'assess_relevance')
    @patch.object(BedrockEntityExtractor, 'extract_entities')
    @patch.object(KeywordMatcher, 'find_keyword_matches')
    def test_evaluate_relevance_success(self, mock_keyword_matcher, mock_entity_extractor, mock_relevance_assessor):
        """Test complete relevance evaluation."""
        # Mock keyword matches
        mock_keyword_matches = [
            KeywordMatch(keyword="Microsoft", hit_count=2, contexts=["test context"], confidence=0.9)
        ]
        mock_keyword_matcher.return_value = mock_keyword_matches
        
        # Mock entity extraction
        mock_entities = EntityExtractionResult(
            cves=['CVE-2024-1234'],
            threat_actors=['APT29'],
            malware=[],
            vendors=['Microsoft'],
            products=['Exchange'],
            sectors=[],
            countries=[]
        )
        mock_entity_extractor.return_value = mock_entities
        
        # Mock relevance assessment
        mock_relevance_assessor.return_value = (True, 0.85, "Highly relevant cybersecurity content")
        
        content = "Microsoft Exchange vulnerability CVE-2024-1234 exploited by APT29"
        keywords = ["Microsoft", "Exchange"]
        
        result = self.evaluator.evaluate_relevance(content, "Test Title", keywords)
        
        assert isinstance(result, RelevanceResult)
        assert result.is_relevant is True
        assert result.relevancy_score >= 0.85  # May be adjusted for keywords
        assert len(result.keyword_matches) == 1
        assert result.entities.cves == ['CVE-2024-1234']
        assert result.confidence > 0.7
        assert "relevant" in result.rationale
    
    def test_calculate_overall_confidence(self):
        """Test overall confidence calculation."""
        keyword_matches = [
            KeywordMatch(keyword="Microsoft", hit_count=1, contexts=["test"], confidence=0.9)
        ]
        entities = EntityExtractionResult(
            cves=['CVE-2024-1234'],
            threat_actors=['APT29'],
            malware=[],
            vendors=['Microsoft'],
            products=[],
            sectors=[],
            countries=[]
        )
        relevancy_score = 0.85
        
        confidence = self.evaluator._calculate_overall_confidence(keyword_matches, entities, relevancy_score)
        
        assert 0.7 <= confidence <= 1.0
        assert confidence > 0.8  # Should be high due to keywords, entities, and score
    
    def test_adjust_score_for_keywords(self):
        """Test relevancy score adjustment for keyword matches."""
        base_score = 0.7
        keyword_matches = [
            KeywordMatch(keyword="Microsoft", hit_count=2, contexts=["test"], confidence=0.9),
            KeywordMatch(keyword="Exchange", hit_count=1, contexts=["test"], confidence=0.8)
        ]
        
        adjusted_score = self.evaluator._adjust_score_for_keywords(base_score, keyword_matches)
        
        assert adjusted_score > base_score
        assert adjusted_score <= 1.0
    
    def test_adjust_score_for_keywords_no_matches(self):
        """Test score adjustment with no keyword matches."""
        base_score = 0.7
        keyword_matches = []
        
        adjusted_score = self.evaluator._adjust_score_for_keywords(base_score, keyword_matches)
        
        assert adjusted_score == base_score
    
    @patch.object(BedrockRelevanceAssessor, 'assess_relevance')
    def test_evaluate_relevance_error_handling(self, mock_relevance_assessor):
        """Test error handling in relevance evaluation."""
        mock_relevance_assessor.side_effect = Exception("Test error")
        
        with pytest.raises(RelevancyEvaluatorError):
            self.evaluator.evaluate_relevance("test content", "test title", ["test"])


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
                KeywordMatch(keyword="Microsoft", hit_count=1, contexts=["test"], confidence=0.9)
            ],
            entities=EntityExtractionResult([], [], [], [], [], [], []),
            rationale="Test rationale",
            confidence=0.8
        )
        mock_evaluate.return_value = mock_result
        
        event = {
            'article_id': 'test-123',
            'content': 'Test cybersecurity content',
            'title': 'Test Article',
            'target_keywords': ['Microsoft', 'Exchange']
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        assert response['body']['success'] is True
        assert response['body']['article_id'] == 'test-123'
        assert 'result' in response['body']
        
        result = response['body']['result']
        assert result['is_relevant'] is True
        assert result['relevancy_score'] == 0.85
    
    def test_lambda_handler_missing_parameters(self):
        """Test Lambda handler with missing required parameters."""
        event = {
            'content': 'Test content'
            # Missing article_id
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        assert response['body']['success'] is False
        assert 'article_id and content are required' in response['body']['error']
    
    @patch.object(RelevancyEvaluator, 'evaluate_relevance')
    def test_lambda_handler_evaluation_error(self, mock_evaluate):
        """Test Lambda handler with evaluation error."""
        mock_evaluate.side_effect = RelevancyEvaluatorError("Test error")
        
        event = {
            'article_id': 'test-123',
            'content': 'Test content'
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        assert response['body']['success'] is False
        assert 'Test error' in response['body']['error']
    
    def test_lambda_handler_optional_parameters(self):
        """Test Lambda handler with optional parameters."""
        with patch.object(RelevancyEvaluator, 'evaluate_relevance') as mock_evaluate:
            mock_result = RelevanceResult(
                is_relevant=False,
                relevancy_score=0.3,
                keyword_matches=[],
                entities=EntityExtractionResult([], [], [], [], [], [], []),
                rationale="Not relevant",
                confidence=0.7
            )
            mock_evaluate.return_value = mock_result
            
            event = {
                'article_id': 'test-123',
                'content': 'Test content'
                # No title or target_keywords
            }
            
            response = lambda_handler(event, None)
            
            assert response['statusCode'] == 200
            mock_evaluate.assert_called_once_with('Test content', '', [])


# Integration test with actual keyword configuration
class TestRelevancyEvaluatorIntegration:
    """Integration tests using actual keyword configuration."""
    
    def setup_method(self):
        self.evaluator = RelevancyEvaluator()
    
    @patch('src.lambda_tools.relevancy_evaluator.bedrock_client')
    def test_integration_with_real_keywords(self, mock_bedrock):
        """Test integration with real keyword configuration."""
        # Mock Bedrock responses
        entity_response = {
            'body': Mock()
        }
        entity_response['body'].read.return_value = json.dumps({
            'content': [{
                'text': json.dumps({
                    'cves': ['CVE-2024-1234'],
                    'threat_actors': [],
                    'malware': [],
                    'vendors': ['Microsoft'],
                    'products': ['Exchange Server'],
                    'sectors': ['Healthcare'],
                    'countries': []
                })
            }]
        }).encode()
        
        relevance_response = {
            'body': Mock()
        }
        relevance_response['body'].read.return_value = json.dumps({
            'content': [{
                'text': json.dumps({
                    'is_relevant': True,
                    'relevancy_score': 0.9,
                    'rationale': 'Article discusses Microsoft Exchange vulnerability'
                })
            }]
        }).encode()
        
        # Mock Bedrock to return different responses for different calls
        mock_bedrock.invoke_model.side_effect = [entity_response, relevance_response]
        
        content = """
        Microsoft has released security updates for Exchange Server to address a critical 
        vulnerability (CVE-2024-1234) that could allow remote code execution. The vulnerability 
        affects Exchange Server 2019 and 2016 installations. Healthcare organizations using 
        Microsoft 365 should apply these updates immediately.
        """
        
        keywords = ["Microsoft", "Exchange Server", "Microsoft 365", "vulnerability"]
        
        result = self.evaluator.evaluate_relevance(content, "Critical Exchange Vulnerability", keywords)
        
        assert result.is_relevant is True
        assert result.relevancy_score > 0.8
        assert len(result.keyword_matches) >= 2  # Should find Microsoft and Exchange Server
        assert result.entities.cves == ['CVE-2024-1234']
        assert result.entities.vendors == ['Microsoft']
        assert result.confidence > 0.8


if __name__ == '__main__':
    pytest.main([__file__])