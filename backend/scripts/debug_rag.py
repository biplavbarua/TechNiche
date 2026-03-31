import sys
import os

# Ensure backend dir is in path
sys.path.append(os.getcwd())

from app.core.rag import query_legal_assistant

print("Testing query_legal_assistant...")
try:
    result = query_legal_assistant("I want to make a movie about a wizard.")
    print("SUCCESS Result:", result)
except Exception as e:
    print("CRASHED:")
    import traceback
    traceback.print_exc()
