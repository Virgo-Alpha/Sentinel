"""
Unit tests for QueryKB Lambda tool.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Import the module under test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_tools.query_kb import (
    QueryKBTool, NaturalLanguageProcessor, DatabaseQueryEngine, 
    ReportGenerator, QueryResult, QueryResponse, lambda_handler
)


class TestNaturalLanguageProcessor:
    """Test cases for NaturalLanguageProcessor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = NaturalLanguageProcessor("test-model")
    
    @patch('lambda_tools.query_kb.bedrock_runtime')
    def test_parse_query_with_llm_success(self, mock_bedrock):
        """Test successful query parsing with LLM."""
        # Mock Bedrock response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{
                'text': '''
                {
                  "keywords": ["Microsoft", "Azure", "vulnerability"],
                  "date_range": {"start": "2024-01-01T00:00:00Z", "end": "2024-01-31T23:59:59Z"},
                  "categories": ["Vulnerabilities"],
                  "sources": [],
                  "entities": {"cves": [], "vendors": ["Microsoft"]},
                  "intent": "search"
                }
                '''
            }]
        }).encode()
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        # Test query parsing
        query = "Show me Microsoft Azure vulnerabilities from January 2024"
        result = self.processor.parse_query(query)
        
        # Assertions
        assert result["keywords"] == ["Microsoft", "Azure", "vulnerability"]
        assert result["categories"] == ["Vulnerabilities"]
        assert result["entities"]["vendors"] == ["Microsoft"]
        assert result["intent"] == "search"
    
    def test_basic_query_parsing_fallback(self):
        """Test basic query parsing as fallback."""
        query = "Show me CVE-2024-1234 Microsoft Azure vulnerabilities from last week"
        result = self.processor._basic_query_parsing(query)
        
        # Should extract CVE
        assert "CVE-2024-1234" in result["entities"]["cves"]
        
        # Should extract relevant keywords
        keywords = result["keywords"]
        assert any("microsoft" in kw.lower() for kw in keywords)
        assert any("azure" in kw.lower() for kw in keywords)
        
        # Should detect time reference
        assert result["date_range"] is not None
        assert "start" in result["date_range"]
        assert "end" in result["date_range"]
    
    def test_date_extraction(self):
        """Test date extraction from queries."""
        # Test "today"
        result = self.processor._basic_query_parsing("vulnerabilities from today")
        assert result["date_range"] is not None
        
        # Test "week"
        result = self.processor._basic_query_parsing("show me alerts from this week")
        assert result["date_range"] is not None
        
        # Test "month"
        result = self.processor._basic_query_parsing("monthly security report")
        assert result["date_range"] is not None


class TestDatabaseQueryEngine:
    """Test cases for DatabaseQueryEngine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('lambda_tools.query_kb.dynamodb'):
            self.engine = DatabaseQueryEngine("test-table")
    
    @patch('lambda_tools.query_kb.dynamodb')
    def test_search_dynamodb_with_filters(self, mock_dynamodb):
        """Test DynamoDB search with various filters."""
        # Mock DynamoDB table
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        # Mock scan response
        mock_table.scan.return_value = {
            'Items': [
                {
                    'article_id': 'test-1',
                    'title': 'Microsoft Azure Security Alert',
                    'url': 'https://example.com/alert1',
                    'published_at': '2024-01-15T10:00:00Z',
                    'state': 'PUBLISHED',
                    'source': 'Microsoft',
                    'summary_short': 'Critical vulnerability in Azure',
                    'relevancy_score': Decimal('0.9'),
                    'keyword_matches': [
                        {'keyword': 'Azure', 'hit_count': 3}
                    ],
                    'tags': ['Vulnerabilities']
                }
            ]
        }
        
        engine = DatabaseQueryEngine("test-table")
        
        # Test search with filters
        filters = {
            "keywords": ["Azure", "Microsoft"],
            "date_range": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-31T23:59:59Z"
            },
            "categories": ["Vulnerabilities"]
        }
        
        results = engine.search_articles(filters, limit=10)
        
        # Assertions
        assert len(results) == 1
        assert results[0].article_id == 'test-1'
        assert results[0].title == 'Microsoft Azure Security Alert'
        assert 'Azure' in results[0].keyword_matches
        assert results[0].hit_count > 0
    
    def test_keyword_matching(self):
        """Test keyword matching logic."""
        engine = DatabaseQueryEngine("test-table")
        
        article = {
            'title': 'Microsoft Azure Security Vulnerability',
            'summary_short': 'Critical Azure issue affecting Microsoft services',
            'tags': ['Security', 'Cloud'],
            'keyword_matches': [
                {'keyword': 'Azure', 'hit_count': 2}
            ]
        }
        
        keywords = ['Microsoft', 'Azure', 'vulnerability']
        matches, hit_count = engine._calculate_keyword_matches(article, keywords)
        
        # Should find matches for Microsoft, Azure, and vulnerability
        assert 'Microsoft' in matches
        assert 'Azure' in matches
        assert 'vulnerability' in matches
        assert hit_count > 0
    
    def test_convert_dynamodb_types(self):
        """Test DynamoDB type conversion."""
        engine = DatabaseQueryEngine("test-table")
        
        item = {
            'relevancy_score': Decimal('0.85'),
            'hit_count': Decimal('5'),
            'nested': {
                'score': Decimal('0.9')
            },
            'list_field': [Decimal('1.0'), 'string', {'inner': Decimal('2.0')}]
        }
        
        converted = engine._convert_from_dynamodb_types(item)
        
        assert isinstance(converted['relevancy_score'], float)
        assert converted['relevancy_score'] == 0.85
        assert isinstance(converted['nested']['score'], float)
        assert isinstance(converted['list_field'][0], float)


class TestReportGenerator:
    """Test cases for ReportGenerator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = ReportGenerator("test-bucket")
        
        # Sample query results
        self.sample_results = [
            QueryResult(
                article_id="test-1",
                title="Microsoft Azure Vulnerability",
                url="https://example.com/1",
                published_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                keyword_matches=["Microsoft", "Azure"],
                hit_count=5,
                description="Critical vulnerability in Azure services",
                relevancy_score=0.9,
                source="Microsoft Security",
                tags=["Vulnerabilities", "Cloud"]
            ),
            QueryResult(
                article_id="test-2", 
                title="AWS Security Alert",
                url="https://example.com/2",
                published_at=datetime(2024, 1, 14, 15, 30, 0, tzinfo=timezone.utc),
                keyword_matches=["AWS"],
                hit_count=2,
                description="Security issue in AWS services",
                relevancy_score=0.8,
                source="AWS Security",
                tags=["Alerts"]
            )
        ]
    
    @patch('lambda_tools.query_kb.boto3.client')
    @patch('openpyxl.Workbook')
    def test_generate_xlsx_report(self, mock_workbook, mock_boto3):
        """Test XLSX report generation."""
        # Mock openpyxl
        mock_wb = Mock()
        mock_ws = Mock()
        mock_wb.active = mock_ws
        mock_workbook.return_value = mock_wb
        
        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/report.xlsx"
        
        # Generate report
        result_url = self.generator.generate_xlsx_report(self.sample_results)
        
        # Assertions
        assert result_url == "https://s3.example.com/report.xlsx"
        mock_s3.put_object.assert_called_once()
        mock_s3.generate_presigned_url.assert_called_once()
        
        # Verify worksheet was populated
        assert mock_ws.cell.call_count > 0  # Headers and data rows
    
    @patch('lambda_tools.query_kb.boto3.client')
    def test_generate_xlsx_report_no_openpyxl(self, mock_boto3):
        """Test XLSX report generation when openpyxl is not available."""
        with patch('builtins.__import__', side_effect=ImportError):
            with pytest.raises(Exception) as exc_info:
                self.generator.generate_xlsx_report(self.sample_results)
            
            assert "openpyxl" in str(exc_info.value).lower()


class TestQueryKBTool:
    """Test cases for QueryKBTool integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('lambda_tools.query_kb.dynamodb'), \
             patch('lambda_tools.query_kb.boto3.client'):
            self.tool = QueryKBTool(
                "test-table", 
                "https://test-opensearch.com",
                "test-bucket",
                "test-model"
            )
    
    @patch.object(NaturalLanguageProcessor, 'parse_query')
    @patch.object(DatabaseQueryEngine, 'search_articles')
    def test_process_query_success(self, mock_search, mock_parse):
        """Test successful query processing."""
        # Mock query parsing
        mock_parse.return_value = {
            "keywords": ["Microsoft", "Azure"],
            "date_range": None,
            "categories": [],
            "sources": [],
            "entities": {"cves": []},
            "intent": "search"
        }
        
        # Mock search results
        mock_results = [
            QueryResult(
                article_id="test-1",
                title="Test Article",
                url="https://example.com/1",
                published_at=datetime.now(timezone.utc),
                keyword_matches=["Microsoft"],
                hit_count=1,
                description="Test description"
            )
        ]
        mock_search.return_value = mock_results
        
        # Process query
        response = self.tool.process_query("Show me Microsoft Azure issues")
        
        # Assertions
        assert response.success is True
        assert response.total_results == 1
        assert len(response.results) == 1
        assert response.results[0].title == "Test Article"
        assert response.query_time_ms > 0
    
    @patch.object(DatabaseQueryEngine, 'search_articles')
    def test_process_query_with_explicit_filters(self, mock_search):
        """Test query processing with explicit filters."""
        mock_search.return_value = []
        
        filters = {
            "keywords": ["test"],
            "date_range": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-31T23:59:59Z"
            }
        }
        
        response = self.tool.process_query("", filters=filters)
        
        assert response.success is True
        assert response.filters_applied == filters
        mock_search.assert_called_once_with(filters, 100)
    
    @patch.object(ReportGenerator, 'generate_xlsx_report')
    @patch.object(DatabaseQueryEngine, 'search_articles')
    def test_process_query_with_export(self, mock_search, mock_export):
        """Test query processing with XLSX export."""
        mock_results = [Mock()]
        mock_search.return_value = mock_results
        mock_export.return_value = "https://s3.example.com/report.xlsx"
        
        response = self.tool.process_query(
            "test query", 
            export_format="xlsx"
        )
        
        assert response.success is True
        assert response.export_url == "https://s3.example.com/report.xlsx"
        mock_export.assert_called_once_with(mock_results)


class TestLambdaHandler:
    """Test cases for Lambda handler."""
    
    @patch('lambda_tools.query_kb.QueryKBTool')
    def test_lambda_handler_success(self, mock_tool_class):
        """Test successful Lambda handler execution."""
        # Mock QueryKBTool
        mock_tool = Mock()
        mock_tool_class.return_value = mock_tool
        
        mock_response = QueryResponse(
            success=True,
            total_results=1,
            results=[
                QueryResult(
                    article_id="test-1",
                    title="Test Article",
                    url="https://example.com/1",
                    published_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
                    keyword_matches=["test"],
                    hit_count=1,
                    description="Test description"
                )
            ],
            query_time_ms=100,
            filters_applied={"keywords": ["test"]}
        )
        mock_tool.process_query.return_value = mock_response
        
        # Test event
        event = {
            "query": "test query",
            "limit": 50
        }
        
        # Set environment variables
        os.environ.update({
            'ARTICLES_TABLE': 'test-articles',
            'ARTIFACTS_BUCKET': 'test-artifacts',
            'BEDROCK_MODEL_ID': 'test-model'
        })
        
        # Call handler
        result = lambda_handler(event, None)
        
        # Assertions
        assert result['statusCode'] == 200
        assert result['body']['success'] is True
        assert result['body']['total_results'] == 1
        assert len(result['body']['results']) == 1
    
    def test_lambda_handler_missing_query(self):
        """Test Lambda handler with missing query."""
        event = {}
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 500
        assert result['body']['success'] is False
        assert "query" in result['body']['error'].lower()
    
    @patch('lambda_tools.query_kb.QueryKBTool')
    def test_lambda_handler_tool_error(self, mock_tool_class):
        """Test Lambda handler with tool error."""
        mock_tool = Mock()
        mock_tool_class.return_value = mock_tool
        mock_tool.process_query.side_effect = Exception("Test error")
        
        event = {"query": "test"}
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 500
        assert result['body']['success'] is False


if __name__ == "__main__":
    pytest.main([__file__])