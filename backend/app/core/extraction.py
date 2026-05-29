import os
import re
import json
import logging
from datetime import date, datetime
from typing import Optional
from openai import OpenAI
from pydantic import BaseModel, Field, model_validator
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configure OpenRouter client
api_key = os.getenv("OPENROUTER_API_KEY")
client = None
if api_key:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

# Reliable free models for extraction (mirrors rag.py cascade)
EXTRACTION_MODELS = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "minimax/minimax-m2.5:free",
    "stepfun/step-3.5-flash:free",
    "arcee-ai/trinity-large-preview:free",
    "liquid/lfm-2.5-1.2b-thinking:free",
    "liquid/lfm-2.5-1.2b-instruct:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "arcee-ai/trinity-mini:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "qwen/qwen3-next-80b-a3b-instruct:free"
]


class CaseMetadata(BaseModel):
    """Structured legal metadata extracted from court judgments.
    
    This model is the schema-validation layer between raw LLM output
    and our database. Every field that enters ChromaDB passes through here.
    """
    case_name: str = Field(description="The official name of the legal case.")
    judgment_date: str = Field(description="The date of the judgment in YYYY-MM-DD format. If unknown, output 'UNKNOWN'.")
    overrules_cases: list[str] = Field(default_factory=list, description="A list of case names that this judgment explicitly overrules. Empty list if none.")
    upholds_cases: list[str] = Field(default_factory=list, description="A list of case names that this judgment explicitly upholds. Empty list if none.")
    legal_domain: str = Field(default="General", description="The primary area of Indian law discussed (e.g., Intellectual Property, Corporate, Tax).")
    validated_date: Optional[date] = Field(default=None, description="Parsed date object for temporal comparison. None if date is UNKNOWN or unparseable.")

    @model_validator(mode="after")
    def compute_validated_date(self) -> "CaseMetadata":
        """Parse judgment_date into a real date after all fields are set."""
        raw_date = self.judgment_date
        if raw_date and raw_date != "UNKNOWN":
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    self.validated_date = datetime.strptime(raw_date, fmt).date()
                    return self
                except ValueError:
                    continue
        self.validated_date = None
        return self


# ─── Markdown-aware section extraction ─────────────────────────────────────

# Regex patterns for sections that contain binding legal reasoning.
# These are prioritised over procedural or background sections.
_PRIORITY_SECTION_PATTERNS = [
    r"^#+\s*(held|ratio|order|judgment|decision|conclusion|finding|per curiam)",
    r"^#+\s*(it is hereby|the court holds|we hold|accordingly|in the result)",
    r"^#+\s*(operative part|final order|disposition|decree)",
]


def extract_key_sections(markdown_text: str, max_chars: int = 20_000) -> str:
    """
    Intelligently extracts the most legally relevant sections from a
    Markdown-formatted judgment, prioritising binding reasoning over
    procedural/background content.

    This replaces the naive ``text[:20000]`` truncation that silently
    discards the *ratio decidendi* in long Supreme Court judgments.

    Strategy:
      1. Split document on Markdown headings (lines starting with ``#``).
      2. Mark blocks whose heading matches a priority pattern (HELD, ORDER, …).
      3. Fill the output budget with: priority blocks first, then others.
    """
    if not markdown_text:
        return ""

    lines = markdown_text.splitlines()
    priority_blocks: list[str] = []
    other_blocks: list[str] = []
    current_lines: list[str] = []
    is_priority: bool = False

    for line in lines:
        if line.startswith("#"):  # New section heading
            if current_lines:
                block = "\n".join(current_lines)
                (priority_blocks if is_priority else other_blocks).append(block)
            current_lines = [line]
            is_priority = any(
                re.search(p, line, re.IGNORECASE)
                for p in _PRIORITY_SECTION_PATTERNS
            )
        else:
            current_lines.append(line)

    # Flush the last block
    if current_lines:
        block = "\n".join(current_lines)
        (priority_blocks if is_priority else other_blocks).append(block)

    # Build output: priority sections first, fill remainder with others
    result_parts: list[str] = []
    chars_used = 0

    for block in priority_blocks + other_blocks:
        if chars_used + len(block) <= max_chars:
            result_parts.append(block)
            chars_used += len(block)
        else:
            # Append a partial block to fill the remaining budget
            remaining = max_chars - chars_used
            if remaining > 200:  # Only worth including if >200 chars remain
                result_parts.append(block[:remaining])
            break

    return "\n\n".join(result_parts)


# ─── LLM-based metadata extraction ──────────────────────────────────────────

def extract_legal_metadata(raw_scraped_text: str) -> dict:
    """
    Passes raw scraped legal text to the AI to extract structured metadata 
    for the Temporal Conflict-Resolution algorithm.
    
    Returns a validated dictionary matching CaseMetadata schema,
    or an empty dict if extraction fails.
    """
    if not client:
        logger.warning("OPENROUTER_API_KEY not set. Skipping AI extraction layer.")
        return {}

    system_prompt = (
        "You are an expert Indian Legal AI. Analyze the scraped court judgment. "
        "Extract the metadata strictly adhering to the following JSON schema: "
        '{"case_name": "string", "judgment_date": "string (YYYY-MM-DD or UNKNOWN)", '
        '"overrules_cases": ["string"], "upholds_cases": ["string"], "legal_domain": "string"}. '
        "You MUST output raw JSON formatting adhering to this schema. "
        "For overrules_cases, list ONLY cases that are EXPLICITLY overruled, struck down, or reversed. "
        "Do NOT include cases that are merely discussed or distinguished."
    )
    
    # Use Markdown-aware section extraction instead of naive char truncation.
    # Priority sections (HELD, ORDER, RATIO) are pulled first so the LLM sees
    # the binding legal reasoning even in very long judgments.
    key_text = extract_key_sections(raw_scraped_text, max_chars=20_000)
    user_prompt = f"Court Judgment (Markdown, key sections prioritised):\n{key_text}"
    
    last_error = None
    for model_name in EXTRACTION_MODELS:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content
            raw_data = json.loads(response_text)
            
            # CRITICAL: Validate through Pydantic — this catches malformed keys,
            # wrong types, and missing fields instead of silently corrupting the DB.
            validated = CaseMetadata(**raw_data)
            
            result = validated.model_dump()
            logger.info(f"Extraction successful via {model_name}: {result.get('case_name', 'Unknown')}")
            return result
            
        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(f"Model {model_name} returned invalid JSON: {e}. Trying next...")
            continue
        except Exception as e:
            last_error = e
            logger.warning(f"Model {model_name} failed extraction: {e}. Trying next...")
            continue
    
    logger.error(f"All extraction models failed. Last error: {last_error}")
    return {}
