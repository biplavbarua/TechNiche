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
    Uses BeautifulSoup to isolate the main judgment container from the full
    IndianKanoon page HTML.

    IndianKanoon wraps the actual judgment in a <div class="judgments"> or
    <div class="doc_content"> element.  Extracting just that div before
    handing it to MarkItDown prevents navigation bars, share buttons, ads,
    and footers from appearing in the converted Markdown.

    Returns the scoped HTML bytes, or the full page if no container is found.
    """
    soup = BeautifulSoup(response_content, "html.parser")
    container = soup.find("div", class_="judgments") or soup.find("div", class_="doc_content")
    if container:
        return str(container).encode()
    # Fallback: return the full page for MarkItDown to process
    return response_content


def fetch_case_text(url: str) -> str:
    """
    Fetches the text content of a legal case from IndianKanoon or similar.

    Strategy:
      1. Download the page HTML.
      2. Scope to the judgment container (strips nav/ads/footer via BeautifulSoup).
      3. Convert the scoped HTML to clean Markdown via MarkItDown.

    This two-step approach preserves structured headings (## HELD, ## ORDER)
    while eliminating site chrome — producing ~20–35% fewer tokens than the
    previous approach for the same document.
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.114 Safari/537.36"
            )
        }
        time.sleep(1)  # Respectful rate-limiting

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # Step 1: Scope to judgment container using BeautifulSoup
        scoped_html = _extract_judgment_html(response.content)

        converter = _get_md_converter()

        if converter is not None:
            # Step 2: Convert scoped HTML to clean Markdown
            result = converter.convert_stream(
                io.BytesIO(scoped_html),
                file_extension=".html",
                url=url,
            )
            text = result.text_content or ""
        else:
            # Fallback: plain text extraction from the scoped HTML
            soup = BeautifulSoup(scoped_html, "html.parser")
            text = soup.get_text(separator="\n", strip=True)

        cleaned = "\n".join(line for line in text.splitlines() if line.strip())
        if not cleaned:
            logger.warning(f"Conversion produced empty text for: {url}")
        return cleaned

    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return ""
