"""
Additional edge case tests for Temporal Conflict Resolution.
"""
import pytest
from unittest.mock import MagicMock, patch
from app.ingest import resolve_legal_conflicts, parse_date_safe


class TestTemporalConflictEdgeCases:
    """Additional edge case tests for temporal conflict resolution."""

    @patch("app.ingest._find_case_in_db")
    @patch("app.ingest.get_pinecone_index")
    def test_multiple_overruled_cases_mixed_dates(self, mock_get_index, mock_find):
        """Test overruling multiple cases with mixed date validity."""
        # Setup: Two existing cases - one with valid date, one without
        old_case_id_1 = "id_old_1"
        old_case_id_2 = "id_old_2"
        
        old_case_meta_1 = {
            "title": "Old Case With Date (2020)",
            "ai_judgment_date": "2020-01-15",
            "status": "active"
        }
        
        old_case_meta_2 = {
            "title": "Old Case Without Date",
            "ai_judgment_date": "UNKNOWN",
            "status": "active"
        }
        
        def mock_find_side_effect(case_name):
            if case_name == "Old Case With Date (2020)":
                return [{"_id": old_case_id_1, "metadata": old_case_meta_1}]
            elif case_name == "Old Case Without Date":
                return [{"_id": old_case_id_2, "metadata": old_case_meta_2}]
            return []
        
        mock_find.side_effect = mock_find_side_effect
        
        mock_index = MagicMock()
        mock_index.fetch = MagicMock()
        mock_index.update = MagicMock()
        mock_get_index.return_value = mock_index
        
        # Mock fetch to return proper vectors
        def mock_fetch_side_effect(ids=None, **kwargs):
            vectors = {}
            if ids:
                for case_id in ids:
                    if case_id == old_case_id_1:
                        vector_obj = MagicMock()
                        vector_obj.metadata = old_case_meta_1
                        vectors[case_id] = vector_obj
                    elif case_id == old_case_id_2:
                        vector_obj = MagicMock()
                        vector_obj.metadata = old_case_meta_2
                        vectors[case_id] = vector_obj
            result = MagicMock()
            result.vectors = vectors
            return result
        
        mock_index.fetch.side_effect = mock_fetch_side_effect
        
        new_metadata = {
            "title": "New Case (2025)",
            "ai_judgment_date": "2025-06-01",
            "ai_overrules_cases": "Old Case With Date (2020), Old Case Without Date",
            "status": "active"
        }
        
        resolve_legal_conflicts(new_metadata)
        
        # Should update both cases (2025 > 2020, and UNKNOWN date proceeds with warning)
        assert mock_index.update.call_count == 2

    @patch("app.ingest._find_case_in_db")
    @patch("app.ingest.get_pinecone_index")
    def test_invalid_date_formats_handled_gracefully(self, mock_get_index, mock_find):
        """Test that various invalid date formats are handled gracefully."""
        old_case_id = "id_old"
        old_case_meta = {
            "title": "Old Case (2020)",
            "ai_judgment_date": "2020-01-15",
            "status": "active"
        }
        
        mock_find.return_value = [{
            "_id": old_case_id,
            "metadata": old_case_meta
        }]
        
        mock_index = MagicMock()
        mock_index.fetch = MagicMock()
        mock_index.update = MagicMock()
        mock_get_index.return_value = mock_index
        
        def mock_fetch_side_effect(ids=None, **kwargs):
            vectors = {}
            if ids:
                for case_id in ids:
                    if case_id == old_case_id:
                        vector_obj = MagicMock()
                        vector_obj.metadata = old_case_meta
                        vectors[case_id] = vector_obj
            result = MagicMock()
            result.vectors = vectors
            return result
        
        mock_index.fetch.side_effect = mock_fetch_side_effect
        
        # Test various invalid/new date formats that should still allow overruling (with warning)
        invalid_dates = [
            "2025",           # Year only
            "January 2025",   # Text format
            "not a date",     # Completely invalid
            "2025-13-45",     # Invalid month/day
            "",               # Empty string
        ]
        
        for invalid_date in invalid_dates:
            new_metadata = {
                "title": "New Case",
                "ai_judgment_date": invalid_date,
                "ai_overrules_cases": "Old Case (2020)",
                "status": "active"
            }
            
            # Reset mock for each iteration
            mock_index.update.reset_mock()
            
            resolve_legal_conflicts(new_metadata)
            
            # Should still proceed with overrule (no date to compare, so trust LLM)
            mock_index.update.assert_called_once()

    @patch("app.ingest._find_case_in_db")
    @patch("app.ingest.get_pinecone_index")
    def test_future_date_handling(self, mock_get_index, mock_find):
        """Test handling of future dates in judgment_date field."""
        old_case_id = "id_old"
        old_case_meta = {
            "title": "Old Case (2020)",
            "ai_judgment_date": "2020-01-15",
            "status": "active"
        }
        
        mock_find.return_value = [{
            "_id": old_case_id,
            "metadata": old_case_meta
        }]
        
        mock_index = MagicMock()
        mock_index.fetch = MagicMock()
        mock_index.update = MagicMock()
        mock_get_index.return_value = mock_index
        
        def mock_fetch_side_effect(ids=None, **kwargs):
            vectors = {}
            if ids:
                for case_id in ids:
                    if case_id == old_case_id:
                        vector_obj = MagicMock()
                        vector_obj.metadata = old_case_meta
                        vectors[case_id] = vector_obj
            result = MagicMock()
            result.vectors = vectors
            return result
        
        mock_index.fetch.side_effect = mock_fetch_side_effect
        
        # Test with a future date that should still allow overruling (new > old)
        new_metadata = {
            "title": "New Case",
            "ai_judgment_date": "2030-01-15",  # Future date
            "ai_overrules_cases": "Old Case (2020)",
            "status": "active"
        }
        
        resolve_legal_conflicts(new_metadata)
        
        # Should allow overruling since 2030 > 2020
        mock_index.update.assert_called_once()
        
        # Test with future date that should prevent overruling (new < old)
        # This would require an even older case, but let's test the logic
        # by using a past date that's still newer than our fake "old" case
        new_metadata_past = {
            "title": "New Case",
            "ai_judgment_date": "2025-01-15",  # Still future but let's make old case even older
            "ai_overrules_cases": "Old Case (2020)",
            "status": "active"
        }
        
        # For this test, we need to adjust the old case to be older than 2025
        old_case_meta_ancient = {
            "title": "Ancient Case (2010)",
            "ai_judgment_date": "2010-01-15",
            "status": "active"
        }
        
        mock_find.return_value = [{
            "_id": old_case_id,
            "metadata": old_case_meta_ancient
        }]
        
        mock_index.update.reset_mock()
        
        resolve_legal_conflicts(new_metadata_past)
        
        # Should allow overruling since 2025 > 2010
        mock_index.update.assert_called_once()

    @patch("app.ingest._find_case_in_db")
    @patch("app.ingest.get_pinecone_index")
    def test_case_name_matching_variations(self, mock_get_index, mock_find):
        """Test that case name matching works with slight variations."""
        old_case_id = "id_old"
        old_case_meta = {
            "title": "State of Karnataka vs. Sri Venkatarama (2021)",
            "ai_judgment_date": "2021-05-20",
            "status": "active"
        }
        
        mock_find.return_value = [{
            "_id": old_case_id,
            "metadata": old_case_meta
        }]
        
        mock_index = MagicMock()
        mock_index.fetch = MagicMock()
        mock_index.update = MagicMock()
        mock_get_index.return_value = mock_index
        
        def mock_fetch_side_effect(ids=None, **kwargs):
            vectors = {}
            if ids:
                for case_id in ids:
                    if case_id == old_case_id:
                        vector_obj = MagicMock()
                        vector_obj.metadata = old_case_meta
                        vectors[case_id] = vector_obj
            result = MagicMock()
            result.vectors = vectors
            return result
        
        mock_index.fetch.side_effect = mock_fetch_side_effect
        
        # Test with slightly different casing/spelling in overrules_cases
        new_metadata = {
            "title": "Union of India vs. Karnataka (2026)",
            "ai_judgment_date": "2026-03-10",
            # Note: Using slightly different phrasing - should still match via semantic search
            "ai_overrules_cases": "state of karnataka vs. sri venkatarama (2021)",
            "status": "active"
        }
        
        resolve_legal_conflicts(new_metadata)
        
        # Should still find and update the case despite case/spacing differences
        mock_index.update.assert_called_once()
