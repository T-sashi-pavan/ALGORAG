import os
import sys
import asyncio
from dotenv import load_dotenv

# Ensure backend root is on Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load dotenv
load_dotenv()

# Force USE_CLOUD_EMBEDDINGS to True to test our new Hugging Face cloud pooling logic
os.environ["USE_CLOUD_EMBEDDINGS"] = "true"

from embeddings.bge import BGEEmbeddings

async def test_embeddings():
    print("==================================================")
    print("TESTING CLOUD BGE EMBEDDINGS WITH HF INFERENCE API")
    print("==================================================")
    
    try:
        # 1. Initialize Embeddings Client
        print("\n[Step 1] Initializing BGEEmbeddings with Cloud Fallback...")
        embeddings = BGEEmbeddings()
        print(f"-> Model Name: {embeddings.model_name}")
        print(f"-> Use Cloud: {embeddings.use_cloud}")
        
        # 2. Test embed_query
        query = "navy army"
        print(f"\n[Step 2] Testing embed_query for: '{query}'...")
        query_vector = embeddings.embed_query(query)
        print(f"-> Done! Vector type: {type(query_vector)}, length: {len(query_vector)}")
        print(f"-> Sample coordinates (first 5): {query_vector[:5]}")
        
        # 3. Test embed_documents
        docs = [
            "Comparison between Navy and Army implementation of SIOH",
            "Officers of the army and navy",
            "U.S. Air Force Pocket Survival Handbook"
        ]
        print(f"\n[Step 3] Testing embed_documents for batch of {len(docs)} items...")
        doc_vectors = embeddings.embed_documents(docs)
        print(f"-> Done! Returend list length: {len(doc_vectors)}")
        for idx, vec in enumerate(doc_vectors):
            print(f"   Document #{idx+1} vector length: {len(vec)}")
            
        print("\n==================================================")
        print("SUCCESS! EMBEDDINGS POOLED AND EXTRACTED CORRECTLY!")
        print("==================================================")
        return True
    except Exception as e:
        print(f"\n[FAIL] Test threw an exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_embeddings())
