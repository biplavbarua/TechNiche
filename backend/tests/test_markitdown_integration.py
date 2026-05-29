"""
Tests for all MarkItDown integration changes.

Covers:
  - Idea 1: scraper.py  — MarkItDown HTML → cleaner text, BeautifulSoup fallback
  - Idea 3: extraction.py — extract_key_sections() priority logic, no [:20000] truncation
  - Idea 2: ingest.py   — ingest_case_from_file() with supported/unsupported extensions
  - Idea 4: ingest.py   — OCR converter selection based on file extension
  - main.py             — POST /api/learn/file endpoint (content-type validation, temp file cleanup)
  - Memory safety       — converter singletons are not re-created per call

No external API calls. Pinecone is fully mocked at sys.modules level.

Run from project root (uses .venv):
    backend/.venv/bin/python -m pytest backend/tests/test_markitdown_integration.py -v --tb=short

Or from backend/:
    .venv/bin/python -m pytest tests/test_markitdown_integration.py -v --tb=short
"""

import io
import os
import sys
import json
import tempfile
import textwrap
import tracemalloc
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Global pinecone stub — must happen BEFORE any app.* import so that
# app.utils.pinecone and app.ingest can be imported without a live Pinecone.
# ─────────────────────────────────────────────────────────────────────────────

def _make_pinecone_stub():
    """Return a minimal stub that satisfies every import app code makes."""
    stub = MagicMock()
    stub.Pinecone = MagicMock(return_value=MagicMock())
    return stub

# Inject the stub before any app module is imported.
if "pinecone" not in sys.modules:
    sys.modules["pinecone"] = _make_pinecone_stub()

# Also stub google.generativeai (imported by some utility modules).
if "google.generativeai" not in sys.modules:
    sys.modules["google"] = MagicMock()
    sys.modules["google.generativeai"] = MagicMock()

# ─────────────────────────────────────────────────────────────────────────────
# Sample fixtures
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_INDIANKANOON_HTML = b"""
<html>
<head><title>ABC Corp v State of Maharashtra</title></head>
<body>
  <nav>Home | Cases | Statutes | Login | Register | Share on Facebook</nav>
  <header>IndianKanoon Navigation Bar</header>
  <div class="judgments">
    <h2>IN THE SUPREME COURT OF INDIA</h2>
    <p>Civil Appeal No. 1234 of 2024</p>
    <h3>HELD</h3>
    <p>The appeal is allowed. The judgment of the High Court is set aside.
    The plaintiff is entitled to the relief claimed.</p>
    <h3>ORDER</h3>
    <p>Accordingly, the appeal is allowed with costs.</p>
  </div>
  <footer>Copyright IndianKanoon 2024 | Privacy Policy | Contact</footer>
  <div class="ads">Advertisement: Law Firm Services</div>
</body>
</html>
"""

LONG_JUDGMENT_MARKDOWN = textwrap.dedent("""
# Supreme Court of India — Civil Appeal No. 5678/2023

## Background

The petitioner, a company incorporated under the Companies Act, filed this appeal.

""") + ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 200) + textwrap.dedent("""

## Facts of the Case

The dispute arose from a merger agreement executed on 1 January 2010.

""") + ("Lorem ipsum dolor sit amet. " * 200) + textwrap.dedent("""

## Held

The court holds that the petitioner's submission is well-founded. The ratio decidendi
is that directors owe a fiduciary duty that cannot be contractually excluded.
The appeal is accordingly allowed.

## Order

In the result, the impugned judgment is set aside. Costs awarded. Appeal allowed.
""")

SAMPLE_CASE_TEXT = textwrap.dedent("""
# HIGH COURT OF JUDICATURE AT BOMBAY

## Case: XYZ Ltd v Revenue Authority

### Held

Tax exemption under Section 10(23C) of the Income Tax Act is granted.

### Order

Appeal allowed. Assessment order quashed.
""")


# ─────────────────────────────────────────────────────────────────────────────
# Idea 1 — scraper.py: MarkItDown cleans HTML
# ─────────────────────────────────────────────────────────────────────────────

class TestScraperMarkItDown:
    """Tests for the upgraded fetch_case_text() using MarkItDown."""

    def _mock_response(self, html_bytes: bytes):
        mock_resp = MagicMock()
        mock_resp.content = html_bytes
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    @patch("app.core.scraper.requests.get")
    def test_markitdown_strips_nav_and_footer(self, mock_get):
        """MarkItDown output must not contain navigation/footer noise."""
        mock_get.return_value = self._mock_response(SAMPLE_INDIANKANOON_HTML)
        from app.core.scraper import fetch_case_text, _get_md_converter
        if _get_md_converter() is None:
            pytest.skip("MarkItDown not installed")

        text = fetch_case_text("https://indiankanoon.org/doc/1234/")

        assert text, "fetch_case_text() returned empty string"
        assert "Copyright IndianKanoon" not in text, "Footer leaked into output"
        assert "Advertisement" not in text, "Ad text leaked into output"

    @patch("app.core.scraper.requests.get")
    def test_fallback_strips_noise_when_no_container_found(self, mock_get):
        """
        When no <div class='judgments'> container exists, the fallback path
        must still strip nav/header/footer/ads before MarkItDown conversion.
        """
        # HTML without a judgment container — only nav + content + footer
        no_container_html = b"""
        <html><body>
          <nav class="navbar">Home | Login | Register | Share on Facebook</nav>
          <header>IndianKanoon Header</header>
          <div id="content">
            <h2>Supreme Court of India</h2>
            <p>The appeal is allowed with costs. Judgment pronounced.</p>
          </div>
          <footer>Copyright IndianKanoon 2024 | Privacy Policy</footer>
          <div class="ads">Advertisement content</div>
        </body></html>
        """
        mock_get.return_value = self._mock_response(no_container_html)
        from app.core.scraper import fetch_case_text

        text = fetch_case_text("https://indiankanoon.org/doc/9999/")

        assert text, "fetch_case_text() returned empty string on fallback path"
        # Core legal content must be present
        assert "appeal is allowed" in text.lower() or "Supreme Court" in text
        # Nav/footer should be stripped
        assert "Copyright IndianKanoon" not in text, "Footer not stripped in fallback path"
        assert "Advertisement" not in text, "Ad not stripped in fallback path"


    @patch("app.core.scraper.requests.get")
    def test_markitdown_preserves_judgment_content(self, mock_get):
        """Legal content (HELD, ORDER) must survive HTML → Markdown conversion."""
        mock_get.return_value = self._mock_response(SAMPLE_INDIANKANOON_HTML)
        from app.core.scraper import fetch_case_text

        text = fetch_case_text("https://indiankanoon.org/doc/1234/")

        assert text, "fetch_case_text() returned empty string"
        assert (
            "Supreme Court" in text or "appeal is allowed" in text.lower()
        ), "Core judgment content missing from MarkItDown output"

    @patch("app.core.scraper.requests.get")
    def test_output_is_smaller_than_raw_html(self, mock_get):
        """Cleaned Markdown must be smaller than raw HTML (noise stripped)."""
        mock_get.return_value = self._mock_response(SAMPLE_INDIANKANOON_HTML)
        from app.core.scraper import fetch_case_text, _get_md_converter
        if _get_md_converter() is None:
            pytest.skip("MarkItDown not installed")

        text = fetch_case_text("https://indiankanoon.org/doc/1234/")
        assert len(text.encode()) < len(SAMPLE_INDIANKANOON_HTML), (
            "Output is not smaller than raw HTML — noise not being stripped"
        )

    @patch("app.core.scraper.requests.get")
    def test_returns_empty_string_on_fetch_error(self, mock_get):
        """Network errors must return '' not raise."""
        mock_get.side_effect = Exception("Connection refused")
        from app.core.scraper import fetch_case_text

        result = fetch_case_text("https://indiankanoon.org/doc/bad/")
        assert result == ""

    @patch("app.core.scraper._get_md_converter", return_value=None)
    @patch("app.core.scraper.requests.get")
    def test_beautifulsoup_fallback_when_markitdown_unavailable(self, mock_get, _mock_conv):
        """When MarkItDown is unavailable the BeautifulSoup path must still work."""
        mock_get.return_value = self._mock_response(SAMPLE_INDIANKANOON_HTML)
        from app.core.scraper import fetch_case_text

        text = fetch_case_text("https://indiankanoon.org/doc/1234/")
        assert "appeal is allowed" in text.lower() or "Supreme Court" in text


# ─────────────────────────────────────────────────────────────────────────────
# Idea 3 — extraction.py: extract_key_sections()
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractKeySections:
    """Tests for the new Markdown-aware section extractor."""

    def setup_method(self):
        from app.core.extraction import extract_key_sections
        self.fn = extract_key_sections

    def test_held_section_prioritised_over_background(self):
        """HELD section must appear before lorem ipsum background text."""
        result = self.fn(LONG_JUDGMENT_MARKDOWN, max_chars=3000)
        held_pos = result.lower().find("the court holds")
        bg_pos = result.lower().find("lorem ipsum")
        assert held_pos != -1, "HELD content missing from output"
        assert held_pos < bg_pos or bg_pos == -1, \
            "HELD section should appear before background filler text"

    def test_order_section_is_present_in_short_budget(self):
        """ORDER section must be reachable even with a tight budget."""
        result = self.fn(LONG_JUDGMENT_MARKDOWN, max_chars=2000)
        assert "appeal allowed" in result.lower() or "order" in result.lower()

    def test_respects_max_chars_budget(self):
        """Output must never exceed max_chars (+small margin for block boundaries)."""
        for budget in [500, 2000, 10000, 20000]:
            result = self.fn(LONG_JUDGMENT_MARKDOWN, max_chars=budget)
            assert len(result) <= budget + 10, \
                f"Output ({len(result)}) exceeded budget ({budget})"

    def test_empty_input_returns_empty_string(self):
        assert self.fn("", max_chars=20000) == ""

    def test_document_without_headings_still_returns_content(self):
        """Plain text without # headings should still return content within budget."""
        plain = "This is a plain text judgment. The appeal is allowed. " * 20
        result = self.fn(plain, max_chars=500)
        assert len(result) <= 510
        assert "appeal is allowed" in result.lower()

    def test_short_document_returned_intact(self):
        """Short docs fitting within budget must not be cut."""
        short = "# Held\n\nAppeal allowed.\n\n# Order\n\nCosts awarded."
        result = self.fn(short, max_chars=20000)
        assert "Appeal allowed" in result
        assert "Costs awarded" in result

    # ── THE KEY before/after demonstration ────────────────────────────────

    def test_smart_extraction_captures_ratio_that_old_truncation_missed(self):
        """
        BEFORE (old [:20000]):
          A 30k-char document with the HELD section at char 25,000 would have
          HELD silently dropped — the LLM never saw the binding reasoning.

        AFTER (extract_key_sections):
          The HELD section is pulled to the front of the output budget,
          so the LLM always sees the ratio decidendi.
        """
        # 25,000 chars of preamble — HELD appears well beyond the old 20k cut
        padding = "Background facts: " + ("a " * 12500)   # ~25,000 chars
        doc = (
            "# Background\n\n" + padding +
            "\n\n# Held\n\nThe ratio is: directors owe fiduciary duty. Appeal allowed."
        )

        old_output = doc[:20000]
        new_output = self.fn(doc, max_chars=20000)

        assert "fiduciary duty" not in old_output, \
            "Test setup error: HELD should be beyond the 20k char mark"
        assert "fiduciary duty" in new_output, \
            "extract_key_sections() failed to surface the HELD section"

    def test_extract_key_sections_is_called_not_raw_truncation(self):
        """
        Verify at source-code level that extract_legal_metadata() calls
        extract_key_sections() and does NOT use the old [:20000] slice.
        """
        import inspect
        import app.core.extraction as ext_module
        src = inspect.getsource(ext_module.extract_legal_metadata)
        assert "extract_key_sections" in src, \
            "extract_legal_metadata() no longer calls extract_key_sections() — regression!"
        assert "[:20000]" not in src, \
            "Old [:20000] truncation still present — was not removed!"


# ─────────────────────────────────────────────────────────────────────────────
# Idea 2 — ingest.py: ingest_case_from_file()
# ─────────────────────────────────────────────────────────────────────────────

class TestIngestCaseFromFile:
    """Tests for the new file-based ingestion path."""

    def _write_tmp(self, content: str, suffix: str = ".txt") -> str:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            return f.name

    def test_text_file_ingested_successfully(self):
        tmp = self._write_tmp(SAMPLE_CASE_TEXT, ".txt")
        try:
            with patch("app.ingest.process_and_store_document", return_value=True) as mock_psd:
                from app.ingest import ingest_case_from_file
                result = ingest_case_from_file(tmp, title="Test Case")
            assert result is True
            mock_psd.assert_called_once()
            text_arg = mock_psd.call_args[0][0]
            assert isinstance(text_arg, str)
            assert len(text_arg) > 50
        finally:
            os.unlink(tmp)

    def test_nonexistent_file_returns_false(self):
        from app.ingest import ingest_case_from_file
        result = ingest_case_from_file("/does/not/exist/judgment.pdf")
        assert result is False

    def test_empty_file_returns_false(self):
        tmp = self._write_tmp("   \n\n  ", ".txt")
        try:
            from app.ingest import ingest_case_from_file
            result = ingest_case_from_file(tmp)
            assert result is False
        finally:
            os.unlink(tmp)

    def test_metadata_includes_required_fields(self):
        content = "# Test Case\n\nJudgment content here. " * 10
        tmp = self._write_tmp(content, ".txt")
        try:
            with patch("app.ingest.process_and_store_document", return_value=True) as mock_psd:
                from app.ingest import ingest_case_from_file
                ingest_case_from_file(tmp)
            meta = mock_psd.call_args[0][1]
            assert meta["source"] == "file_upload"
            assert meta["file_type"] == "txt"
            assert meta["status"] == "active"
            assert meta["url"].startswith("file://")
        finally:
            os.unlink(tmp)

    def test_process_and_store_receives_str_not_bytes(self):
        content = "# Case ABC\n\nThe judgment is as follows. " * 10
        tmp = self._write_tmp(content, ".txt")
        try:
            with patch("app.ingest.process_and_store_document", return_value=True) as mock_psd:
                from app.ingest import ingest_case_from_file
                ingest_case_from_file(tmp)
            text_arg = mock_psd.call_args[0][0]
            assert isinstance(text_arg, str), \
                "process_and_store_document must receive str, not bytes"
        finally:
            os.unlink(tmp)


# ─────────────────────────────────────────────────────────────────────────────
# Idea 4 — ingest.py: OCR converter selection
# ─────────────────────────────────────────────────────────────────────────────

class TestConverterSelection:
    """Tests that OCR vs plain converter selection is correct."""

    def test_pdf_in_ocr_extensions(self):
        from app.ingest import _OCR_EXTENSIONS
        assert ".pdf" in _OCR_EXTENSIONS

    def test_docx_in_ocr_extensions(self):
        from app.ingest import _OCR_EXTENSIONS
        assert ".docx" in _OCR_EXTENSIONS

    def test_pptx_in_ocr_extensions(self):
        from app.ingest import _OCR_EXTENSIONS
        assert ".pptx" in _OCR_EXTENSIONS

    def test_txt_not_in_ocr_extensions(self):
        from app.ingest import _OCR_EXTENSIONS
        assert ".txt" not in _OCR_EXTENSIONS

    def test_html_not_in_ocr_extensions(self):
        from app.ingest import _OCR_EXTENSIONS
        assert ".html" not in _OCR_EXTENSIONS

    def test_ocr_converter_falls_back_without_api_key(self):
        """Without OPENROUTER_API_KEY OCR converter must not crash."""
        import app.ingest as ingest_module
        ingest_module._md_ocr = None  # Force re-init

        saved = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            converter = ingest_module._get_ocr_converter()
        finally:
            if saved:
                os.environ["OPENROUTER_API_KEY"] = saved

        # Must either return None or a MarkItDown instance — never raise
        from markitdown import MarkItDown
        assert converter is None or isinstance(converter, MarkItDown)

    def test_plain_converter_is_singleton(self):
        """_get_plain_converter() must return the same instance every call."""
        import app.ingest as ingest_module
        ingest_module._md_plain = None

        c1 = ingest_module._get_plain_converter()
        c2 = ingest_module._get_plain_converter()
        assert c1 is c2, "Plain converter is not a singleton — memory leak risk"


# ─────────────────────────────────────────────────────────────────────────────
# main.py — POST /api/learn/file endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestLearnFileEndpoint:
    """Tests for the new /api/learn/file FastAPI endpoint."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        with patch("app.main.get_pinecone_index") as mock_idx:
            mock_idx.return_value = MagicMock()
            mock_idx.return_value.describe_index_stats.return_value = {"total_vector_count": 0}
            from fastapi.testclient import TestClient
            from app.main import app
            self.client = TestClient(app, raise_server_exceptions=False)

    def _upload(self, content: bytes, filename: str, content_type: str):
        return self.client.post(
            "/api/learn/file",
            files={"file": (filename, io.BytesIO(content), content_type)},
        )

    @patch("app.main.ingest_case_from_file", return_value=True)
    def test_pdf_upload_returns_200(self, _):
        resp = self._upload(b"%PDF-1.4 sample", "judgment.pdf", "application/pdf")
        assert resp.status_code == 200
        assert resp.json()["file_name"] == "judgment.pdf"

    @patch("app.main.ingest_case_from_file", return_value=True)
    def test_docx_upload_returns_200(self, _):
        resp = self._upload(
            b"PK docx content", "case.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert resp.status_code == 200

    def test_unsupported_mime_returns_415(self):
        resp = self._upload(b"\x4d\x5a", "malware.exe", "application/octet-stream")
        assert resp.status_code == 415
        assert "Unsupported file type" in resp.json()["detail"]

    @patch("app.main.ingest_case_from_file", return_value=False)
    def test_failed_ingestion_returns_422(self, _):
        resp = self._upload(b"content", "empty.pdf", "application/pdf")
        assert resp.status_code == 422

    @patch("app.main.ingest_case_from_file", return_value=True)
    def test_txt_upload_accepted(self, _):
        resp = self._upload(b"Case text here", "case.txt", "text/plain")
        assert resp.status_code == 200

    @patch("app.main.ingest_case_from_file", return_value=True)
    def test_jpeg_image_accepted(self, _):
        """Scanned judgment images (JPEG) must be accepted."""
        resp = self._upload(b"\xff\xd8\xff\xe0 jpeg", "scan.jpg", "image/jpeg")
        assert resp.status_code == 200

    @patch("app.main.ingest_case_from_file", return_value=True)
    def test_zip_archive_accepted(self, _):
        """ZIP archives (batch case file folders) must be accepted."""
        resp = self._upload(b"PK zip data", "cases.zip", "application/zip")
        assert resp.status_code == 200

    def test_temp_file_cleaned_up_after_request(self):
        """Temp file must be deleted from disk after the request completes."""
        captured_paths: list[str] = []

        def capture_and_succeed(path, title=None):
            captured_paths.append(path)
            return True

        with patch("app.main.ingest_case_from_file", side_effect=capture_and_succeed):
            self._upload(b"sample content", "test.pdf", "application/pdf")

        for tmp_path in captured_paths:
            assert not Path(tmp_path).exists(), \
                f"Temp file not cleaned up: {tmp_path}"


# ─────────────────────────────────────────────────────────────────────────────
# Memory safety
# ─────────────────────────────────────────────────────────────────────────────

class TestMemorySafety:
    """Ensures the integration does not leak memory under repeated use."""

    def test_extract_key_sections_no_memory_accumulation(self):
        """
        100 calls to extract_key_sections() on a large doc must not cause
        unbounded allocation (no per-call list accumulation).
        """
        from app.core.extraction import extract_key_sections
        doc = LONG_JUDGMENT_MARKDOWN * 3

        tracemalloc.start()
        snap1 = tracemalloc.take_snapshot()

        for _ in range(100):
            extract_key_sections(doc, max_chars=20000)

        snap2 = tracemalloc.take_snapshot()
        tracemalloc.stop()

        new_bytes = sum(
            s.size_diff for s in snap2.compare_to(snap1, "lineno") if s.size_diff > 0
        )
        assert new_bytes < 10 * 1024 * 1024, \
            f"extract_key_sections() allocated {new_bytes / 1024:.1f} KB across 100 calls"

    def test_scraper_converter_is_singleton(self):
        """_get_md_converter() must always return the same object."""
        import app.core.scraper as scraper_module
        scraper_module._md_converter = None

        c1 = scraper_module._get_md_converter()
        c2 = scraper_module._get_md_converter()
        assert c1 is c2, "_get_md_converter() is not a singleton"

    def test_chunk_text_caps_output_regardless_of_input_size(self):
        """
        chunk_text() must never return more than MAX_CHUNKS chunks even for
        a 1,000,000-char judgment — prevents OOM on very long documents.
        """
        from app.ingest import chunk_text, MAX_CHUNKS
        huge_doc = "word " * 200_000   # ~1 million characters

        chunks = chunk_text(huge_doc)

        assert len(chunks) <= MAX_CHUNKS, \
            f"chunk_text() produced {len(chunks)} chunks — exceeds MAX_CHUNKS={MAX_CHUNKS}"

    def test_ingest_from_file_uses_path_not_in_memory_bytes(self):
        """
        ingest_case_from_file() must accept a file path (disk), not buffer the
        entire file content in memory as a bytes argument.
        """
        import inspect
        from app.ingest import ingest_case_from_file
        sig = inspect.signature(ingest_case_from_file)
        assert "file_path" in sig.parameters, \
            "ingest_case_from_file() must take file_path (disk path), not in-memory bytes"
