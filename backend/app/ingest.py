import csv
import os
import sys
import logging
import chromadb
import time
import google.generativeai as genai
from app.core.scraper import fetch_case_text
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env vars
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    logger.error("GOOGLE_API_KEY not found. Please check .env file.")
    sys.exit(1)

genai.configure(api_key=GOOGLE_API_KEY)

def get_embedding(text: str):
    """Generates embedding using Gemini."""
    try:
        # Gemini text-embedding-004 is current standard
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document",
            title="Legal Case"
        )
        return result['embedding']
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None

def ingest_data():
    """Reads cases.csv, scrapes text, embeds, and stores in ChromaDB."""
    
    # Initialize Chroma (Persistent)
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection = chroma_client.get_or_create_collection(name="legal_cases")
    
    csv_path = "../legacy/cases.csv" # Relative to backend/ directory assuming run from backend/
    
    if not os.path.exists(csv_path):
        # Fallback absolute path check
        csv_path = "/Users/biplavbarua/Developer/TechNiche/legacy/cases.csv"
        
    if not os.path.exists(csv_path):
        logger.error(f"CSV file not found at {csv_path}")
        return

    logger.info(f"Reading cases from {csv_path}...")
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        idx = 0
        for row in reader:
            url = row['case_url']
            title = row['case_title']
            
            # Check if likely already exists (naive check)
            existing = collection.get(ids=[str(idx)])
            if existing['ids']:
                logger.info(f"Skipping {title} (Already indexed)")
                idx += 1
                continue

            logger.info(f"Processing: {title}")
            
            # Scrape
            text_content = fetch_case_text(url)
            if not text_content:
                logger.warning(f"Failed to fetch content for {url}")
                continue
                
            # Chunking (Naive - first 8000 chars for demo, real implementations need smart chunking)
            # Gemini has input limits for embeddings, usually 2048 or something.
            # let's take a safe chunk.
            chunk = text_content[:9000] 
            
            # Embed
            embedding = get_embedding(chunk)
            
            # Rate limiting for Free Tier
            time.sleep(4)
            
            if embedding:
                collection.add(
                    documents=[chunk],
                    metadatas=[{"title": title, "url": url, "author": row.get('case_author', '')}],
                    ids=[str(idx)],
                    embeddings=[embedding]
                )
                logger.info(f"Indexed: {title}")
            
            idx += 1
            
    logger.info("Ingestion Complete!")

if __name__ == "__main__":
    # Ensure we are in the backend directory or adjust paths
    ingest_data()
