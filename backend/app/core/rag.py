import os
import re
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

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
if not PINECONE_API_KEY:
    raise EnvironmentError("PINECONE_API_KEY not found in environment variables.")

pc = Pinecone(api_key=PINECONE_API_KEY)
INDEX_NAME = "techniche-legal-index"
index = pc.Index(INDEX_NAME)

# The embedding model hosted by Pinecone (Integrated Inference)
EMBED_MODEL = "llama-text-embed-v2"

# ─── LLM Models (Free models fallback cascade) ───────────────────────────────

MODELS = [
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
                timeout=45.0  # Fails sequence to the next model if hanging > 45s
            )
            return response.choices[0].message.content
        except Exception as e:
            last_error = e
            print(f"Warning: Model {model_name} failed ({e}). Trying next fallback...")
            continue
            
    return f"Error from AI Provider (All models failed). Last error: {str(last_error)}"


def _assess_relevance(hits: list, user_query: str) -> dict:
    """
    Intelligent relevance assessment using score distribution analysis.
    
    The llama-text-embed-v2 model produces cosine similarity scores in a
    compressed range (~0.20–0.40). A static threshold cannot separate
    relevant from irrelevant because BOTH score similarly low.
    
    Instead we use TWO signals:
    
    1. ABSOLUTE FLOOR — Any top score below 0.30 is definitely irrelevant.
    2. SCORE GAP — If the top score is not meaningfully higher than the
       median score, the query doesn't match any specific case better 
       than random noise — so nothing is truly relevant.
    3. LLM RELEVANCE CHECK — As a final gate, we ask the LLM directly 
       whether the top retrieved case is actually relevant to the query.
    """
    if not hits:
        return {"is_relevant": False, "relevant_hits": [], "reason": "no_hits"}
    
    scores = [h.get("_score", 0) for h in hits]
    top_score = max(scores)
    median_score = sorted(scores)[len(scores) // 2]
    score_gap = top_score - median_score
    avg_score = sum(scores) / len(scores)
    
    print(f"DEBUG RELEVANCE: top={top_score:.4f}, median={median_score:.4f}, "
          f"avg={avg_score:.4f}, gap={score_gap:.4f}")
    
    # Gate 1: Absolute floor — nothing useful below 0.30
    if top_score < 0.30:
        return {
            "is_relevant": False,
            "relevant_hits": [],
            "reason": f"top_score_too_low ({top_score:.4f} < 0.30)"
        }
    
    # Gate 2: Score gap — the top hit must stand out from the crowd.
    # If gap < 0.03, all hits are equally (ir)relevant.
    if score_gap < 0.03:
        return {
            "is_relevant": False,
            "relevant_hits": [],
            "reason": f"no_score_gap (gap={score_gap:.4f} < 0.03, all hits equally poor)"
        }
    
    # Gate 3: LLM quick relevance check
    # Ask the LLM to verify the top hit is actually related to the query.
    top_hit = hits[0]
    top_title = top_hit.get("fields", {}).get("title", "Unknown")
    top_text = top_hit.get("fields", {}).get("text", "")[:500]
    
    relevance_prompt = f"""You are a relevance classifier. Determine if the following legal case is ACTUALLY RELEVANT to the user's query.

USER QUERY: {user_query}

RETRIEVED CASE TITLE: {top_title}
RETRIEVED CASE EXCERPT: {top_text}

Answer with ONLY one word: RELEVANT or IRRELEVANT

Think carefully: Does this case's subject matter genuinely relate to the legal question being asked? A trademark case is NOT relevant to a query about naming a child. A copyright case is NOT relevant to a query about criminal law. Only answer RELEVANT if the case's legal domain directly addresses the user's question."""
    
    try:
        relevance_check = get_llm_response(relevance_prompt).strip().upper()
        print(f"DEBUG RELEVANCE CHECK: LLM says '{relevance_check}' for '{top_title}'")
        
        # Extract the core answer — LLMs sometimes add reasoning
        is_relevant_llm = "RELEVANT" in relevance_check and "IRRELEVANT" not in relevance_check
    except Exception as e:
        print(f"DEBUG: LLM relevance check failed: {e}")
        # If the check fails, be conservative — assume irrelevant for low scores
        is_relevant_llm = top_score > 0.40
    
    if not is_relevant_llm:
        return {
            "is_relevant": False,
            "relevant_hits": [],
            "reason": f"llm_classified_irrelevant (top_title='{top_title}')"
        }
    
    # All gates passed — return the hits that are above (median + 0.01)
    # This naturally filters out the noise floor.
    threshold = median_score + 0.01
    relevant_hits = [h for h in hits if h.get("_score", 0) >= threshold]
    
    return {
        "is_relevant": True,
        "relevant_hits": relevant_hits,
        "reason": f"passed_all_gates (top={top_score:.4f}, gap={score_gap:.4f})"
    }


def _detect_legal_domain(hits: list) -> str:
    """
    Extracts the dominant legal domain from retrieved chunk metadata.
    Falls back to 'Indian Law' if no domain is found.
    """
    domains = []
    for hit in hits:
        fields = hit.get("fields", {})
        domain = fields.get("ai_legal_domain", "")
        if domain and domain != "General" and domain != "UNKNOWN":
            domains.append(domain)
    
    if not domains:
        return "Indian Law"
    
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


def _verify_citations(analysis_text: str, retrieved_titles: list[str]) -> dict:
    """
    Post-generation citation verification.
    
    Cross-references case names mentioned in the LLM's response against
    the titles of actually-retrieved documents. Flags any ungrounded
    citations that the LLM may have hallucinated.
    """
    analysis_lower = analysis_text.lower()
    
    grounded = []      # Referenced in response AND retrieved from DB
    ungrounded = []    # Retrieved from DB but NOT referenced in response
    
    for title in retrieved_titles:
        title_lower = title.lower()
        words = [w for w in title_lower.split() if len(w) > 3 and w not in ("the", "and", "vs.", "vs", "state", "union", "india")]
        
        match_count = sum(1 for w in words if w in analysis_lower)
        match_ratio = match_count / max(len(words), 1)
        
        if match_ratio >= 0.4 or title_lower in analysis_lower:
            grounded.append(title)
        else:
            ungrounded.append(title)
    
    return {
        "grounded": grounded,
        "ungrounded": ungrounded,
        "confidence": "high" if len(grounded) > 0 else "low"
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
        search_results = index.search(
            namespace="__default__",
            query={
                "top_k": 20,
                "inputs": {"text": user_query},
                "filter": {"status": {"$eq": "active"}}
            }
        )
        
        hits = []
        if search_results and hasattr(search_results, 'result') and search_results.result.hits:
            hits = search_results.result.hits
        
        print(f"DEBUG: Pinecone search returned {len(hits)} raw hits.")
        for hit in hits:
            score = hit.get("_score", 0)
            title = hit.get("fields", {}).get("title", "Unknown")
            print(f"  HIT: score={score:.4f}  title={title}")
        
        # ── 2. Multi-gate relevance assessment ──
        relevance = _assess_relevance(hits, user_query)
        print(f"DEBUG RELEVANCE DECISION: is_relevant={relevance['is_relevant']}, "
              f"reason={relevance['reason']}, "
              f"hits_passing={len(relevance['relevant_hits'])}")
        
        if relevance["is_relevant"] and relevance["relevant_hits"]:
            has_relevant_context = True
            relevant_hits = relevance["relevant_hits"]
            seen_titles = set()
            selected_docs = []
            
            # Diversity Filter: Prioritize chunks from different cases
            for hit in relevant_hits:
                fields = hit.get("fields", {})
                title = fields.get("title", "Unknown Case")
                clean_title = title.strip()
                chunk_text = fields.get("text", "")
                
                # Stop if we have enough context (max 7 chunks)
                if len(selected_docs) >= 7:
                    break
                    
                is_valid_title = (
                    clean_title 
                    and clean_title not in ('Unknown Case', 'UNKNOWN', 'Full Document') 
                    and not clean_title.startswith('[')
                )
                
                # Force diversity: max 2 chunks per case until we have 3 distinct cases
                chunk_count_for_case = sum(1 for c in selected_docs if c['title'] == clean_title)
                if is_valid_title and chunk_count_for_case >= 2 and len(seen_titles) < 3:
                    continue 
                
                selected_docs.append({
                    'doc': chunk_text, 
                    'fields': fields, 
                    'title': clean_title,
                    'score': hit.get("_score", 0)
                })
                if is_valid_title:
                    seen_titles.add(clean_title)

            # Build context from selected_docs
            for item in selected_docs:
                doc = item['doc']
                fields = item['fields']
                title = fields.get('title', 'Unknown Case')
                clean_title = item['title']
                score = item['score']
                
                domain = fields.get('ai_legal_domain', '')
                judgment_date = fields.get('ai_judgment_date', '')
                date_info = f" (Decided: {judgment_date})" if judgment_date and judgment_date != "UNKNOWN" else ""
                domain_info = f" [{domain}]" if domain and domain != "General" else ""
                
                context_text += f"\nCase: {title}{date_info}{domain_info} [Relevance: {score:.2f}]\nContent: {doc[:1500]}...\n"
                
                if clean_title and clean_title not in ('Unknown Case', 'UNKNOWN', 'Full Document') and not clean_title.startswith('['):
                    if clean_title not in cited_cases:
                        cited_cases.append(clean_title)
                        snippet = doc.strip()
                        if len(snippet) > 400:
                            snippet = snippet[:400] + "..."
                        cited_cases_details.append({
                            "title": clean_title,
                            "url": fields.get('url', ''),
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
