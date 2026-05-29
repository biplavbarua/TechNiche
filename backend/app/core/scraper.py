import io
import time
import logging
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── MarkItDown converter (lazy init so import errors don't crash the whole app) ──
_md_converter = None

def _get_md_converter():
    """Lazy-init a shared MarkItDown instance (thread-safe for read-only use)."""
    global _md_converter
    if _md_converter is None:
        try:
            from markitdown import MarkItDown
            _md_converter = MarkItDown()
            logger.info("MarkItDown converter initialised for scraper.")
        except ImportError:
            logger.warning(
                "markitdown not installed. Falling back to raw text extraction. "
                "Run: pip install 'markitdown[html]'"
            )
    return _md_converter


def _extract_judgment_html(response_content: bytes) -> bytes:
    """
    Scopes the raw HTML to the main judgment content before MarkItDown
    conversion, stripping site chrome (nav bars, ads, footers, scripts).

    Strategy:
      1. Try a priority list of judgment-specific containers.
      2. If none found, surgically remove all known noise elements from the
         full-page soup before handing the pruned HTML to MarkItDown.

    This ensures MarkItDown always receives clean, scoped HTML regardless of
    whether the target page uses a known container class.
    """
    soup = BeautifulSoup(response_content, "html.parser")

    # Priority list of judgment content containers used across Indian legal portals
    container = (
        soup.find("div", class_="judgments")
        or soup.find("div", class_="doc_content")
        or soup.find("div", class_="judgment-text")
        or soup.find("div", id="doc_content")
        or soup.find("div", id="judgment")
        or soup.find("article")
        or soup.find("main")
        or soup.find("div", id="content")
    )

    if container:
        return str(container).encode()

    # ── Fallback: strip all noise from the full page, then hand to MarkItDown ──
    # Remove structural noise tags outright
    for tag in soup.find_all(["nav", "header", "footer", "aside", "script", "style", "noscript"]):
        tag.decompose()

    # Remove elements with noise-indicating CSS classes or IDs
    _NOISE_TOKENS = {
        "nav", "navigation", "navbar", "sidebar", "side-bar",
        "ad", "ads", "advert", "advertisement",
        "share", "social", "cookie", "banner",
        "menu", "header", "footer", "breadcrumb", "pagination",
    }
    for el in soup.find_all(True):
        classes = " ".join(el.get("class", [])).lower()
        el_id   = (el.get("id") or "").lower()
        if any(tok in classes or tok in el_id for tok in _NOISE_TOKENS):
            el.decompose()

    return str(soup).encode()



def fetch_case_text(url: str) -> str:
    """
    Fetches the text content of a legal case from IndianKanoon or similar.

    Strategy:
      1. Check if the URL is an IndianKanoon doc and IK_API_TOKEN is present.
         If so, fetch via the official IK API to bypass 403 blocks.
      2. Otherwise, download the page HTML normally.
      3. Scope to the judgment container (strips nav/ads/footer).
      4. Convert the scoped HTML to clean Markdown via MarkItDown.
    """
    import os
    import re
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.114 Safari/537.36"
            )
        }
        
        scoped_html = None
        
        # Step 1: Check for IndianKanoon URL and API Token
        ik_token = os.environ.get("IK_API_TOKEN", "").strip()
        ik_match = re.search(r"indiankanoon\.org/doc/([0-9]+)/?", url)
        
        if ik_match and ik_token:
            docid = ik_match.group(1)
            api_url = f"https://api.indiankanoon.org/doc/{docid}/"
            logger.info(f"Using official IndianKanoon API for docid: {docid}")
            api_headers = {
                "Authorization": f"Token {ik_token}",
                "Accept": "application/json"
            }
            try:
                # IK API requires POST
                api_resp = requests.post(api_url, headers=api_headers, timeout=10)
                api_resp.raise_for_status()
                data = api_resp.json()
                if "doc" in data:
                    # Enriched HTML from API
                    scoped_html = data["doc"].encode("utf-8")
                else:
                    logger.warning("IK API response did not contain 'doc'. Falling back.")
            except Exception as e:
                logger.warning(f"IK API failed ({e}). Falling back to web scraper.")
        
        # Step 2: Fallback to web scraping if API wasn't used or failed
        if not scoped_html:
            time.sleep(1)  # Respectful rate-limiting
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            scoped_html = _extract_judgment_html(response.content)

        converter = _get_md_converter()

        if converter is not None:
            # Step 3: Convert scoped HTML to clean Markdown
            result = converter.convert_stream(
                io.BytesIO(scoped_html),
                file_extension=".html",
                url=url,
            )
            text = result.text_content or ""
        else:
            # Fallback: plain text extraction from the scoped HTML
            soup = BeautifulSoup(scoped_html, "html.parser")
            text = soup.get_text(separator="\\n", strip=True)

        cleaned = "\\n".join(line for line in text.splitlines() if line.strip())
        if not cleaned:
            logger.warning(f"Conversion produced empty text for: {url}")
        return cleaned

    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return ""
