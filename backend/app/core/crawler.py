import requests
from bs4 import BeautifulSoup
import time
import logging
from app.core.scraper import fetch_case_text

logger = logging.getLogger(__name__)

def crawl_and_ingest(start_url: str, limit: int = 5):
    """
    Crawls a search result page, extracts case links, and returns their content.
    For this demo, we will simulate finding links because scraping search result pages 
    can be complex and fragile.
    
    In a real scenario, this would:
    1. requests.get(start_url)
    2. soup.find_all('a', class_='result_link')
    3. yield urls
    """
    logger.info(f"Crawling {start_url} for new cases...")
    
    # Mocking autonomy for the demo if the URL isn't a direct search page we support
    # Or we can implement a real simple extractor if the user gives a specific format.
    
    found_cases = []
    
    try:
        # Check if the start_url is already a likely case URL
        if "/doc/" in start_url:
             logger.info(f"URL {start_url} appears to be a specific document.")
             # We might fetch the title from the page content in real scraping, 
             # but here we'll just return it as a found case to be processed.
             return [{"url": start_url, "title": "Direct Link Case"}]
        
        # User-Agent helpful for not getting blocked
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(start_url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Generic link finder for kanoon - very naive
            # IndianKanoon search results usually have links like /doc/123456/
            links = soup.find_all('a', href=True)
            
            count = 0
            for link in links:
                href = link['href']
                if "/doc/" in href and count < limit:
                    full_url = f"https://indiankanoon.org{href}" if href.startswith('/') else href
                    # Avoid duplicates or non-case links if possible
                    title = link.get_text(strip=True)
                    if len(title) > 10: # filtering noise
                        found_cases.append({"url": full_url, "title": title})
                        count += 1
        
    except Exception as e:
        logger.error(f"Crawl failed: {e}")
        
    return found_cases
