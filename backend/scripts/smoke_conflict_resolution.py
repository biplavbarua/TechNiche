import time
from app.ingest import process_and_store_document
from app.utils.pinecone import get_pinecone_index
from app.core.rag import query_legal_assistant

index = get_pinecone_index()


def run_test():
    print("Starting Temporal Conflict-Resolution Verification...\n")
    
    # ==========================================
    # 1. Ingest Old Case
    # ==========================================
    print("=== Step 1: Ingesting Old Case ===")
    title1 = 'Tech Innovations Pvt Ltd vs. State of Karnataka (2021)'
    text1 = 'The High Court rules that all software-as-a-service (SaaS) platforms operating within the state are exempt from local digital infrastructure taxes for a period of ten years, provided their primary servers are hosted domestically.'
    
    metadata1 = {
        "title": title1,
        "source": "test_script"
    }
    process_and_store_document(text1, metadata1)
    
    # Short wait to ensure chroma persistence sync
    time.sleep(2)
    
    # ==========================================
    # 2. Query 1
    # ==========================================
    print("\n=== Step 2: Querying (Pre-overrule) ===")
    query = "How many years of tax exemption do SaaS platforms get?"
    resp1 = query_legal_assistant(query)
    print(f"Cited Cases: {resp1.get('cited_cases', [])}")
    print(f"LLM Answer:\n{resp1.get('analysis', '')}\n")
    
    # ==========================================
    # 3. Ingest New Case
    # ==========================================
    print("=== Step 3: Ingesting New Case (Overrules Old Case) ===")
    title2 = 'Union of India vs. Tech Innovations Pvt Ltd (2026)'
    text2 = "The Supreme Court of India hereby reviews the lower court's decision regarding digital infrastructure taxes. The previous ruling in Tech Innovations Pvt Ltd vs. State of Karnataka (2021) is explicitly overruled. SaaS platforms are only exempt for a period of three years, effective immediately."
    
    metadata2 = {
        "title": title2,
        "source": "test_script"
    }
    process_and_store_document(text2, metadata2)
    
    # Short wait for chroma DB update
    time.sleep(2)
    
    # ==========================================
    # 4. Verifying Database Mutation
    # ==========================================
    print("\n=== Step 4: Verifying Database Mutation ===")
    
    # Query Pinecone using metadata filter
    # Note: top_k=10 to find all chunks for this title
    results = index.query(
        namespace="__default__",
        filter={"title": title1},
        top_k=10,
        include_metadata=True
    )
    
    if results and results.get("matches"):
        print(f"Metadata for '{title1}' in Pinecone:")
        for match in results["matches"]:
            m = match.get("metadata", {})
            print(f"  - status: {m.get('status', 'N/A')}")
    else:
        print(f"Could not find case: {title1} in Pinecone using metadata filter")

        
    # ==========================================
    # 5. Query 2
    # ==========================================
    print("\n=== Step 5: Querying (Post-overrule) ===")
    resp2 = query_legal_assistant(query)
    print(f"Cited Cases: {resp2.get('cited_cases', [])}")
    print(f"LLM Answer:\n{resp2.get('analysis', '')}\n")

if __name__ == "__main__":
    run_test()
