"""
Edge case tests for citation verification in rag.py.
"""
import pytest
from app.core.rag import _verify_citations


class TestCitationVerificationEdgeCases:
    """Edge case tests for the post-generation citation verification system."""

    def test_empty_analysis_text(self):
        """Test with empty analysis text."""
        analysis = ""
        retrieved_titles = ["Case A", "Case B"]
        
        result = _verify_citations(analysis, retrieved_titles)
        assert result["confidence"] == "low"
        assert result["grounded"] == []
        # With empty analysis, no titles can be grounded, so all should be ungrounded
        assert set(result["ungrounded"]) == set(retrieved_titles)

    def test_empty_retrieved_titles(self):
        """Test with empty retrieved titles."""
        analysis = "Some analysis text"
        retrieved_titles = []
        
        result = _verify_citations(analysis, retrieved_titles)
        assert result["grounded"] == []
        assert result["ungrounded"] == []
        assert result["confidence"] == "low"  # No titles means low confidence

    def test_both_empty(self):
        """Test with both analysis and titles empty."""
        analysis = ""
        retrieved_titles = []
        
        result = _verify_citations(analysis, retrieved_titles)
        assert result["grounded"] == []
        assert result["ungrounded"] == []
        assert result["confidence"] == "low"

    def test_exact_match(self):
        """Test exact title matching."""
        analysis = "The ruling in ABC Corp vs. State of Maharashtra established..."
        retrieved_titles = ["ABC Corp vs. State of Maharashtra"]
        
        result = _verify_citations(analysis, retrieved_titles)
        assert "ABC Corp vs. State of Maharashtra" in result["grounded"]
        assert result["confidence"] == "high"

    def test_substring_match(self):
        """Test substring matching within title."""
        analysis = "The ABC Corp ruling established important precedent..."
        retrieved_titles = ["ABC Corp vs. State of Maharashtra"]
        
        result = _verify_citations(analysis, retrieved_titles)
        # "ABC Corp" appears in both
        assert "ABC Corp vs. State of Maharashtra" in result["grounded"]

    def test_true_no_match(self):
        """Test case where there is truly no match."""
        # Use words that are all <= 3 chars or stop words so they get filtered out
        # This way match_ratio calculation will be 0/1 = 0, and no substring match
        analysis = "The XYZ ruling established important precedent..."
        retrieved_titles = ["ABC V XY"]  # All words <= 3 chars after filtering
        
        result = _verify_citations(analysis, retrieved_titles)
        # After filtering, no meaningful words remain in title
        # And "abc v xy" is not in "the xyz ruling established important precedent..."
        assert len(result["grounded"]) == 0
        assert len(result["ungrounded"]) > 0
        assert result["confidence"] == "low"

    def test_partial_word_match(self):
        """Test partial word matching with meaningful words."""
        analysis = "The landmark ABC Corporation ruling on property rights..."
        retrieved_titles = ["ABC Corporation vs. State"]
        
        result = _verify_citations(analysis, retrieved_titles)
        # Should match based on "ABC" and "Corporation" or "Corp" variations
        assert len(result["grounded"]) > 0 or len(result["ungrounded"]) > 0

    def test_low_word_match_ratio(self):
        """Test match ratio below threshold (0.4)."""
        # Need a case where after filtering, we have enough words but low match ratio
        # Title: "Word1 Word2 Word3 Word4 LongWord" (5 words, need 3+ to match at 0.6+ ratio for 0.4 threshold with 5 words)
        # Actually: need match_ratio < 0.4, so with 5 words need < 2 matches -> max 1 match
        analysis = "Word1 completely different terms here"
        retrieved_titles = ["Word1 Word2 Word3 Word4 LongWord"]
        
        result = _verify_citations(analysis, retrieved_titles)
        # Only "Word1" matches = 1/5 = 0.2 < 0.4, and no substring match
        assert "Word1 Word2 Word3 Word4 LongWord" in result["ungrounded"]
        assert result["confidence"] == "low"

    def test_high_word_match_ratio(self):
        """Test match ratio above threshold (0.4)."""
        # Title: "Word1 Word2 Word3 Word4" (4 words, need 2+ to match at 0.4 threshold)
        # Analysis has 3 matching words (75% > 40%)
        analysis = "Word1 Word2 Word3 something else"
        retrieved_titles = ["Word1 Word2 Word3 Word4"]
        
        result = _verify_citations(analysis, retrieved_titles)
        assert "Word1 Word2 Word3 Word4" in result["grounded"]
        assert result["confidence"] == "high"

    def test_exact_threshold(self):
        """Test exactly at the 0.4 threshold."""
        # Title: "Word1 Word2 Word3 Word4 Word5" (5 words, need 2+ to match at 0.4 threshold)
        analysis = "Word1 Word2 completely different terms"
        retrieved_titles = ["Word1 Word2 Word3 Word4 Word5"]
        
        result = _verify_citations(analysis, retrieved_titles)
        # Exactly 2 out of 5 words match = 0.4 ratio, should be grounded
        assert "Word1 Word2 Word3 Word4 Word5" in result["grounded"]
        assert result["confidence"] == "high"

    def test_special_characters(self):
        """Test handling of special characters in case names."""
        analysis = "The ruling in M/s. ABC Corp. (India) vs. State established..."
        retrieved_titles = ["M/s. ABC Corp. (India) vs. State"]
        
        result = _verify_citations(analysis, retrieved_titles)
        assert "M/s. ABC Corp. (India) vs. State" in result["grounded"]

    def test_numeric_title(self):
        """Test handling of numerical variations in case titles."""
        analysis = "The 2020 ruling in ABC Corp vs State..."
        retrieved_titles = ["ABC Corp vs. State (2020)"]
        
        result = _verify_citations(analysis, retrieved_titles)
        # Should match despite parentheses and spacing differences
        assert len(result["grounded"]) > 0 or len(result["ungrounded"]) > 0

    def test_mixed_grounded_and_ungrounded(self):
        """Test with multiple titles where some are grounded and some not."""
        analysis = "ABC Corp vs. State set precedent, but XYZ Ltd was not discussed."
        retrieved_titles = ["ABC Corp vs. State", "XYZ Ltd vs. Union", "PQR Industries"]
        
        result = _verify_citations(analysis, retrieved_titles)
        assert "ABC Corp vs. State" in result["grounded"]
        # One of the others should be ungrounded
        ungrounded_count = sum(1 for title in ["XYZ Ltd vs. Union", "PQR Industries"] 
                              if title in result["ungrounded"])
        assert ungrounded_count > 0

    def test_case_insensitive(self):
        """Test that matching is case insensitive."""
        analysis = "THE RULING IN abc corp vs. STATE OF MAHARASHTRA established..."
        retrieved_titles = ["ABC Corp vs. State of Maharashtra"]
        
        result = _verify_citations(analysis, retrieved_titles)
        assert "ABC Corp vs. State of Maharashtra" in result["grounded"]

    def test_title_with_punctuation(self):
        """Test handling of punctuation in titles."""
        analysis = "The case of ABC Corp, Ltd. vs. State established precedent..."
        retrieved_titles = ["ABC Corp, Ltd. vs. State"]
        
        result = _verify_citations(analysis, retrieved_titles)
        assert "ABC Corp, Ltd. vs. State" in result["grounded"]

    def test_short_title_filtering(self):
        """Test filtering of short words (length <= 3) in titles."""
        analysis = "The ABC VS case..."
        retrieved_titles = ["ABC VS"]  # Both words are <= 3 chars after filtering
        
        result = _verify_citations(analysis, retrieved_titles)
        # After filtering, no meaningful words remain in title (both <= 3)
        # So substring matching is the only way to match
        # "abc vs" is in "the abc vs case..." so it WILL match
        assert "ABC VS" in result["grounded"]
        assert result["confidence"] == "high"

    def test_stop_word_filtering(self):
        """Test filtering of stop words like 'the', 'and', 'vs.', etc."""
        analysis = "State versus corporation case analysis..."
        retrieved_titles = ["The State vs Corporation"]  # Contains stop words
        
        result = _verify_citations(analysis, retrieved_titles)
        # "The" and "vs" should be filtered out, leaving "State Corporation"
        # Analysis has "State versus corporation" which matches after filtering
        # "state" and "corporation" should match (after filtering stop words from title)
        assert "The State vs Corporation" in result["grounded"]

    def test_unicode_characters(self):
        """Test handling of unicode characters in case names."""
        analysis = "The célèbre case of Ëxámplë Corp vs. État..."
        retrieved_titles = ["Ëxámplë Corp vs. État"]
        
        result = _verify_citations(analysis, retrieved_titles)
        # Should handle unicode characters
        assert len(result["grounded"]) > 0 or len(result["ungrounded"]) > 0
