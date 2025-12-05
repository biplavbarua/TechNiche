import sys
import os

# Add current dir to path to import app
sys.path.append(os.getcwd())

from app.core.rag import query_legal_assistant

def test():
    query = "I want to make a funny parody of a famous song for a commercial add."
    print(f"Query: {query}")
    try:
        result = query_legal_assistant(query)
        print("\n--- Analysis ---")
        print(result['analysis'])
        print("\n--- Cited Cases ---")
        print(result['cited_cases'])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
