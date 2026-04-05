import asyncio
from app.core.rag import query_legal_assistant

def main():
    query = 'Company XYZ has recently launched a smartwatch named "VitalBand." VitalBand features a continuous heart rate monitoring system that uses a combination of optical sensors and a machine learning algorithm.'
    result = query_legal_assistant(query)
    
    with open('/tmp/patent_evidence_raw.txt', 'w') as f:
        f.write("ANALYSIS:\n")
        f.write(result.get("analysis", "") + "\n\n")
        
        f.write("CITED CASES DETAILS (Pinecone):\n")
        for idx, case in enumerate(result.get("cited_cases_details", [])):
            if isinstance(case, dict):
                f.write(f"[{idx+1}] {case.get('case_name')} ({case.get('judgment_date')})\n")
            else:
                f.write(f"[{idx+1}] {case}\n")
        
        f.write("\nLLM EXTRACTED CITES:\n")
        for idx, case in enumerate(result.get("llm_cited_cases", [])):
            if isinstance(case, dict):
                f.write(f"[{idx+1}] {case.get('case_name', case)}\n")
            else:
                f.write(f"[{idx+1}] {case}\n")
    print("Test Complete. Check /tmp/patent_evidence_raw.txt")

if __name__ == "__main__":
    main()
