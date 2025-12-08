import requests
from bs4 import BeautifulSoup
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_case_text(url: str) -> str:
    """
    Fetches the text content of a legal case from IndianKanoon or similar.
    """
    try:
        # Respectful scraping: User-Agent and minor delay
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }
        time.sleep(1) # Rate limiting
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # IndianKanoon specific extraction
        # The main judgment text is often in a div with class "judgments" or "doc_content"
        main_content = soup.find('div', class_='judgments')
        if not main_content:
             main_content = soup.find('div', class_='doc_content')
             
        if main_content:
            content = main_content.get_text(separator='\n', strip=True)
        else:
            # Fallback to getting all text if specific container not found
            content = soup.get_text(separator='\n', strip=True)
        
        # Basic cleaning (removing excessive newlines)
        cleaned_content = '\n'.join([line for line in content.split('\n') if line.strip()])
        
        return cleaned_content
    
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return ""
