import os
import time
import logging
from app.core.crawler import crawl_and_ingest
from app.ingest import ingest_case_from_url

# Configure Logging to show progress clearly
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [TRAINING BOT] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Target Sources for Wide "Training"
# These start URLs act as seeds. The crawler will find case links within them.
SEED_URLS = [
    "https://indiankanoon.org/search/?formInput=copyright+infringement+doctrines+sort:mostrecent",
    "https://indiankanoon.org/search/?formInput=trademark+passing+off+cases+sort:mostrecent",
    "https://indiankanoon.org/search/?formInput=fair+use+doctrine+india+cases",
    "https://indiankanoon.org/search/?formInput=media+law+defamation+cases+india",
    "https://indiankanoon.org/search/?formInput=intellectual+property+rights+startups"
]

def run_training_bot():
    """
    The Training Bot.
    It iterates through seed topics, finds new cases, and ingests them into the Vector Database.
    """
    logger.info("Initializing Legal AI Training Bot...")
    logger.info("Targeting Indian Copyright & IP Law Corpus...")
    
    total_new_cases = 0
    
    for seed in SEED_URLS:
        logger.info(f"\n--- Scouting topic: {seed} ---")
        
        # 1. Crawl for potential cases (Limit increased to 20 per topic for broader coverage)
        # Note: crawl_and_ingest returns a list of dicts {url, title}
        potential_cases = crawl_and_ingest(seed, limit=15)
        
        if not potential_cases:
            logger.warning("No cases found for this topic. Moving to next.")
            continue
            
        logger.info(f"Found {len(potential_cases)} potential cases to learn.")
        
        # 2. Ingest each case
        for i, case in enumerate(potential_cases, 1):
            url = case['url']
            title = case['title']
            
            logger.info(f"[{i}/{len(potential_cases)}] Learning: {title}...")
            
            try:
                success = ingest_case_from_url(url, title=title)
                
                if success:
                    logger.info(f"✅ Learned: {title}")
                    total_new_cases += 1
                else:
                    logger.warning(f"❌ Failed to learn: {title}")
                
                # Politeness delay to be a good bot
                time.sleep(2) 
                
            except Exception as e:
                logger.error(f"Error learning {url}: {e}")
                
    logger.info("\n" + "="*50)
    logger.info(f"TRAINING SESSION COMPLETE.")
    logger.info(f"Total new legal precedents ingested: {total_new_cases}")
    logger.info("Your AI is now smarter!")
    logger.info("="*50)

if __name__ == "__main__":
    run_training_bot()
