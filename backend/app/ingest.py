import csv
import os
import sys
import logging
import chromadb
import time

from app.core.scraper import fetch_case_text
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env vars
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    logger.warning("GOOGLE_API_KEY not found. Ingestion will fail if attempted.")
    # sys.exit(1) # Removed to allow import in CI/CD without env vars

# Ensure robust path for ChromaDB
# If running in Docker, it maps to /app/chroma_db. 
# If running locally from backend/, it maps to ./chroma_db
CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db")
if not os.path.exists(CHROMA_DB_PATH):
    os.makedirs(CHROMA_DB_PATH)

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = chroma_client.get_or_create_collection(name="legal_cases")


def process_and_store_document(text: str, metadata: dict, doc_id: str = None):
    """
    Processes a single document: chunks and stores in ChromaDB.
    ChromaDB handles embedding automatically using default local model.
    """
    try:
        # Chunking (Naive - first 9000 chars for demo safety)
        chunk = text[:9000] 
        
        # Generate ID if not provided
        if not doc_id:
            doc_id = f"doc_{int(time.time())}_{abs(hash(chunk))}"

        # Add to collection (Let Chroma embed it)
        collection.add(
            documents=[chunk],
            metadatas=[metadata],
            ids=[doc_id]
        )
        source = metadata.get('url', 'Unknown Source')
        logger.info(f"Successfully stored document: {metadata.get('title', 'Untitled')} from {source}")
        return True

    except Exception as e:
        logger.error(f"Error processing document: {e}")
        return False

def ingest_case_from_url(url: str, title: str = None) -> bool:
    """
    Fetches content from a URL and ingests it into the knowledge base.
    """
    logger.info(f"Ingesting from URL: {url}")
    
    text_content = fetch_case_text(url)
    if not text_content:
        logger.warning(f"Failed to fetch content for {url}")
        return False
    
    # If title is not provided, try to extract or use a default
    if not title:
        # Simple heuristic: first line or slice
        title = text_content.split('\n')[0][:100] if text_content else "Untitled Legal Case"
        
    metadata = {
        "title": title,
        "url": url,
        "source": "autonomous_learning",
        "ingested_at": str(time.time())
    }
    
    return process_and_store_document(text_content, metadata)

def ingest_data():
    """Reads cases.csv, scrapes text, embeds, and stores in ChromaDB."""
    
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
            
            # Check if likely already exists (naive check by ID)
            # In a real app, we might check by URL in metadata
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
            
            metadata = {
                "title": title, 
                "url": url, 
                "author": row.get('case_author', '')
            }
            
            # Use the new shared function
            # We enforce the ID to match the CSV index for backward compatibility/idempotency
            success = process_and_store_document(text_content, metadata, doc_id=str(idx))
            
            # Rate limiting for Free Tier
            if success:
                time.sleep(4)
            
            idx += 1
            
    logger.info("Ingestion Complete!")

if __name__ == "__main__":
    # Ensure we are in the backend directory or adjust paths
    ingest_data()
