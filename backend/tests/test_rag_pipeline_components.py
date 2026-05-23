"""
Tests for RAG pipeline components in app/core/rag.py.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.core.rag import (
    _assess_relevance,
    _filter_diversity,
    _detect_legal_domain,
    _extract_llm_cited_cases,
    _verify_citations,
    query_legal_assistant,
    get_llm_response,
    MODELS
)


class TestAssessRelevance:
    """Tests for the _assess_relevance function."""

    def test_empty_hits_returns_false(self):
        """Test that empty hits returns False."""
        search_results = {"matches": []}
        assert _assess_relevance("test query", search_results) is False

    def test_low_max_score_returns_false(self):
        """Test that very low max score returns False."""
        search_results = {
            "matches": [
                {"_score": 0.1},  # Very low score
                {"_score": 0.2}
            ]
        }
        assert _assess_relevance("test query", search_results) is False

    def test_high_max_score_passes_to_llm_check(self):
        """Test that high enough score passes to LLM check."""
        search_results = {
            "matches": [
                {"_score": 0.8},  # High score
                {"_score": 0.7}
            ]
        }
        # With high scores, it should go to LLM check
        # We'll mock the LLM response to control the outcome
        with patch('app.core.rag.get_llm_response') as mock_llm:
            mock_llm.return_value = "YES"
            result = _assess_relevance("test query", search_results)
            assert result is True
            mock_llm.assert_called_once()

    def test_llm_returns_no_returns_false(self):
        """Test that LLM returning NO results in False."""
        search_results = {
            "matches": [
                {"_score": 0.8},
                {"_score": 0.7}
            ]
        }
        with patch('app.core.rag.get_llm_response') as mock_llm:
            mock_llm.return_value = "NO"
            result = _assess_relevance("test query", search_results)
            assert result is False

    def test_llm_error_fallback_to_score_heuristic(self):
        """Test that LLM errors fall back to score heuristic."""
        search_results = {
            "matches": [
                {"_score": 0.4},  # Above 0.35 threshold
                {"_score": 0.3}
            ]
        }
        with patch('app.core.rag.get_llm_response') as mock_llm:
            mock_llm.side_effect = Exception("LLM error")
            result = _assess_relevance("test query", search_results)
            # Should fall back to score heuristic: max_score > 0.35 -> True
            assert result is True

    def test_llm_error_fallback_low_score(self):
        """Test that LLM errors with low scores fall back to False."""
        search_results = {
            "matches": [
                {"_score": 0.3},  # Below 0.35 threshold
                {"_score": 0.2}
            ]
        }
        with patch('app.core.rag.get_llm_response') as mock_llm:
            mock_llm.side_effect = Exception("LLM error")
            result = _assess_relevance("test query", search_results)
            # Should fall back to score heuristic: max_score > 0.35 -> False
            assert result is False


class TestFilterDiversity:
    """Tests for the _filter_diversity function."""

    def test_empty_hits_returns_empty_list(self):
        """Test that empty hits returns empty list."""
        assert _filter_diversity([]) == []

    def test_single_hit_returns_same(self):
        """Test that single hit returns same hit."""
        hits = [{"metadata": {"title": "Case A"}}]
        result = _filter_diversity(hits)
        assert result == hits

    def test_max_per_case_limit_respected(self):
        """Test that max_per_case limit is respected."""
        # Create hits from same case
        hits = [
            {"metadata": {"title": "Same Case"}},
            {"metadata": {"title": "Same Case"}},
            {"metadata": {"title": "Same Case"}},
            {"metadata": {"title": "Same Case"}},
            {"metadata": {"title": "Different Case"}}
        ]
        result = _filter_diversity(hits, max_per_case=2, min_cases=1)
        # Should only take 2 from Same Case (max_per_case) and 1 from Different Case
        # But since we have min_cases=1, we stop when we have enough diversity
        # Actually, the algorithm continues until we have 10 total or run out of hits
        # Let's check the logic more carefully
        same_case_count = sum(1 for hit in result if hit["metadata"]["title"] == "Same Case")
        diff_case_count = sum(1 for hit in result if hit["metadata"]["title"] == "Different Case")
        assert same_case_count <= 2  # max_per_case
        assert diff_case_count >= 1  # at least one different case

    def test_min_cases_respected(self):
        """Test that min_cases is respected."""
        # Create hits from multiple cases
        hits = [
            {"metadata": {"title": "Case A"}},
            {"metadata": {"title": "Case A"}},
            {"metadata": {"title": "Case B"}},
            {"metadata": {"title": "Case B"}},
            {"metadata": {"title": "Case C"}}
        ]
        result = _filter_diversity(hits, max_per_case=2, min_cases=3)
        # Should have at least 3 different cases
        unique_titles = set(hit["metadata"]["title"] for hit in result)
        assert len(unique_titles) >= 3

    def test_stops_at_10_total(self):
        """Test that function stops at 10 total hits."""
        # Create more than 10 hits from various cases
        hits = []
        for i in range(15):
            hits.append({"metadata": {"title": f"Case {i % 5}"}})  # 5 different cases
        
        result = _filter_diversity(hits, max_per_case=3, min_cases=2)
        assert len(result) <= 10  # Should not exceed 10

    def test_preserves_order(self):
        """Test that original order is preserved."""
        hits = [
            {"metadata": {"title": "Case C"}, "score": 0.1},
            {"metadata": {"title": "Case A"}, "score": 0.5},
            {"metadata": {"title": "Case B"}, "score": 0.3}
        ]
        result = _filter_diversity(hits)
        # Should preserve the order of first occurrence of each case
        # Case C (0), Case A (1), Case B (2)
        titles = [hit["metadata"]["title"] for hit in result]
        # Find first occurrence of each
        first_case_c = titles.index("Case C") if "Case C" in titles else -1
        first_case_a = titles.index("Case A") if "Case A" in titles else -1
        first_case_b = titles.index("Case B") if "Case B" in titles else -1
        # They should appear in order C, A, B (0, 1, 2)
        assert first_case_c < first_case_a < first_case_b


class TestDetectLegalDomain:
    """Tests for the _detect_legal_domain function."""

    def test_empty_hits_returns_indian_law(self):
        """Test that empty hits returns Indian Law."""
        assert _detect_legal_domain([]) == "Indian Law"

    def test_no_legal_domain_returns_indian_law(self):
        """Test that hits with no legal_domain returns Indian Law."""
        hits = [
            {"metadata": {"title": "Case A"}},
            {"metadata": {"title": "Case B"}}
        ]
        assert _detect_legal_domain(hits) == "Indian Law"

    def test_general_and_unknown_ignored(self):
        """Test that General and UNKNOWN domains are ignored."""
        hits = [
            {"metadata": {"title": "Case A", "ai_legal_domain": "General"}},
            {"metadata": {"title": "Case B", "ai_legal_domain": "UNKNOWN"}},
            {"metadata": {"title": "Case C", "ai_legal_domain": "Corporate Law"}}
        ]
        assert _detect_legal_domain(hits) == "Corporate Law"

    def test_returns_most_frequent_domain(self):
        """Test that the most frequent domain is returned."""
        hits = [
            {"metadata": {"title": "Case A", "ai_legal_domain": "Tax Law"}},
            {"metadata": {"title": "Case B", "ai_legal_domain": "Tax Law"}},
            {"metadata": {"title": "Case C", "ai_legal_domain": "Tax Law"}},
            {"metadata": {"title": "Case D", "ai_legal_domain": "Corporate Law"}},
            {"metadata": {"title": "Case E", "ai_legal_domain": "Corporate Law"}}
        ]
        assert _detect_legal_domain(hits) == "Tax Law"

    def test_handles_metadata_variations(self):
        """Test handling of different metadata structures."""
        # Test with direct metadata (not nested)
        hits = [
            {"title": "Case A", "ai_legal_domain": "IP Law"},
            {"title": "Case B", "ai_legal_domain": "IP Law"},
            {"title": "Case C", "ai_legal_domain": "Tax Law"}
        ]
        # This tests the hasattr(hit, "metadata") branch
        class MockHit:
            def __init__(self, metadata):
                self.metadata = metadata
        
        mock_hits = [MockHit(h) for h in hits]
        assert _detect_legal_domain(mock_hits) == "IP Law"


class TestExtractLLMCitedCases:
    """Tests for the _extract_llm_cited_cases function."""

    def test_empty_analysis_returns_empty_list(self):
        """Test that empty analysis returns empty list."""
        assert _extract_llm_cited_cases("") == []

    def test_no_citations_returns_empty_list(self):
        """Test that analysis with no citations returns empty list."""
        analysis = "This is just plain text with no case citations."
        assert _extract_llm_cited_cases(analysis) == []

    def test_basic_v_pattern(self):
        """Test basic 'v.' pattern matching (requires bold formatting)."""
        analysis = "As seen in **ABC Corp v. XYZ Ltd (2020)**, the court held..."
        result = _extract_llm_cited_cases(analysis)
        assert "ABC Corp v. XYZ Ltd (2020)" in result

    def test_vs_pattern(self):
        """Test 'vs' pattern matching (requires bold formatting)."""
        analysis = "The ruling in **ABC Corp vs. State (2021)** established..."
        result = _extract_llm_cited_cases(analysis)
        assert "ABC Corp vs. State (2021)" in result

    def test_v_pattern_without_period(self):
        """Test 'v' pattern without period (requires bold formatting)."""
        analysis = "Refer to **ABC Corp v State (2022)** for details."
        result = _extract_llm_cited_cases(analysis)
        assert "ABC Corp v State (2022)" in result

    def test_pattern_with_comma_before_year(self):
        """Test pattern with comma before year (requires bold formatting)."""
        analysis = "The case of **ABC Corp vs. State, 2020** was landmark."
        result = _extract_llm_cited_cases(analysis)
        assert "ABC Corp vs. State, 2020" in result

    def test_multiple_citations(self):
        """Test extraction of multiple citations."""
        analysis = "First, see **ABC Corp v. XYZ (2020)**. Second, **DEF Ltd vs. State (2021)**."
        result = _extract_llm_cited_cases(analysis)
        assert "ABC Corp v. XYZ (2020)" in result
        assert "DEF Ltd vs. State (2021)" in result

    def test_deduplication_preserves_order(self):
        """Test that deduplication preserves order of first occurrence."""
        analysis = "**ABC Corp v. XYZ (2020)** and later **ABC Corp v. XYZ (2020)** again."
        result = _extract_llm_cited_cases(analysis)
        assert result == ["ABC Corp v. XYZ (2020)"]
        assert len(result) == 1

    def test_no_false_positives_on_similar_text(self):
        """Test that similar but non-matching text doesn't produce false positives."""
        analysis = "This text mentions v and vs but not in case context: v vs v."
        result = _extract_llm_cited_cases(analysis)
        assert result == []

    def test_handles_special_characters_in_names(self):
        """Test handling of special characters in case names."""
        analysis = "See **M/s. ABC Corp. (India) vs. State (2020)** for precedent."
        result = _extract_llm_cited_cases(analysis)
        assert "M/s. ABC Corp. (India) vs. State (2020)" in result


class TestQueryLegalAssistantIntegration:
    """Integration tests for the query_legal_assistant function."""

    @patch("app.core.rag.index")
    @patch("app.core.rag.get_pinecone_client")
    @patch("app.core.rag.get_llm_response")
    def test_no_relevant_context_uses_general_prompt(self, mock_llm, mock_get_pc, mock_index):
        """Test that irrelevant context triggers general prompt."""
        mock_pc = MagicMock()
        
        # Mock embeddings
        mock_embedding = MagicMock()
        mock_embedding.values = [0.1, 0.2, 0.3]
        mock_pc.inference.embed.return_value = [mock_embedding]
        mock_get_pc.return_value = mock_pc
        
        # Mock search results with low relevance
        mock_search_result = MagicMock()
        mock_search_result.matches = []  # No hits
        mock_index.query.return_value = mock_search_result
        
        mock_llm.return_value = "General legal analysis"
        
        result = query_legal_assistant("What is the meaning of life?")
        
        assert result["analysis"] == "General legal analysis"
        assert result["relevance_quality"] == "none"
        assert result["cited_cases"] == ["General Legal Principles"]
        assert result["citation_verification"]["confidence"] == "general"
        mock_llm.assert_called_once()

    @patch("app.core.rag.index")
    @patch("app.core.rag.get_pinecone_client")
    @patch("app.core.rag.get_llm_response")
    def test_relevant_context_uses_grounded_prompt(self, mock_llm, mock_get_pc, mock_index):
        """Test that relevant context triggers grounded prompt."""
        mock_pc = MagicMock()
        
        # Mock embeddings
        mock_embedding = MagicMock()
        mock_embedding.values = [0.1, 0.2, 0.3]
        mock_pc.inference.embed.return_value = [mock_embedding]
        mock_get_pc.return_value = mock_pc

        mock_hit = {
            "score": 0.8,
            "metadata": {
                "title": "Test Case vs. State",
                "text": "This is the case text",
                "url": "https://example.com/case"
            }
        }
        
        # Convert dictionary to object with properties so getattr works
        mock_hit_obj = MagicMock()
        mock_hit_obj.score = 0.8
        mock_hit_obj.metadata = {
            "title": "Test Case vs. State",
            "text": "This is the case text",
            "url": "https://example.com/case"
        }
        
        mock_search_result = MagicMock()
        mock_search_result.matches = [mock_hit_obj]
        mock_index.query.return_value = mock_search_result
        
        # Mock relevance assessment to return True
        with patch('app.core.rag._assess_relevance', return_value=True):
            mock_llm.return_value = "Grounded legal analysis with **Test Case vs. State**"
            
            result = query_legal_assistant("Tell me about test case")
            
            assert result["analysis"] == "Grounded legal analysis with **Test Case vs. State**"
            assert result["relevance_quality"] == "high"
            assert "Test Case vs. State" in result["cited_cases"]
            assert result["citation_verification"]["confidence"] == "high"
            assert len(result["llm_cited_cases"]) == 0  # No general case citations

    @patch("app.core.rag.index")
    @patch("app.core.rag.get_pinecone_client")
    @patch("app.core.rag.get_llm_response")
    def test_extracts_llm_cited_cases_from_knowledge(self, mock_llm, mock_get_pc, mock_index):
        """Test that LLM-cited cases from general knowledge are extracted."""
        mock_pc = MagicMock()
        
        # Mock embeddings
        mock_embedding = MagicMock()
        mock_embedding.values = [0.1, 0.2, 0.3]
        mock_pc.inference.embed.return_value = [mock_embedding]
        mock_get_pc.return_value = mock_pc
        
        # Mock search results but make them irrelevant
        mock_search_result = MagicMock()
        mock_search_result.matches = []
        mock_index.query.return_value = mock_search_result
        
        # Mock relevance assessment to return False (irrelevant)
        with patch('app.core.rag._assess_relevance', return_value=False):
            mock_llm.return_value = "According to **Kesavananda Bharati v. State of Kerala (1973)**, basic structure doctrine applies."
            
            result = query_legal_assistant("What is basic structure doctrine?")
            
            assert "Kesavananda Bharati v. State of Kerala (1973)" in result["llm_cited_cases"]
            assert result["relevance_quality"] == "none"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
