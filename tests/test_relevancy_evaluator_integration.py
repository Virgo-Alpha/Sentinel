"""
Integration tests for RelevancyEvaluator with mocked Bedrock calls.

This demonstrates the complete functionality without requiring actual AWS credentials.
"""

import json
import sys
import os
from unittest.mock import patch, Mock

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_tools.relevancy_evaluator import lambda_handler


def test_complete_integration_flow():
    """Test complete integration flow with mocked Bedrock responses."""
    
    # Sample cybersecurity article
    test_event = {
        "article_id": "integration-test-123",
        "content": """
        Microsoft has released critical security updates for Exchange Server to address 
        CVE-2024-1234, a remote code execution vulnerability. The vulnerability affects 
        Exchange Server 2019 and 2016 installations and has been actively exploited 
        by the Lazarus Group APT in targeted attacks against financial institutions.
        
        Organizations using Azure Active Directory and Microsoft 365 should prioritize 
        applying these patches immediately. The vulnerability allows attackers to execute 
        arbitrary code on vulnerable servers without authentication.
        
        Fortinet researchers discovered the vulnerability during routine security testing. 
        The attack vector involves specially crafted email messages that trigger the 
        vulnerability when processed by the Exchange Server.
        
        This incident highlights the ongoing threat from state-sponsored actors targeting 
        critical infrastructure. The healthcare and financial services sectors have been 
        particularly affected by these attacks.
        """,
        "title": "Critical Exchange Server Vulnerability CVE-2024-1234 Exploited by Lazarus Group",
        "target_keywords": [
            "Microsoft", "Exchange Server", "Azure", "Microsoft 365", "CVE", 
            "Fortinet", "vulnerability", "APT", "Lazarus Group", "healthcare", 
            "financial services"
        ]
    }
    
    # Mock Bedrock responses
    entity_response = {
        "cves": ["CVE-2024-1234"],
        "threat_actors": ["Lazarus Group"],
        "malware": [],
        "vendors": ["Microsoft", "Fortinet"],
        "products": ["Exchange Server", "Azure Active Directory", "Microsoft 365"],
        "sectors": ["Healthcare", "Financial Services"],
        "countries": []
    }
    
    relevance_response = {
        "is_relevant": True,
        "relevancy_score": 0.92,
        "rationale": "This article is highly relevant to cybersecurity as it discusses a critical vulnerability (CVE-2024-1234) in Microsoft Exchange Server that is being actively exploited by the Lazarus Group APT. The article covers key cybersecurity topics including vulnerability disclosure, threat actor activity, and impact on critical sectors."
    }
    
    # Mock Bedrock client
    with patch('lambda_tools.relevancy_evaluator.bedrock_client') as mock_bedrock:
        # Set up mock responses
        mock_responses = [
            # Entity extraction response
            {
                'body': Mock()
            },
            # Relevance assessment response  
            {
                'body': Mock()
            }
        ]
        
        mock_responses[0]['body'].read.return_value = json.dumps({
            'content': [{'text': json.dumps(entity_response)}]
        }).encode()
        
        mock_responses[1]['body'].read.return_value = json.dumps({
            'content': [{'text': json.dumps(relevance_response)}]
        }).encode()
        
        mock_bedrock.invoke_model.side_effect = mock_responses
        
        # Execute the Lambda handler
        result = lambda_handler(test_event, None)
        
        # Verify successful execution
        assert result['statusCode'] == 200
        assert result['body']['success'] is True
        assert result['body']['article_id'] == "integration-test-123"
        
        # Verify result structure
        evaluation_result = result['body']['result']
        
        # Check relevance assessment
        assert evaluation_result['is_relevant'] is True
        assert evaluation_result['relevancy_score'] >= 0.92  # May be adjusted for keywords
        assert "vulnerability" in evaluation_result['rationale'].lower()
        
        # Check keyword matches
        keyword_matches = evaluation_result['keyword_matches']
        found_keywords = [m['keyword'] for m in keyword_matches]
        
        # Should find multiple target keywords
        assert "Microsoft" in found_keywords
        assert "Exchange Server" in found_keywords
        assert "Azure" in found_keywords
        assert "Microsoft 365" in found_keywords
        assert "CVE" in found_keywords
        assert "Fortinet" in found_keywords
        assert "vulnerability" in found_keywords
        assert "APT" in found_keywords
        
        # Check entity extraction
        entities = evaluation_result['entities']
        assert "CVE-2024-1234" in entities['cves']
        assert "Lazarus Group" in entities['threat_actors']
        assert "Microsoft" in entities['vendors']
        assert "Fortinet" in entities['vendors']
        assert "Exchange Server" in entities['products']
        assert "Healthcare" in entities['sectors']
        assert "Financial Services" in entities['sectors']
        
        # Check confidence score
        assert 0.0 <= evaluation_result['confidence'] <= 1.0
        assert evaluation_result['confidence'] > 0.8  # Should be high confidence
        
        # Verify Bedrock was called correctly
        assert mock_bedrock.invoke_model.call_count == 2
        
        # Check entity extraction call
        entity_call = mock_bedrock.invoke_model.call_args_list[0]
        entity_body = json.loads(entity_call[1]['body'])
        assert "anthropic_version" in entity_body
        assert "CVE-2024-1234" in entity_body['messages'][0]['content']
        
        # Check relevance assessment call
        relevance_call = mock_bedrock.invoke_model.call_args_list[1]
        relevance_body = json.loads(relevance_call[1]['body'])
        assert "cybersecurity analyst" in relevance_body['messages'][0]['content'].lower()
        
        print("✅ Integration test passed!")
        print(f"📊 Found {len(keyword_matches)} keyword matches")
        print(f"🎯 Relevancy score: {evaluation_result['relevancy_score']:.2f}")
        print(f"🔒 Confidence: {evaluation_result['confidence']:.2f}")
        print(f"🏷️ Entities: {len(entities['cves'])} CVEs, {len(entities['threat_actors'])} actors, {len(entities['vendors'])} vendors")
        
        return result


def test_low_relevance_article():
    """Test with a non-cybersecurity article."""
    
    test_event = {
        "article_id": "low-relevance-test",
        "content": """
        The local farmers market will be hosting its annual harvest festival next weekend.
        Visitors can enjoy fresh produce, live music, and family-friendly activities.
        The event will feature local vendors selling organic vegetables, homemade crafts,
        and artisanal foods. Parking will be available in the nearby school lot.
        """,
        "title": "Annual Harvest Festival at Farmers Market",
        "target_keywords": ["Microsoft", "Azure", "cybersecurity", "vulnerability"]
    }
    
    # Mock responses for non-relevant content
    entity_response = {
        "cves": [],
        "threat_actors": [],
        "malware": [],
        "vendors": [],
        "products": [],
        "sectors": [],
        "countries": []
    }
    
    relevance_response = {
        "is_relevant": False,
        "relevancy_score": 0.15,
        "rationale": "This article is about a farmers market harvest festival and is not relevant to cybersecurity topics. It does not discuss security vulnerabilities, threats, or technology."
    }
    
    with patch('lambda_tools.relevancy_evaluator.bedrock_client') as mock_bedrock:
        # Set up mock responses
        mock_responses = [
            {'body': Mock()},
            {'body': Mock()}
        ]
        
        mock_responses[0]['body'].read.return_value = json.dumps({
            'content': [{'text': json.dumps(entity_response)}]
        }).encode()
        
        mock_responses[1]['body'].read.return_value = json.dumps({
            'content': [{'text': json.dumps(relevance_response)}]
        }).encode()
        
        mock_bedrock.invoke_model.side_effect = mock_responses
        
        result = lambda_handler(test_event, None)
        
        # Verify low relevance result
        assert result['statusCode'] == 200
        evaluation_result = result['body']['result']
        
        assert evaluation_result['is_relevant'] is False
        assert evaluation_result['relevancy_score'] < 0.5
        assert len(evaluation_result['keyword_matches']) == 0  # No target keywords found
        assert len(evaluation_result['entities']['cves']) == 0
        
        print("✅ Low relevance test passed!")
        print(f"📊 Relevancy score: {evaluation_result['relevancy_score']:.2f}")
        
        return result


if __name__ == "__main__":
    print("🧪 Running RelevancyEvaluator integration tests...\n")
    
    print("Test 1: High relevance cybersecurity article")
    test_complete_integration_flow()
    
    print("\nTest 2: Low relevance non-cybersecurity article")
    test_low_relevance_article()
    
    print("\n🎉 All integration tests completed successfully!")