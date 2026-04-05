import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()
try:
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index("techniche-legal-index")
    print("Methods available on index:", [m for m in dir(index) if not m.startswith('_')])
    
    # Let's try to embed a string to search
    response = pc.inference.embed(
        model="multilingual-e5-small",
        inputs=["law case judgment"],
        parameters={"input_type": "query"}
    )
    vector = response[0]['values']
    print(f"Generated Vector of length {len(vector)}")
    
    # Now try to query
    res = index.query(
        vector=vector,
        top_k=5,
        include_metadata=True,
    )
    print("Query results:", len(res.matches))
except Exception as e:
    print(f"Error: {e}")
