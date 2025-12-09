import os
from openai import OpenAI
import chromadb
import traceback
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenRouter Client
# We use OpenRouter's API URL. The key is in env vars (OPENROUTER_API_KEY)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Initialize client lazily or with dummy key to prevent immediate crash on import if env var is missing (like in CI)
try:
    if OPENROUTER_API_KEY:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
    else:
        # Placeholder for CI/CD import tests
        client = None
except Exception as e:
    client = None
    print(f"Warning: Failed to initialize OpenAI client: {e}")

# Initialize ChromaDB (Persistent)
# Robust path handling matching ingest.py
CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "chroma_db")

if not os.path.exists(CHROMA_DB_PATH):
    pass # Chroma will create it if needed interaction happens

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = chroma_client.get_or_create_collection(name="legal_cases")

def get_llm_response(prompt: str) -> str:
    if not client:
        return "Error: OpenRouter API configuration missing (Key not found)."
    
    # Primary Model: Nvidia Nemotron
    try:
        response = client.chat.completions.create(
            model="nvidia/nemotron-nano-12b-v2-vl:free", 
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Warning: Nvidia Nemotron failed ({e}). Switching to Fallback (Gemini Flash)...")
        # Fallback Model: Gemini Flash 2.0 (Experimental/Free)
        try:
            response = client.chat.completions.create(
                model="google/gemini-2.0-flash-exp:free",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as fallback_error:
             return f"Error from AI Provider (Primary & Fallback failed): {str(fallback_error)}"

def query_legal_assistant(user_query: str):
    """
    Real RAG Construction - Hardened
    """
    context_text = ""
    cited_cases = []
    
    # 1. Retrieve (Chroma handles embedding the query string automatically)
    print(f"DEBUG: Starting retrieval for query: {user_query}")
    try:
        results = collection.query(
            query_texts=[user_query],
            n_results=3
        )
        print(f"DEBUG: Retrieval successful. Found {len(results['documents'][0])} docs.")
        
        # Parse results
        if results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i]
                title = meta.get('title', 'Unknown Case')
                context_text += f"\nCase: {title}\nContent: {doc[:1000]}...\n"
                cited_cases.append(title)
                
    except Exception as e:
        print(f"CRITICAL RETRIEVAL ERROR: {e}")
        traceback.print_exc()
        # Fallback: Don't crash, just proceed without context
        context_text = "Database retrieval temporarily unavailable. Proceeding with general legal knowledge."
    
    # Fallback if no context
    if not context_text:
        context_text = "No specific case law found in database. Answering based on general knowledge."
    
    # 2. Generate
    prompt = f"""
    You are an expert Legal AI Assistant for Indian Copyright Law.
    
    Relevant Case Law Context:
    {context_text}
    
    User Idea:
    {user_query}
    
    Task:
    Analyze the risk of copyright infringement. 
    1. Assess the risk (High/Medium/Low).
    2. Explain WHY based on the provided case law context (cite them).
    3. Suggest specific modifications (Loopholes/Transformativeness) to reduce risk.
    """
    
    analysis = get_llm_response(prompt)
    
    return {
        "analysis": analysis,
        "cited_cases": cited_cases if cited_cases else ["General Legal Principles"]
    }
