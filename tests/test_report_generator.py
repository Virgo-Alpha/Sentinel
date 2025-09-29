"""
Unit tests for Enhanced Report Generator.
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

# Import the module under test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_tools.report_generator import (
    EnhancedReportGenerator, XLSXReportGenerator, KeywordAnalyzer,
    BatchProcessor, ReportConfig, ReportResult
)


class TestKeywordAnalyzer:
    """Test cases for KeywordAnalyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = KeywordAnalyzer()
        
        self.sample_results = [
            {
                "article_id": "test-1",
                "title": "Microsoft Azure Security Alert",
                "keyword_matches": ["Microsoft", "Azure", "security"],
                "hit_count": 5
            },
            {
                "article_id": "test-2", 
                "title": "AWS Vulnerability Report",
                "keyword_matches": ["AWS", "vulnerability"],
                "hit_count": 3
            },
            {
                "article_id": "test-3",
                "title": "Microsoft Windows Update",
                "keyword_matches": ["Microsoft", "Windows"],
                "hit_count": 2
            }
        ]
    
    def test_analyze_keyword_hits(self):
        """Test keyword hit analysis."""
        analysis = self.analyzer.analyze_keyword_hits(self.sample_results)
        
        # Check basic statistics
        assert analysis['total_articles'] == 3
        assert analysis['total_keyword_hits'] == 10  # 5 + 3 + 2
        assert analysis['unique_keywords'] == 6  # Microsoft, Azure, security, AWS, vulnerability, Windows
        assert analysis['average_hits_per_article'] == 10/3
        
        # Check keyword breakdown
        keyword_breakdown = analysis['keyword_breakdown']
        assert 'Microsoft' in keyword_breakdown
        assert keyword_breakdown['Microsoft']['article_count'] == 2  # appears in 2 articles
        
        # Check percentages
        microsoft_stats = keyword_breakdown['Microsoft']
        assert microsoft_stats['articles_percentage'] == (2/3) * 100
    
    def test_analyze_empty_results(self):
        """Test analysis with empty results."""
        analysis = self.analyzer.analyze_keyword_hits([])
        
        assert analysis['total_articles'] == 0
        assert analysis['total_keyword_hits'] == 0
        assert analysis['unique_keywords'] == 0
        assert analysis['average_hits_per_article'] == 0


class TestBatchProcessor:
    """Test cases for BatchProcessor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = BatchProcessor(batch_size=2)
    
    def test_process_in_batches(self):
        """Test batch processing functionality."""
        # Sample data
        data = [1, 2, 3, 4, 5]
        
        # Mock processor function
        def mock_processor(batch):
            return [x * 2 for x in batch]
        
        # Process in batches
        results = self.processor.process_in_batches(data, mock_processor)
        
        # Should return all items processed
        assert results == [2, 4, 6, 8, 10]
    
    def test_batch_processing_with_errors(self):
        """Test batch processing with errors in some batches."""
        data = [1, 2, 3, 4, 5]
        
        def error_processor(batch):
            if 3 in batch:
                raise Exception("Test error")
            return [x * 2 for x in batch]
        
        # Should continue processing other batches despite errors
        results = self.processor.process_in_batches(data, error_processor)
        
        # Should have results from successful batches only
        assert len(results) < len(data) * 2  # Some batches failed


class TestReportConfig:
    """Test cases for ReportConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ReportConfig()
        
        assert config.format == "xlsx"
        assert config.sort_by == "published_at"
        assert config.sort_order == "desc"
        assert config.batch_size == 1000
        assert config.include_keyword_analysis is True
        assert config.include_summary_stats is True
        
        # Check default columns
        expected_columns = [
            "title", "url", "published_at", "keyword", 
            "hit_count", "description", "source", "relevancy_score", "tags"
        ]
        assert config.include_columns == expected_columns
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = ReportConfig(
            format="json",
            sort_by="hit_count",
            sort_order="asc",
            include_columns=["title", "url", "hit_count"]
        )
        
        assert config.format == "json"
        assert config.sort_by == "hit_count"
        assert config.sort_order == "asc"
        assert config.include_columns == ["title", "url", "hit_count"]


class TestXLSXReportGenerator:
    """Test cases for XLSXReportGenerator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_s3_client = Mock()
        self.generator = XLSXReportGenerator(self.mock_s3_client, "test-bucket")
        
        self.sample_results = [
            {
                "article_id": "test-1",
                "title": "Microsoft Azure Security Alert",
                "url": "https://example.com/1",
                "published_at": "2024-01-15T10:00:00Z",
                "keyword_matches": ["Microsoft", "Azure"],
                "hit_count": 5,
                "description": "Critical security issue",
                "source": "Microsoft Security",
                "relevancy_score": 0.9,
                "tags": ["Security", "Cloud"]
            },
            {
                "article_id": "test-2",
                "title": "AWS Vulnerability Report",
                "url": "https://example.com/2", 
                "published_at": "2024-01-14T15:30:00Z",
                "keyword_matches": ["AWS"],
                "hit_count": 3,
                "description": "New vulnerability discovered",
                "source": "AWS Security",
                "relevancy_score": 0.8,
                "tags": ["Vulnerability"]
            }
        ]
    
    def test_sort_results_by_date_desc(self):
        """Test sorting results by published date descending."""
        config = ReportConfig(sort_by="published_at", sort_order="desc")
        sorted_results = self.generator._sort_results(self.sample_results, config.sort_by, config.sort_order)
        
        # Should be sorted by date descending (newest first)
        assert sorted_results[0]["article_id"] == "test-1"  # 2024-01-15
        assert sorted_results[1]["article_id"] == "test-2"  # 2024-01-14
    
    def test_sort_results_by_hit_count(self):
        """Test sorting results by hit count."""
        config = ReportConfig(sort_by="hit_count", sort_order="desc")
        sorted_results = self.generator._sort_results(self.sample_results, config.sort_by, config.sort_order)
        
        # Should be sorted by hit count descending
        assert sorted_results[0]["hit_count"] == 5  # test-1
        assert sorted_results[1]["hit_count"] == 3  # test-2
    
    def test_sort_results_by_title(self):
        """Test sorting results by title alphabetically."""
        config = ReportConfig(sort_by="title", sort_order="asc")
        sorted_results = self.generator._sort_results(self.sample_results, config.sort_by, config.sort_order)
        
        # Should be sorted alphabetically by title
        assert sorted_results[0]["title"].startswith("AWS")  # AWS comes before Microsoft
        assert sorted_results[1]["title"].startswith("Microsoft")
    
    @patch('openpyxl.Workbook')
    def test_generate_xlsx_report_success(self, mock_workbook):
        """Test successful XLSX report generation."""
        # Mock openpyxl
        mock_wb = Mock()
        mock_ws = Mock()
        mock_wb.create_sheet.return_value = mock_ws
        mock_wb.remove = Mock()
        mock_workbook.return_value = mock_wb
        
        # Mock S3 operations
        self.mock_s3_client.put_object = Mock()
        self.mock_s3_client.generate_presigned_url.return_value = "https://s3.example.com/report.xlsx"
        
        config = ReportConfig()
        result = self.generator.generate_xlsx_report(self.sample_results, config)
        
        # Check result
        assert result.success is True
        assert result.report_url == "https://s3.example.com/report.xlsx"
        assert result.total_records == 2
        assert result.processing_time_ms > 0
        
        # Verify S3 operations
        self.mock_s3_client.put_object.assert_called_once()
        self.mock_s3_client.generate_presigned_url.assert_called_once()
    
    def test_generate_xlsx_report_no_openpyxl(self):
        """Test XLSX report generation when openpyxl is not available."""
        with patch('builtins.__import__', side_effect=ImportError):
            config = ReportConfig()
            result = self.generator.generate_xlsx_report(self.sample_results, config)
            
            assert result.success is False
            assert "openpyxl not available" in result.errors[0]


class TestEnhancedReportGenerator:
    """Test cases for EnhancedReportGenerator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('boto3.client'):
            self.generator = EnhancedReportGenerator("test-bucket")
        
        self.sample_results = [
            {
                "article_id": "test-1",
                "title": "Test Article 1",
                "url": "https://example.com/1",
                "published_at": "2024-01-15T10:00:00Z",
                "keyword_matches": ["test"],
                "hit_count": 1,
                "description": "Test description",
                "source": "Test Source",
                "relevancy_score": 0.9,
                "tags": ["Test"]
            }
        ]
    
    @patch.object(XLSXReportGenerator, 'generate_xlsx_report')
    def test_generate_xlsx_report(self, mock_xlsx_gen):
        """Test XLSX report generation."""
        mock_result = ReportResult(success=True, report_url="https://example.com/report.xlsx")
        mock_xlsx_gen.return_value = mock_result
        
        config = ReportConfig(format="xlsx")
        result = self.generator.generate_report(self.sample_results, config)
        
        assert result.success is True
        assert result.report_url == "https://example.com/report.xlsx"
        mock_xlsx_gen.assert_called_once()
    
    @patch('boto3.client')
    def test_generate_json_report(self, mock_boto3):
        """Test JSON report generation."""
        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        mock_s3.put_object = Mock()
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/report.json"
        
        generator = EnhancedReportGenerator("test-bucket")
        config = ReportConfig(format="json")
        result = generator.generate_report(self.sample_results, config)
        
        assert result.success is True
        assert result.report_url == "https://s3.example.com/report.json"
        mock_s3.put_object.assert_called_once()
    
    @patch('boto3.client')
    def test_generate_csv_report(self, mock_boto3):
        """Test CSV report generation."""
        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        mock_s3.put_object = Mock()
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/report.csv"
        
        generator = EnhancedReportGenerator("test-bucket")
        config = ReportConfig(format="csv")
        result = generator.generate_report(self.sample_results, config)
        
        assert result.success is True
        assert result.report_url == "https://s3.example.com/report.csv"
        mock_s3.put_object.assert_called_once()
    
    def test_unsupported_format(self):
        """Test handling of unsupported report format."""
        config = ReportConfig(format="pdf")  # Unsupported format
        result = self.generator.generate_report(self.sample_results, config)
        
        assert result.success is False
        assert "Unsupported report format" in result.errors[0]
    
    def test_default_config(self):
        """Test report generation with default config."""
        with patch.object(self.generator, '_generate_xlsx_report') as mock_xlsx:
            mock_xlsx.return_value = ReportResult(success=True)
            
            result = self.generator.generate_report(self.sample_results)
            
            assert result.success is True
            mock_xlsx.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])