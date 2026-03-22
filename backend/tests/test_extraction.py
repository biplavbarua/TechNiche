"""
Tests for app.core.extraction — Pydantic validation, date parsing, and model fallback.

These replace the previous ad-hoc test scripts with proper pytest assertions.
Run: cd backend && python -m pytest tests/test_extraction.py -v
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from app.core.extraction import extract_legal_metadata, CaseMetadata


class TestCaseMetadataValidation:
    """Tests that CaseMetadata Pydantic model catches malformed LLM output."""
    
    def test_valid_full_metadata(self):
        data = {
            "case_name": "ABC Corp vs. State of Maharashtra",
            "judgment_date": "2024-01-15",
            "overrules_cases": ["OldCorp vs. State"],
            "upholds_cases": [],
            "legal_domain": "Intellectual Property"
        }
        meta = CaseMetadata(**data)
        assert meta.case_name == "ABC Corp vs. State of Maharashtra"
        assert meta.validated_date == date(2024, 1, 15)
        assert meta.overrules_cases == ["OldCorp vs. State"]
        assert meta.legal_domain == "Intellectual Property"
    
    def test_unknown_date_produces_none_validated_date(self):
        data = {
            "case_name": "Test Case",
            "judgment_date": "UNKNOWN",
            "overrules_cases": [],
            "upholds_cases": [],
            "legal_domain": "General"
        }
        meta = CaseMetadata(**data)
        assert meta.validated_date is None
    
    def test_alternative_date_format_dd_mm_yyyy(self):
        data = {
            "case_name": "Test Case",
            "judgment_date": "15-01-2024",
            "overrules_cases": [],
            "upholds_cases": [],
            "legal_domain": "General"
        }
        meta = CaseMetadata(**data)
        assert meta.validated_date == date(2024, 1, 15)
    
    def test_missing_optional_fields_get_defaults(self):
        data = {
            "case_name": "Minimal Case",
            "judgment_date": "2023-06-01"
        }
        meta = CaseMetadata(**data)
        assert meta.overrules_cases == []
        assert meta.upholds_cases == []
        assert meta.legal_domain == "General"
    
    def test_missing_required_field_raises(self):
        """case_name is required — missing it should raise ValidationError."""
        with pytest.raises(Exception):
            CaseMetadata(judgment_date="2024-01-01")
    
    def test_wrong_type_for_overrules_raises(self):
        """overrules_cases must be a list, not a string."""
        with pytest.raises(Exception):
            CaseMetadata(
                case_name="Test",
                judgment_date="2024-01-01",
                overrules_cases="NotAList"
            )
    
    def test_unparseable_date_returns_none(self):
        """Garbage date should produce validated_date=None, not crash."""
        data = {
            "case_name": "Test",
            "judgment_date": "someday last year",
            "overrules_cases": [],
            "upholds_cases": [],
            "legal_domain": "General"
        }
        meta = CaseMetadata(**data)
        assert meta.validated_date is None


class TestExtractLegalMetadata:
    """Integration tests for the extraction pipeline with mocked LLM responses."""
    
    @patch("app.core.extraction.client")
    def test_successful_extraction_returns_validated_dict(self, mock_client):
        """When the LLM returns valid JSON, we get a validated dictionary."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "case_name": "Good Case vs. State",
            "judgment_date": "2024-03-15",
            "overrules_cases": ["Bad Case vs. State"],
            "upholds_cases": [],
            "legal_domain": "Constitutional Law"
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        result = extract_legal_metadata("Some legal text here...")
        
        assert result["case_name"] == "Good Case vs. State"
        assert result["validated_date"] == date(2024, 3, 15)
        assert result["overrules_cases"] == ["Bad Case vs. State"]
    
    @patch("app.core.extraction.client")
    def test_invalid_json_tries_next_model(self, mock_client):
        """When the LLM returns garbage, it should try the next model in the cascade."""
        # First call returns invalid JSON, second returns valid
        response_bad = MagicMock()
        response_bad.choices = [MagicMock()]
        response_bad.choices[0].message.content = "NOT JSON AT ALL"
        
        response_good = MagicMock()
        response_good.choices = [MagicMock()]
        response_good.choices[0].message.content = json.dumps({
            "case_name": "Recovered Case",
            "judgment_date": "2024-01-01",
            "overrules_cases": [],
            "upholds_cases": [],
            "legal_domain": "Tax Law"
        })
        
        mock_client.chat.completions.create.side_effect = [response_bad, response_good]
        
        result = extract_legal_metadata("Some text")
        assert result["case_name"] == "Recovered Case"
    
    @patch("app.core.extraction.client", None)
    def test_no_api_key_returns_empty_dict(self):
        """When there's no API client configured, return empty dict gracefully."""
        result = extract_legal_metadata("Some text")
        assert result == {}
    
    @patch("app.core.extraction.client")
    def test_pydantic_validation_catches_wrong_keys(self, mock_client):
        """If LLM returns wrong field names, Pydantic should reject it and try next model."""
        # All models return wrong keys
        bad_response = MagicMock()
        bad_response.choices = [MagicMock()]
        bad_response.choices[0].message.content = json.dumps({
            "ruling_name": "Wrong Key Case",  # wrong key!
            "ruling_date": "2024-01-01"        # wrong key!
        })
        mock_client.chat.completions.create.return_value = bad_response
        
        result = extract_legal_metadata("Some text")
        # Should either raise or (since it retries all models with same bad output) return {}
        # The key point is it doesn't silently pass through bad data
        # Since case_name is required, Pydantic will reject and the cascade exhausts → empty
        assert result == {} or "case_name" in result
