"""
Edge case tests for extraction validation in app.core.extraction.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from app.core.extraction import extract_legal_metadata, CaseMetadata


class TestCaseMetadataValidationEdgeCases:
    """Edge case tests for CaseMetadata Pydantic model validation."""

    def test_case_name_whitespace_handling(self):
        """Test that leading/trailing whitespace in case_name is handled."""
        data = {
            "case_name": "  ABC Corp vs. State of Maharashtra  ",
            "judgment_date": "2024-01-15",
            "overrules_cases": [],
            "upholds_cases": [],
            "legal_domain": "General"
        }
        meta = CaseMetadata(**data)
        # Pydantic should preserve whitespace unless configured otherwise
        assert meta.case_name == "  ABC Corp vs. State of Maharashtra  "

    def test_empty_case_name_allowed_but_meaningless(self):
        """Test that empty case_name is allowed but meaningless."""
        # Pydantic doesn't reject empty strings for str fields by default
        data = {
            "case_name": "",
            "judgment_date": "2024-01-15",
            "overrules_cases": [],
            "upholds_cases": [],
            "legal_domain": "General"
        }
        meta = CaseMetadata(**data)
        assert meta.case_name == ""

    def test_negative_year_date_parsed_as_literal_string(self):
        """Test that negative years in date are treated as literal strings (not parsed)."""
        # The judgment_date field is a str, not a date, so "-2024-01-15" is valid
        data = {
            "case_name": "Test Case",
            "judgment_date": "-2024-01-15",
            "overrules_cases": [],
            "upholds_cases": [],
            "legal_domain": "General"
        }
        meta = CaseMetadata(**data)
        assert meta.judgment_date == "-2024-01-15"
        # validated_date will be None because it can't parse the negative year
        assert meta.validated_date is None

    def test_future_date_accepted(self):
        """Test that future dates are accepted (no validation against real dates)."""
        data = {
            "case_name": "Future Case",
            "judgment_date": "2030-01-15",
            "overrules_cases": [],
            "upholds_cases": [],
            "legal_domain": "General"
        }
        meta = CaseMetadata(**data)
        assert meta.validated_date == date(2030, 1, 15)

    def test_leap_year_date_handling(self):
        """Test that leap year dates are handled correctly."""
        data = {
            "case_name": "Leap Year Case",
            "judgment_date": "2024-02-29",  # Valid leap year date
            "overrules_cases": [],
            "upholds_cases": [],
            "legal_domain": "General"
        }
        meta = CaseMetadata(**data)
        assert meta.validated_date == date(2024, 2, 29)

    def test_invalid_leap_year_date_string_preserved(self):
        """Test that invalid leap year dates are preserved as strings."""
        # judgment_date is a str field, so "2023-02-29" is valid as a string
        data = {
            "case_name": "Test Case",
            "judgment_date": "2023-02-29",  # Invalid date but valid string
            "overrules_cases": [],
            "upholds_cases": [],
            "legal_domain": "General"
        }
        meta = CaseMetadata(**data)
        assert meta.judgment_date == "2023-02-29"
        # validated_date will be None because it can't parse as a valid date
        assert meta.validated_date is None

    def test_overrules_cases_with_empty_strings(self):
        """Test that overrules_cases with empty strings are preserved."""
        data = {
            "case_name": "Test Case",
            "judgment_date": "2024-01-15",
            "overrules_cases": ["Valid Case", "", "Another Valid Case"],
            "upholds_cases": [],
            "legal_domain": "General"
        }
        meta = CaseMetadata(**data)
        # Pydantic preserves the list as-is
        assert meta.overrules_cases == ["Valid Case", "", "Another Valid Case"]

    def test_overrules_cases_with_duplicate_entries(self):
        """Test that duplicate entries in overrules_cases are preserved."""
        data = {
            "case_name": "Test Case",
            "judgment_date": "2024-01-15",
            "overrules_cases": ["Case A", "Case B", "Case A"],
            "upholds_cases": [],
            "legal_domain": "General"
        }
        meta = CaseMetadata(**data)
        # Pydantic preserves duplicates
        assert meta.overrules_cases == ["Case A", "Case B", "Case A"]

    def test_legal_domain_case_sensitivity(self):
        """Test that legal_domain preserves case sensitivity."""
        data = {
            "case_name": "Test Case",
            "judgment_date": "2024-01-15",
            "overrules_cases": [],
            "upholds_cases": [],
            "legal_domain": "intellectual property"  # lowercase
        }
        meta = CaseMetadata(**data)
        assert meta.legal_domain == "intellectual property"

    def test_legal_domain_with_special_characters(self):
        """Test that legal_domain accepts special characters."""
        data = {
            "case_name": "Test Case",
            "judgment_date": "2024-01-15",
            "overrules_cases": [],
            "upholds_cases": [],
            "legal_domain": "Intellectual Property (IP)"
        }
        meta = CaseMetadata(**data)
        assert meta.legal_domain == "Intellectual Property (IP)"


class TestExtractLegalMetadataEdgeCases:
    """Edge case tests for the extract_legal_metadata function."""

    @patch("app.core.extraction.client")
    def test_llm_returns_null_values(self, mock_client):
        """Test handling when LLM returns null values for fields."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "case_name": "Valid Case",
            "judgment_date": None,  # NULL value
            "overrules_cases": None,  # NULL value
            "upholds_cases": None,  # NULL value
            "legal_domain": None   # NULL value
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        result = extract_legal_metadata("Some legal text here...")
        
        # Should handle NULL values appropriately - validation fails and returns empty dict
        assert result == {}

    @patch("app.core.extraction.client")
    def test_llm_returns_empty_strings(self, mock_client):
        """Test handling when LLM returns empty strings."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "case_name": "",  # Empty string
            "judgment_date": "",  # Empty string
            "overrules_cases": [],  # Empty list
            "upholds_cases": [],  # Empty list
            "legal_domain": ""   # Empty string
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        result = extract_legal_metadata("Some legal text here...")
        
        # Empty strings are valid for str fields, so validation passes
        # Empty judgment_date results in validated_date=None
        assert result["case_name"] == ""
        assert result["judgment_date"] == ""
        assert result["legal_domain"] == ""
        assert result["overrules_cases"] == []
        assert result["upholds_cases"] == []
        assert result["validated_date"] is None

    @patch("app.core.extraction.client")
    def test_llm_returns_extra_fields(self, mock_client):
        """Test that extra fields in LLM output are ignored."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "case_name": "Valid Case",
            "judgment_date": "2024-01-15",
            "overrules_cases": ["Old Case"],
            "upholds_cases": [],
            "legal_domain": "Constitutional Law",
            "extra_field": "should be ignored",
            "another_extra": 123
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        result = extract_legal_metadata("Some legal text here...")
        
        # Should only contain the validated fields
        assert result["case_name"] == "Valid Case"
        assert result["judgment_date"] == "2024-01-15"
        assert result["overrules_cases"] == ["Old Case"]
        assert result["upholds_cases"] == []
        assert result["legal_domain"] == "Constitutional Law"
        assert "extra_field" not in result
        assert "another_extra" not in result

    @patch("app.core.extraction.client")
    def test_llm_returns_nested_objects(self, mock_client):
        """Test handling when LLM returns nested objects instead of primitives."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "case_name": {"nested": "object"},  # Invalid type
            "judgment_date": "2024-01-15",
            "overrules_cases": ["Old Case"],
            "upholds_cases": [],
            "legal_domain": "Constitutional Law"
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        result = extract_legal_metadata("Some legal text here...")
        
        # Should reject invalid type and try next model
        # Since we only mock one call, should return empty dict
        assert result == {}

    @patch("app.core.extraction.client")
    def test_llm_returns_overrules_as_string_instead_of_list(self, mock_client):
        """Test handling when LLM returns overrules_cases as string instead of list."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "case_name": "Valid Case",
            "judgment_date": "2024-01-15",
            "overrules_cases": "Old Case vs. State",  # String instead of list
            "upholds_cases": [],
            "legal_domain": "Constitutional Law"
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        result = extract_legal_metadata("Some legal text here...")
        
        # Should reject invalid type and try next model
        # Since we only mock one call, should return empty dict
        assert result == {}

    @patch("app.core.extraction.client")
    def test_all_models_return_same_invalid_output(self, mock_client):
        """Test behavior when all models in cascade return invalid output."""
        # Mock all calls to return invalid JSON
        mock_client.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content="INVALID JSON 1"))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content="INVALID JSON 2"))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content="INVALID JSON 3"))]),
            # Add more to cover all models in the cascade
        ] * 4  # Repeat to ensure we cover all 10 models
        
        result = extract_legal_metadata("Some text")
        
        # Should exhaust all models and return empty dict
        assert result == {}

    @patch("app.core.extraction.client")
    def test_models_return_different_invalid_outputs(self, mock_client):
        """Test behavior when models return different types of invalid output."""
        mock_client.chat.completions.create.side_effect = [
            # First model: invalid JSON
            MagicMock(choices=[MagicMock(message=MagicMock(content="NOT JSON"))]),
            # Second model: valid JSON but wrong types
            MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps({
                "case_name": 123,  # Wrong type
                "judgment_date": "2024-01-15",
                "overrules_cases": [],
                "upholds_cases": [],
                "legal_domain": "General"
            })))]),
            # Third model: valid JSON but missing required field
            MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps({
                "judgment_date": "2024-01-15",  # Missing case_name
                "overrules_cases": [],
                "upholds_cases": [],
                "legal_domain": "General"
            })))]),
            # Fourth model: valid and correct
            MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps({
                "case_name": "Valid Case",
                "judgment_date": "2024-01-15",
                "overrules_cases": ["Old Case"],
                "upholds_cases": [],
                "legal_domain": "Constitutional Law"
            })))]),
        ]
        
        result = extract_legal_metadata("Some text")
        
        # Should succeed on the fourth model
        assert result["case_name"] == "Valid Case"
        assert result["judgment_date"] == "2024-01-15"
        assert result["overrules_cases"] == ["Old Case"]
        assert result["legal_domain"] == "Constitutional Law"
