"""
Tests for Temporal Conflict Resolution — the novel core of the pipeline.

Verifies that overruling ONLY works when the new case is chronologically newer.
Run: cd backend && python -m pytest tests/test_conflict_resolution.py -v
"""
import pytest
from unittest.mock import MagicMock, patch
from app.ingest import resolve_legal_conflicts, parse_date_safe, chunk_text


class TestParseDateSafe:
    """Tests for the date parsing utility."""
    
    def test_iso_format(self):
        assert parse_date_safe("2024-01-15") is not None
        assert parse_date_safe("2024-01-15").year == 2024
    
    def test_dd_mm_yyyy_format(self):
        result = parse_date_safe("15-01-2024")
        assert result is not None
        assert result.day == 15
    
    def test_unknown_returns_none(self):
        assert parse_date_safe("UNKNOWN") is None
    
    def test_empty_returns_none(self):
        assert parse_date_safe("") is None
    
    def test_garbage_returns_none(self):
        assert parse_date_safe("last Tuesday probably") is None


class TestTemporalConflictResolution:
    """Tests that the overruling logic respects chronological ordering."""
    
    def _make_mock_index(self, existing_cases: list[dict] = None):
        """Creates a mock Pinecone index with pre-loaded cases."""
        mock_index = MagicMock()
        
        # Mock search
        def mock_search(**kwargs):
            query = kwargs.get("query", {})
            filter_dict = query.get("filter", {})
            status_filter = filter_dict.get("status", {}).get("$eq")
            
            matches = []
            if existing_cases:
                for case in existing_cases:
                    if status_filter and case["metadata"].get("status") != status_filter:
                        continue
                    # For testing we assume a match if it's there
                    matches.append({
                        "_id": case["id"],
                        "metadata": case["metadata"]
                    })
            return {"matches": matches}
        
        mock_index.search = MagicMock(side_effect=mock_search)
        
        # Mock fetch
        def mock_fetch(ids=None, **kwargs):
            vectors = {}
            if existing_cases:
                for case in existing_cases:
                    if case["id"] in ids:
                        # Wrap metadata in an object that has it as an attribute
                        # Since ingest.py uses vec.metadata
                        vector_obj = MagicMock()
                        vector_obj.metadata = case["metadata"]
                        vectors[case["id"]] = vector_obj
            
            result = MagicMock()
            result.vectors = vectors
            return result
            
        mock_index.fetch = MagicMock(side_effect=mock_fetch)
        mock_index.update = MagicMock()
        
        return mock_index
    
    @patch("app.ingest._find_case_in_db")
    def test_newer_case_overrules_older_case(self, mock_find):
        """A 2026 case should successfully overrule a 2021 case."""
        old_case_id = "id_old"
        old_case_meta = {
            "title": "Tech Innovations vs Karnataka (2021)",
            "ai_judgment_date": "2021-05-15",
            "status": "active"
        }
        
        # _find_case_in_db returns matches
        mock_find.return_value = [{
            "_id": old_case_id,
            "metadata": old_case_meta
        }]
        
        mock_index = self._make_mock_index([{"id": old_case_id, "metadata": old_case_meta}])
        
        new_metadata = {
            "title": "Union of India vs Tech Innovations (2026)",
            "ai_judgment_date": "2026-03-01",
            "ai_overrules_cases": "Tech Innovations vs Karnataka (2021)",
            "status": "active"
        }
        
        resolve_legal_conflicts(new_metadata, index=mock_index)
        
        # Verify update was called
        mock_index.update.assert_called_once()
        call_args = mock_index.update.call_args
        updated_meta = call_args[1]["set_metadata"]
        
        assert updated_meta["status"] == "overruled"
        assert updated_meta["overruled_by"] == "Union of India vs Tech Innovations (2026)"
    
    @patch("app.ingest._find_case_in_db")
    def test_older_case_cannot_overrule_newer_case(self, mock_find):
        """A 2015 case claiming to overrule a 2020 case should be REJECTED."""
        newer_case_id = "id_newer"
        newer_case_meta = {
            "title": "Modern Case (2020)",
            "ai_judgment_date": "2020-08-20",
            "status": "active"
        }
        
        mock_find.return_value = [{
            "_id": newer_case_id,
            "metadata": newer_case_meta
        }]
        
        mock_index = self._make_mock_index([{"id": newer_case_id, "metadata": newer_case_meta}])
        
        # An old case claims to overrule a newer one
        old_case_metadata = {
            "title": "Ancient Case (2015)",
            "ai_judgment_date": "2015-03-10",
            "ai_overrules_cases": "Modern Case (2020)",
            "status": "active"
        }
        
        resolve_legal_conflicts(old_case_metadata, index=mock_index)
        
        # update should NOT be called — temporal rejection
        mock_index.update.assert_not_called()
    
    @patch("app.ingest._find_case_in_db")
    def test_same_date_does_not_overrule(self, mock_find):
        """Cases with the same judgment date should NOT overrule each other."""
        existing_case_id = "id_same"
        existing_case_meta = {
            "title": "Same Day Case",
            "ai_judgment_date": "2023-06-01",
            "status": "active"
        }
        
        mock_find.return_value = [{
            "_id": existing_case_id,
            "metadata": existing_case_meta
        }]
        
        mock_index = self._make_mock_index([{"id": existing_case_id, "metadata": existing_case_meta}])
        
        new_metadata = {
            "title": "Another Same Day Case",
            "ai_judgment_date": "2023-06-01",
            "ai_overrules_cases": "Same Day Case",
            "status": "active"
        }
        
        resolve_legal_conflicts(new_metadata, index=mock_index)
        
        # Should NOT overrule (new_case_date <= old_case_date)
        mock_index.update.assert_not_called()
    
    @patch("app.ingest.get_pinecone_index")
    def test_no_overrules_field_is_noop(self, mock_get_index):
        """If ai_overrules_cases is empty, nothing happens."""
        mock_index = self._make_mock_index()
        mock_get_index.return_value = mock_index
        
        metadata = {
            "title": "Peaceful Case",
            "ai_judgment_date": "2024-01-01",
            "ai_overrules_cases": "",
            "status": "active"
        }
        
        resolve_legal_conflicts(metadata)
        mock_index.update.assert_not_called()
    
    @patch("app.ingest._find_case_in_db")
    @patch("app.ingest.get_pinecone_index")
    def test_overruled_case_not_in_db_skips_gracefully(self, mock_get_index, mock_find):
        """If the overruled case isn't in the DB, log and skip — don't crash."""
        mock_index = self._make_mock_index()  # empty DB
        mock_get_index.return_value = mock_index
        mock_find.return_value = []
        
        metadata = {
            "title": "New Case (2026)",
            "ai_judgment_date": "2026-01-01",
            "ai_overrules_cases": "Nonexistent Case (2010)",
            "status": "active"
        }
        
        # Should not raise any exception
        resolve_legal_conflicts(metadata)
        mock_index.update.assert_not_called()
    
    @patch("app.ingest._find_case_in_db")
    def test_unknown_new_date_still_overrules_with_warning(self, mock_find):
        """If the new case has no parseable date, proceed with LLM assertion (lower confidence)."""
        old_case_id = "id_old"
        old_case_meta = {
            "title": "Dated Case (2020)",
            "ai_judgment_date": "2020-01-01",
            "status": "active"
        }
        
        mock_find.return_value = [{
            "_id": old_case_id,
            "metadata": old_case_meta
        }]
        
        mock_index = self._make_mock_index([{"id": old_case_id, "metadata": old_case_meta}])
        
        new_metadata = {
            "title": "Undated Case",
            "ai_judgment_date": "UNKNOWN",
            "ai_overrules_cases": "Dated Case (2020)",
            "status": "active"
        }
        
        resolve_legal_conflicts(new_metadata, index=mock_index)
        
        # Should still overrule (no date to reject, so we trust the LLM with a warning)
        mock_index.update.assert_called_once()
        call_args = mock_index.update.call_args
        assert call_args[1]["id"] == old_case_id
        assert call_args[1]["set_metadata"]["status"] == "overruled"



class TestChunking:
    """Tests for the sliding-window text chunking."""
    
    def test_short_text_single_chunk(self):
        """Text shorter than chunk size produces exactly one chunk."""
        text = "A" * 500
        chunks = chunk_text(text)
        assert len(chunks) == 1
    
    def test_long_text_multiple_chunks(self):
        """Long text is split into multiple overlapping chunks."""
        text = "A" * 5000
        chunks = chunk_text(text)
        assert len(chunks) > 1
    
    def test_chunks_have_overlap(self):
        """Consecutive chunks should share overlapping content."""
        # Use identifiable text pattern
        text = "".join([f"S{i:04d}_" for i in range(1000)])  # S0000_S0001_S0002_...
        chunks = chunk_text(text, chunk_size=100, overlap=30)
        
        if len(chunks) >= 2:
            # End of chunk 0 should appear at start of chunk 1
            end_of_first = chunks[0][-30:]
            assert end_of_first in chunks[1], "Chunks should overlap"
    
    def test_empty_text_returns_empty(self):
        chunks = chunk_text("")
        assert chunks == []
    
    def test_max_chunks_cap(self):
        """Extremely long text should be capped at MAX_CHUNKS."""
        text = "A" * 100000
        chunks = chunk_text(text)
        assert len(chunks) <= 15  # MAX_CHUNKS
    
    def test_whitespace_only_chunks_skipped(self):
        """Chunks that are only whitespace should be filtered out."""
        text = "Real content here" + (" " * 3000) + "More content"
        chunks = chunk_text(text)
        for chunk in chunks:
            assert len(chunk.strip()) > 50
