"""
Tests for continuous learning endpoints: URL ingestion and crawling.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app


class TestContinuousLearningEndpoints:
    """Tests for the continuous learning endpoints."""

    def setup_method(self):
        """Set up test client for each test."""
        self.client = TestClient(app)

    @patch("app.main.ingest_case_from_url")
    def test_learn_from_url_success(self, mock_ingest):
        """Test successful URL learning endpoint."""
        mock_ingest.return_value = True
        
        response = self.client.post(
            "/api/learn/url",
            json={"url": "https://example.com/legal-case"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Successfully ingested content from verified URL."
        assert data["url"] == "https://example.com/legal-case"
        mock_ingest.assert_called_once_with("https://example.com/legal-case")

    @patch("app.main.ingest_case_from_url")
    def test_learn_from_url_failure(self, mock_ingest):
        """Test failed URL learning endpoint."""
        mock_ingest.return_value = False
        
        response = self.client.post(
            "/api/learn/url",
            json={"url": "https://example.com/failed-case"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Failed to ingest content" in data["detail"]
        mock_ingest.assert_called_once_with("https://example.com/failed-case")

    @patch("app.main.crawl_and_ingest")
    @patch("app.main.ingest_case_from_url")
    def test_crawl_url_success(self, mock_ingest, mock_crawl):
        """Test successful URL crawling endpoint."""
        # Mock crawling to return some cases
        mock_crawl.return_value = [
            {"url": "https://example.com/case1", "title": "Case One"},
            {"url": "https://example.com/case2", "title": "Case Two"}
        ]
        # Mock ingestion to succeed for both
        mock_ingest.return_value = True
        
        response = self.client.post(
            "/api/crawl",
            json={"url": "https://example.com/search-results"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Successfully scouted and learned" in data["message"]
        assert data["message"].endswith("new potential cases.")
        assert "cases" in data
        assert len(data["cases"]) == 2
        
        # Verify crawl was called
        mock_crawl.assert_called_once_with("https://example.com/search-results", limit=3)
        
        # Verify ingestion was called for each case
        assert mock_ingest.call_count == 2
        mock_ingest.assert_any_call("https://example.com/case1", title="Case One")
        mock_ingest.assert_any_call("https://example.com/case2", title="Case Two")

    @patch("app.main.crawl_and_ingest")
    @patch("app.main.ingest_case_from_url")
    def test_crawl_url_partial_failure(self, mock_ingest, mock_crawl):
        """Test crawling endpoint with partial ingestion failures."""
        # Mock crawling to return some cases
        mock_crawl.return_value = [
            {"url": "https://example.com/case1", "title": "Case One"},
            {"url": "https://example.com/case2", "title": "Case Two"},
            {"url": "https://example.com/case3", "title": "Case Three"}
        ]
        # Mock ingestion to succeed for first and third, fail for second
        mock_ingest.side_effect = [True, False, True]
        
        response = self.client.post(
            "/api/crawl",
            json={"url": "https://example.com/search-results"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Successfully scouted and learned 2 new potential cases." in data["message"]
        assert "cases" in data
        assert len(data["cases"]) == 3
        
        # Verify crawl was called
        mock_crawl.assert_called_once_with("https://example.com/search-results", limit=3)
        
        # Verify ingestion was called for each case
        assert mock_ingest.call_count == 3

    @patch("app.main.crawl_and_ingest")
    @patch("app.main.ingest_case_from_url")
    def test_crawl_url_no_cases_found(self, mock_ingest, mock_crawl):
        """Test crawling endpoint when no cases are found."""
        # Mock crawling to return empty list
        mock_crawl.return_value = []
        # Mock ingestion to return False (not called in this case)
        mock_ingest.return_value = False
        
        response = self.client.post(
            "/api/crawl",
            json={"url": "https://example.com/empty-results"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Successfully scouted and learned 0 new potential cases." in data["message"]
        assert "cases" in data
        assert len(data["cases"]) == 0
        
        # Verify crawl was called
        mock_crawl.assert_called_once_with("https://example.com/empty-results", limit=3)
        
        # Verify ingestion was not called
        mock_ingest.assert_not_called()

    def test_learn_from_url_invalid_url(self):
        """Test learning endpoint with invalid URL."""
        response = self.client.post(
            "/api/learn/url",
            json={"url": "not-a-valid-url"}
        )
        
        # Should fail validation due to invalid URL
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "detail" in data

    def test_crawl_url_invalid_url(self):
        """Test crawling endpoint with invalid URL."""
        response = self.client.post(
            "/api/crawl",
            json={"url": "not-a-valid-url"}
        )
        
        # Should fail validation due to invalid URL
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "detail" in data
