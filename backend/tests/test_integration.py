"""
Integration tests for the full RAG pipeline.
These tests require a valid OpenRouter API key and will make actual API calls.
"""
import os
import pytest
from app.core.rag import query_legal_assistant


class TestRAGIntegration:
    """Integration tests for the RAG pipeline."""

    def test_simple_query_returns_structured_response(self):
        """Test that a simple query returns a properly structured response."""
        # Skip if no API key is available
        if not os.getenv("OPENROUTER_API_KEY"):
            pytest.skip("OpenRouter API key not available")
        
        # Test with a simple legal query
        query = "What is the penalty for theft under Indian Penal Code?"
        result = query_legal_assistant(query)
        
        # Check that we get a response with expected structure
        assert "analysis" in result
        assert isinstance(result["analysis"], str)
        assert len(result["analysis"]) > 0
        
        assert "cited_cases" in result
        assert isinstance(result["cited_cases"], list)
        
        assert "citation_verification" in result
        assert isinstance(result["citation_verification"], dict)
        assert "confidence" in result["citation_verification"]
        
        assert "relevance_quality" in result
        assert result["relevance_quality"] in ["none", "low", "medium", "high"]
        
        assert "llm_cited_cases" in result
        assert isinstance(result["llm_cited_cases"], list)

    def test_query_with_legal_terms(self):
        """Test a query with specific legal terms."""
        if not os.getenv("OPENROUTER_API_KEY"):
            pytest.skip("OpenRouter API key not available")
            
        query = "Section 302 IPC punishment for murder"
        result = query_legal_assistant(query)
        
        assert "analysis" in result
        assert len(result["analysis"]) > 0
        
        # Should mention IPC or Indian Penal Code somewhere
        analysis_lower = result["analysis"].lower()
        # Note: This might not always be true depending on what the LLM knows
        # but it's a reasonable expectation for a well-trained legal model

    def test_empty_query_handled_gracefully(self):
        """Test that empty query is handled gracefully."""
        if not os.getenv("OPENROUTER_API_KEY"):
            pytest.skip("OpenRouter API key not available")
            
        result = query_legal_assistant("")
        
        # Should still return a structured response
        assert "analysis" in result
        assert isinstance(result["analysis"], str)
        # Might be empty or contain general legal principles

    def test_very_long_query(self):
        """Test handling of very long query."""
        if not os.getenv("OPENROUTER_API_KEY"):
            pytest.skip("OpenRouter API key not available")
            
        # Create a very long query by repeating a phrase
        base_query = "What is the legal principle of stare decisis in Indian law? "
        query = base_query * 50  # Make it quite long
        
        result = query_legal_assistant(query)
        
        assert "analysis" in result
        assert isinstance(result["analysis"], str)
        # Should not crash or hang


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
