import os
import google.generativeai as genai
import chromadb
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# Initialize ChromaDB (Persistent)
# Robust path handling matching ingest.py
CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "chroma_db")

if not os.path.exists(CHROMA_DB_PATH):
    # Fallback to local dir if structure implies it
    CHROMA_DB_PATH = "chroma_db"

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = chroma_client.get_or_create_collection(name="legal_cases")

def get_gemini_response(prompt: str) -> str:
    if not GOOGLE_API_KEY:
        return "Error: Gemini API Key not found."
    
    model = genai.GenerativeModel('models/gemini-2.0-flash')
    response = model.generate_content(prompt)
    return response.text

def get_query_embedding(text: str):
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_query"
        )
        return result['embedding']
    except Exception as e:
        print(f"Embedding error: {e}")
        return None

def query_legal_assistant(user_query: str):
    """
    Real RAG Construction
    """
    # 1. Embed Query
    query_emb = get_query_embedding(user_query)
    
    context_text = ""
    cited_cases = []
    
    if query_emb:
        # 2. Retrieve
        results = collection.query(
            query_embeddings=[query_emb],
            n_results=3
        )
        
        # Parse results
        if results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i]
                context_text += f"\nCase: {meta['title']}\nContent: {doc[:1000]}...\n"
                cited_cases.append(meta['title'])
    
    # Fallback if no context
    if not context_text:
        context_text = "No specific case law found in database. Answering based on general knowledge."
    
    # 3. Generate
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
    
    analysis = get_gemini_response(prompt)
    
    return {
        "analysis": analysis,
        "cited_cases": cited_cases if cited_cases else ["General Legal Principles"]
    }
