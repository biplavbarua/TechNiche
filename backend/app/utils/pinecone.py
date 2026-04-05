from pinecone import Pinecone
import os
from dotenv import load_dotenv

load_dotenv()

# Global Pinecone client instance
_pc = None

def get_pinecone_client():
    """Get or initialize the Pinecone client instance."""
    global _pc
    if _pc is None:
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable is not set")
        _pc = Pinecone(api_key=api_key)
    return _pc

def get_pinecone_index():
    """Get the Pinecone index using the centralized client."""
    pc = get_pinecone_client()
    index_name = os.getenv("PINECONE_INDEX_NAME")
    if not index_name:
        # Fallback to a default if not set, though it should be in .env
        index_name = "techniche-legal-index"
    return pc.Index(index_name)
