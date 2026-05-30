import os
import re
import difflib
import traceback
from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

# ─── OpenRouter Client ───────────────────────────────────────────────────────

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

try:
    if OPENROUTER_API_KEY:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
    else:
        client = None
except Exception as e:
    client = None
    print(f"Warning: Failed to initialize OpenAI client: {e}")

# ─── Pinecone Client ─────────────────────────────────────────────────────────

from app.utils.pinecone import get_pinecone_client, get_pinecone_index

# Constants
EMBED_MODEL = "llama-text-embed-v2"
TOP_K = 50 # Increased for better recall
SIMILARITY_THRESHOLD = 0.5  # Ignore anything below 50% match

# Initializing Pinecone index
# Initializing Pinecone index
try:
    index = get_pinecone_index()
except Exception as e:
    print(f"Warning: Failed to initialize Pinecone index: {e}")
    index = None


# ─── LLM Models (Free models fallback cascade) ───────────────────────────────

MODELS = [
    "deepseek/deepseek-v4-flash:free",        # flagship — 1M ctx, best reasoning
    "meta-llama/llama-3.3-70b-instruct:free", # 131K ctx, excellent instruction following
    "google/gemma-4-31b-it:free",             # 262K ctx, strong legal reasoning
    "nvidia/nemotron-3-super-120b-a12b:free", # 1M ctx, large model
    "liquid/lfm-2.5-1.2b-instruct:free",      # confirmed working fallback
]


def get_llm_response(prompt: str) -> str:
    if not client:
        return "Error: OpenRouter API configuration missing (Key not found)."
    
    last_error = None
    for model_name in MODELS:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                timeout=12.0  # 12s/model → worst-case cascade 60s; DeepSeek typically 3-8s
            )
            return response.choices[0].message.content
        except Exception as e:
            last_error = e
            print(f"Warning: Model {model_name} failed ({e}). Trying next fallback...")
            continue
            
    return f"Error from AI Provider (All models failed). Last error: {str(last_error)}"


def _assess_relevance(query: str, search_results: dict) -> bool:
    """
    Assesses if the search results contain information relevant to the query.

    Previously used an LLM for a 'nuanced check' but that added a full model
    round-trip (up to 60s in the worst-case cascade) to every query.

    Replaced with a pure score-based heuristic:
    - score >= 0.45  → clearly relevant (Pinecone cosine similarity is high)
    - score 0.25-0.45 → borderline: relevant if 2+ chunks agree (same case URL)
    - score < 0.25   → not relevant

    This is fast (microseconds), deterministic, and empirically reliable for
    legal case queries where Pinecone's llama-text-embed-v2 model is well-calibrated.
    """
    hits = search_results.get("matches", [])
    if not hits:
        return False

    top_hits = hits[:5]
    scores = [hit.get("score", hit.get("_score", 0)) for hit in top_hits]
    max_score = max(scores) if scores else 0

    # Clearly relevant: high cosine similarity
    if max_score >= 0.45:
        return True

    # Completely irrelevant: score too low for any match
    if max_score < 0.25:
        return False

    # Borderline: check if multiple chunks from the same case all agree
    # (reduces false positives where one chunk accidentally scores OK)
    urls = [
        (hit.get("fields") or hit.get("metadata") or {}).get("url", "")
        for hit in top_hits
        if (hit.get("score", hit.get("_score", 0))) >= 0.30
    ]
    unique_urls = set(u for u in urls if u)
    # If 2+ chunks from the same case are above 0.30, treat as relevant
    url_counts = {u: urls.count(u) for u in unique_urls}
    if any(count >= 2 for count in url_counts.values()):
        return True

    return False

def _filter_diversity(hits: list, max_per_case: int = 2, min_cases: int = 3) -> list:
    """
    Filters hits to maintain diversity, preventing a single case from dominating the results.
    - max_per_case: Max chunks to take from a single case.
    - min_cases: Try to include at least this many distinct cases if available.
    """
    selected = []
    seen_cases = {} # case_title -> count

    for hit in hits:
        # Pinecone returns metadata in 'fields' for serverless, or 'metadata' for pod
        meta = hit.get("fields", {}) or hit.get("metadata", {})
        title = meta.get("title", "Unknown Case").strip()
        
        # Count for this specific case
        current_count = seen_cases.get(title, 0)
        
        # If we already have enough from this case AND we have reached our min_cases threshold, skip
        if current_count >= max_per_case and len(seen_cases) >= min_cases:
            continue
        
        selected.append(hit)
        seen_cases[title] = current_count + 1
        
        # Stop if we have enough total context
        if len(selected) >= 10:
            break
            
    return selected


def _detect_legal_domain(hits: list) -> str:
    """
    Looks at the top 3 hits and extracts the legal domain from metadata.
    Returns 'Indian Law' as fallback.
    """
    if not hits:
        return "Indian Law"
        
    domains = []
    for hit in hits[:3]:
        # Pinecone metadata format can vary slightly based on serverless vs pod
        # Safely access metadata or fields
        meta = {}
        if isinstance(hit, dict):
            meta = hit.get("metadata") or hit.get("fields", {})
        elif hasattr(hit, "metadata"):
            meta = hit.metadata
            
        if meta and isinstance(meta, dict):
            domain = meta.get("legal_domain") or meta.get("ai_legal_domain")
            if domain and domain.lower() not in {"general", "unknown"}:
                domains.append(domain)
            
    if not domains:
        return "Indian Law"
        
    # Return the most frequent domain
    from collections import Counter
    return Counter(domains).most_common(1)[0][0]


def _extract_llm_cited_cases(analysis_text: str) -> list[str]:
    """
    Extract case names that the LLM cited in its generated text.
    
    When in general analysis mode, the LLM cites landmark cases from its
    own knowledge (e.g. **R.G. Anand v. Deluxe Films (1978)**). We extract
    these so the frontend can display them in the Precedent Database sidebar.
    
    Patterns matched:
    - **Name v. Name (Year)**
    - **Name vs. Name (Year)**
    - **Name v. Name, Year**
    """
    # Match bold case citations: **Anything v/vs/v. Anything (Year)**
    pattern = r'\*\*([^*]+?\s+v\.?s?\.?\s+[^*]+?\(\d{4}\))\*\*'
    matches = re.findall(pattern, analysis_text)
    
    # Also match pattern without year in parens but with year after comma
    pattern2 = r'\*\*([^*]+?\s+v\.?s?\.?\s+[^*]+?,\s*\d{4})\*\*'
    matches2 = re.findall(pattern2, analysis_text)
    
    # Deduplicate while preserving order
    seen = set()
    result = []
    for m in matches + matches2:
        clean = m.strip()
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
    
    return result


# Legal stopwords excluded from word-bag matching (appear in almost every case name)
_LEGAL_STOPWORDS = {
    "the", "and", "vs", "vs.", "v.", "v", "state", "union",
    "india", "of", "in", "re", "ors", "anr", "another"
}


def _verify_citations(analysis_text: str, retrieved_titles: list[str]) -> dict:
    """
    Post-generation citation verification — FIX 5: uses difflib.SequenceMatcher
    in addition to word-bag matching to catch partial/abbreviated case name matches.

    A title is 'grounded' if:
      - It appears verbatim (case-insensitive) in the analysis, OR
      - >= 65% of its significant words appear AND the overall sequence
        similarity of title vs. any 120-char window of the analysis is >= 0.55.

    Anything else is flagged as 'ungrounded' — the LLM may have hallucinated it.
    """
    analysis_lower = analysis_text.lower()

    grounded = []   # Retrieved AND referenced in the response
    ungrounded = [] # Retrieved but NOT referenced — possible hallucination

    for title in retrieved_titles:
        title_lower = title.lower()

        # Fast path: verbatim substring match
        if title_lower in analysis_lower:
            grounded.append(title)
            continue

        # Significant-word filter (strip stopwords and short tokens)
        sig_words = [
            w for w in title_lower.split()
            if len(w) > 3 and w not in _LEGAL_STOPWORDS
        ]

        if not sig_words:
            # Degenerate title — can't verify, mark ungrounded to be safe
            ungrounded.append(title)
            continue

        word_hits = sum(1 for w in sig_words if w in analysis_lower)
        word_ratio = word_hits / len(sig_words)

        # SequenceMatcher check: slide a window across the first 6000 chars
        # to catch abbreviated/reordered citations (e.g. "Vishaka case" for
        # "Vishaka v. State of Rajasthan") even when word_ratio is low.
        seq_matched = False
        window = len(title_lower) + 20
        for i in range(0, min(len(analysis_lower), 6000) - window + 1, 15):
            ratio = difflib.SequenceMatcher(
                None, title_lower, analysis_lower[i:i + window]
            ).ratio()
            if ratio >= 0.55:
                seq_matched = True
                break

        # 0.4 word-ratio threshold preserves the original detection contract;
        # SequenceMatcher picks up additional abbreviation/reorder matches.
        if word_ratio >= 0.4 or seq_matched:
            grounded.append(title)
        else:
            ungrounded.append(title)

    return {
        "grounded": grounded,
        "ungrounded": ungrounded,
        "confidence": "high" if grounded else "low",
    }


def query_legal_assistant(user_query: str):
    """
    RAG Pipeline with Pinecone Integrated Embeddings + Multi-Gate Relevance.
    
    1. Send the user's raw text query to Pinecone for integrated search.
    2. Run 3-gate relevance assessment (absolute floor, score gap, LLM check).
    3. If relevant context found, generate case-law-grounded analysis.
    4. If context is IRRELEVANT, generate general legal analysis WITHOUT
       forcing citations to unrelated cases — and signal the frontend.
    """
    context_text = ""
    cited_cases = []
    cited_cases_details = []
    search_results = None
    has_relevant_context = False
    
    # ── 1. Retrieve from Pinecone using Integrated Embeddings ──
    print(f"\n{'='*60}")
    print(f"DEBUG: Starting Pinecone search for query: {user_query}")
    print(f"{'='*60}")
    try:
        pc = get_pinecone_client()
        embeddings = pc.inference.embed(
            model=EMBED_MODEL,
            inputs=[user_query],
            parameters={"input_type": "query"}
        )
        query_vector = embeddings[0].values

        search_results = index.query(
            namespace="",
            vector=query_vector,
            top_k=TOP_K,
            include_metadata=True,
            filter={"status": {"$eq": "active"}}
        )
        
        hits = []
        print(f"DEBUG: Pinecone search returned {len(search_results.matches)} raw hits.")
        for hit in search_results.matches:
            score = getattr(hit, "score", 0)
            meta = getattr(hit, "metadata", {})
            if not isinstance(meta, dict):
                meta = dict(meta) if meta else {}
                
            hit_dict = {
                "_score": score,
                "fields": meta,
                "metadata": meta
            }
            
            title = meta.get("title", "Unknown")
            print(f"  HIT: score={score:.4f}  title={title}")
            hits.append(hit_dict)
        
        # ── 2. Multi-gate relevance assessment ──
        is_relevant = _assess_relevance(user_query, {"matches": hits})
        print(f"DEBUG RELEVANCE DECISION: is_relevant={is_relevant}")
        
        if is_relevant and hits: # If LLM says relevant, proceed with filtering
            has_relevant_context = True
            
            # Apply Diversity Filtering
            selected_docs_raw = _filter_diversity(hits)

            # Format context for LLM
            context_text = ""
            for doc_hit in selected_docs_raw:
                # Pinecone returns metadata in 'fields' for serverless, or 'metadata' for pod
                meta = doc_hit.get("fields", {}) or doc_hit.get("metadata", {})
                title = meta.get("title", "Unknown Case")
                text = meta.get("text", "")
                score = doc_hit.get("_score", 0)

                clean_title = title.strip()

                domain = meta.get('ai_legal_domain', '')
                judgment_date = meta.get('ai_judgment_date', '')
                date_info = f" (Decided: {judgment_date})" if judgment_date and judgment_date != "UNKNOWN" else ""
                domain_info = f" [{domain}]" if domain and domain != "General" else ""
                
                context_text += f"\nCase: {title}{date_info}{domain_info} [Relevance: {score:.2f}]\nContent: {text[:1500]}...\n"
                
                if clean_title and clean_title not in ('Unknown Case', 'UNKNOWN', 'Full Document') and not clean_title.startswith('['):
                    if clean_title not in cited_cases:
                        cited_cases.append(clean_title)
                        snippet = text.strip()
                        if len(snippet) > 400:
                            snippet = snippet[:400] + "..."
                        cited_cases_details.append({
                            "title": clean_title,
                            "url": meta.get('url', ''),
                            "snippet": snippet
                        })
                
    except Exception as e:
        print(f"CRITICAL RETRIEVAL ERROR: {e}")
        traceback.print_exc()
        context_text = ""
    
    # ── 3. Detect domain from relevant hits only ──
    detected_domain = "Indian Law"
    try:
        if has_relevant_context and search_results and hasattr(search_results, 'result') and search_results.result.hits:
            detected_domain = _detect_legal_domain(search_results.result.hits)
    except Exception:
        pass
    
    # ── 4. Generate with the right prompt based on relevance ──
    if has_relevant_context and context_text:
        prompt = _build_grounded_prompt(user_query, context_text, detected_domain)
        relevance_quality = "high"
        print(f"DEBUG: Using GROUNDED prompt with {len(cited_cases)} cited cases.")
    else:
        prompt = _build_general_prompt(user_query)
        relevance_quality = "none"
        print(f"DEBUG: Using GENERAL prompt (no relevant context).")
    
    analysis = get_llm_response(prompt)

    # ── 5. Citation verification (only when we have context) ──
    citation_check = _verify_citations(analysis, cited_cases) if cited_cases else {
        "grounded": [],
        "ungrounded": [],
        "confidence": "general"
    }

    # ── 5b. FIX 2: Deterministic Citation Correction Pass ──────────────────────
    # If the LLM cited cases that were NOT in the retrieved documents, run a
    # targeted correction prompt to strip the hallucinated references.
    # This makes citation bounding *enforceable*, not just diagnostic.
    if citation_check.get("ungrounded") and has_relevant_context:
        ungrounded_list = "\n".join(
            f"  - {c}" for c in citation_check["ungrounded"]
        )
        correction_prompt = f"""The following legal analysis contains citations to cases that were NOT \
found in the retrieved evidence base and may be hallucinated:

UNVERIFIED CITATIONS TO REMOVE:
{ungrounded_list}

Rewrite the analysis below, removing any references to the above unverified cases. \
Replace them with the directly retrieved cases already cited, or with specific statutory \
principles (e.g. Section X of Act Y). Preserve all section headings, risk levels, \
recommendations, and all other verified content exactly.

ORIGINAL ANALYSIS:
{analysis}"""
        corrected = get_llm_response(correction_prompt)
        if corrected and not corrected.startswith("Error"):
            analysis = corrected
            # Re-verify after correction to update grounded/ungrounded counts
            citation_check = _verify_citations(analysis, cited_cases)
            citation_check["correction_applied"] = True
            print(
                f"DEBUG: Citation correction pass applied. "
                f"Removed hallucinated references: {citation_check.get('ungrounded', [])}"
            )

    # ── 6. Extract case names cited by LLM in its text ──
    # This captures landmark cases the LLM references from its own knowledge
    # (especially important in general analysis mode where cited_cases is empty)
    llm_cited = _extract_llm_cited_cases(analysis)
    
    print(f"DEBUG: Response generated. relevance_quality={relevance_quality}, "
          f"cited_cases={cited_cases}, llm_cited={llm_cited}")
    print(f"{'='*60}\n")
    
    return {
        "analysis": analysis,
        "cited_cases": cited_cases if cited_cases else ["General Legal Principles"],
        "cited_cases_details": cited_cases_details,
        "citation_verification": citation_check,
        "relevance_quality": relevance_quality,
        "llm_cited_cases": llm_cited,
    }


def _build_grounded_prompt(user_query: str, context_text: str, detected_domain: str) -> str:
    """
    Prompt used when the retrieval step found genuinely relevant cases.
    Instructs the LLM to cite them — but only the ones that are actually applicable.
    """
    return f"""You are an expert Legal AI Assistant specializing in {detected_domain} under Indian jurisdiction.

Relevant Case Law Context (from verified legal database):
{context_text}

User Query:
{user_query}

INSTRUCTIONS:
Structure your response using these markdown sections. Write concisely — be dense with information, not verbose.

## Risk Assessment

State the risk level as **High**, **Medium**, or **Low** in bold, then give a concise 2-3 sentence explanation of the overall legal risk.

## Detailed Analysis

Analyse the legal issues as flowing prose. For each relevant case from the context:
- Bold the case name (e.g. **Smith v. Jones (2021)**)
- Explain its relevance in 2-3 sentences inline
- Cite specific statutes and sections (e.g. Section 52(1)(a) of the Copyright Act, 1957)

Cite only the cases from the context that are genuinely relevant to the user's query. If a case in the context is not relevant, DO NOT cite it just to pad the answer.

Use paragraphs, bullet points, and numbered lists. Group related issues under ### subheadings when it improves clarity.

## Legal Loopholes & Exceptions

Identify any potential loopholes, exceptions, or alternative legal interpretations based on the context provided. Explain how they might apply.

## Recommendations

Numbered, actionable strategies to mitigate risk:
1. First recommendation with specific legal basis
2. Second recommendation
3. Third recommendation (and so on)

FORMATTING RULES:
- NEVER use markdown tables (pipes |). Use structured prose, bullet points, and subheadings instead.
- ONLY cite cases that appear in the context above AND are genuinely relevant — do NOT fabricate case names.
- If a case from the context is unrelated to the user's question, simply ignore it.
- Use ## for sections, ### for subsections, **bold** for case names and risk levels.
- Keep your response concise and information-dense. Avoid filler sentences.
"""


def _build_general_prompt(user_query: str) -> str:
    """
    Prompt used when no relevant case law was found in the database.
    Instructs the LLM to answer with general legal knowledge transparently.
    """
    return f"""You are an expert Legal AI Assistant specializing in Indian Law.

User Query:
{user_query}

IMPORTANT CONTEXT:
Our legal precedent database was searched but did NOT contain case law directly relevant to this specific query. You must answer based on your general legal knowledge of Indian law.

INSTRUCTIONS:
Structure your response using these markdown sections. Write concisely — be dense with information, not verbose.

## Risk Assessment

State the risk level as **High**, **Medium**, or **Low** in bold, then give a concise 2-3 sentence explanation of the overall legal risk.

## Detailed Analysis

Analyse the legal issues as flowing prose using your general knowledge of Indian law.
- Cite specific statutes and sections (e.g. Section 52(1)(a) of the Copyright Act, 1957)
- Refer to well-known landmark cases that you are confident actually exist
- Bold all case names (e.g. **Kesavananda Bharati v. State of Kerala (1973)**)

CRITICAL: Only cite cases you are highly confident are real. Do NOT fabricate case names. It is better to cite a statute than a dubious case name.

Use paragraphs, bullet points, and numbered lists. Group related issues under ### subheadings when it improves clarity.

## Legal Loopholes & Exceptions

Identify any potential loopholes, exceptions, or alternative legal interpretations. Explain how they might apply.

## Recommendations

Numbered, actionable strategies to mitigate risk:
1. First recommendation with specific legal basis
2. Second recommendation
3. Third recommendation (and so on)

FORMATTING RULES:
- NEVER use markdown tables (pipes |). Use structured prose, bullet points, and subheadings instead.
- Use ## for sections, ### for subsections, **bold** for case names and risk levels.
- Keep your response concise and information-dense. Avoid filler sentences.
"""
