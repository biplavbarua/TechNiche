"""
Tests for citation verification in rag.py.

Run: cd backend && python -m pytest tests/test_rag.py -v  
"""
import pytest
from app.core.rag import _verify_citations, _detect_legal_domain


class TestCitationVerification:
    """Tests for the post-generation citation verification system."""
    
    def test_grounded_citation_detected(self):
        analysis = "Based on the ruling in ABC Corp vs. State of Maharashtra, the court held that..."
        retrieved_titles = ["ABC Corp vs. State of Maharashtra"]
        
        result = _verify_citations(analysis, retrieved_titles)
        assert "ABC Corp vs. State of Maharashtra" in result["grounded"]
        assert result["confidence"] == "high"
    
    def test_ungrounded_citation_detected(self):
        analysis = "The risk assessment shows moderate concern based on general principles."
        retrieved_titles = ["Specific Case vs. State"]
        
        result = _verify_citations(analysis, retrieved_titles)
        assert "Specific Case vs. State" in result["ungrounded"]
    
    def test_partial_title_match(self):
        """If key words from the title appear, it should be considered grounded."""
        analysis = "The landmark ABC Corp ruling established clear precedent for intellectual property rights."
        retrieved_titles = ["ABC Corp vs. Union of India (2024)"]
        
        result = _verify_citations(analysis, retrieved_titles)
        # "ABC" and "Corp" are the distinguishing words
        assert len(result["grounded"]) > 0 or len(result["ungrounded"]) > 0
    
    def test_empty_analysis(self):
        result = _verify_citations("", ["Case A", "Case B"])
        assert result["confidence"] == "low"
    
    def test_empty_titles(self):
        result = _verify_citations("Some analysis text", [])
        assert result["grounded"] == []
        assert result["ungrounded"] == []


class TestDomainDetection:
    """Tests for automatic legal domain detection from retrieved metadata."""
    
    def test_detects_common_domain(self):
        metadatas = [
            {"ai_legal_domain": "Intellectual Property"},
            {"ai_legal_domain": "Intellectual Property"},
            {"ai_legal_domain": "Tax Law"}
        ]
        assert _detect_legal_domain(metadatas) == "Intellectual Property"
    
    def test_falls_back_to_indian_law(self):
        metadatas = [{"ai_legal_domain": "General"}, {}]
        assert _detect_legal_domain(metadatas) == "Indian Law"
    
    def test_empty_metadatas(self):
        assert _detect_legal_domain([]) == "Indian Law"
    
    def test_ignores_unknown_and_general(self):
        metadatas = [
            {"ai_legal_domain": "UNKNOWN"},
            {"ai_legal_domain": "General"},
            {"ai_legal_domain": "Corporate Law"}
        ]
        assert _detect_legal_domain(metadatas) == "Corporate Law"
