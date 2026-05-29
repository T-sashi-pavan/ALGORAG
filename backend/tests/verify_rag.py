import os
import sys
from dotenv import load_dotenv

# Ensure backend root is on Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from embeddings.bge import BGEEmbeddings
from vectorstore.mongodb import MongoDBVectorStore

def run_rag_diagnostics():
    print("==================================================")
    print("ALGONOX DIAGNOSTIC: EMBEDDING & VECTORSTORE TEST")
    print("==================================================")
    load_dotenv()
    
    # 1. Initialize BGE Embeddings
    print("\n[Step 1] Loading BGE Embeddings...")
    try:
        embedder = BGEEmbeddings()
        print(f"-> Embedding Model successfully loaded: {embedder.model_name}")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to load BGE Embeddings: {e}")
        return False

    # 2. Test encoding simple string
    print("\n[Step 2] Testing query vector generation...")
    test_query = "What is multimodal RAG intelligence?"
    try:
        vector = embedder.embed_query(test_query)
        print(f"-> Generated query vector. Length: {len(vector)}")
        if len(vector) > 0:
            print("-> [SUCCESS] Vector calculation verification passed!")
        else:
            print("-> [FAIL] Vector generated was empty.")
            return False
    except Exception as e:
        print(f"ERROR: Encoding failed: {e}")
        return False

    # 3. Test MongoDB connection and insertion
    print("\n[Step 3] Loading MongoDB Atlas Vector Store...")
    try:
        db = MongoDBVectorStore()
        print("-> Connection established to MongoDB Atlas.")
    except Exception as e:
        print(f"CRITICAL ERROR: MongoDB connection failed: {e}")
        print("Please check your MONGODB_URI configuration.")
        return False

    # 4. Insert dummy test documents
    print("\n[Step 4] Inserting diagnostic test nodes...")
    test_chunks = [
        {
            "text": "ALGONOX is an enterprise-grade artificial intelligence dashboard utilizing Next.js 14 and FastAPI.",
            "embedding": embedder.embed_query("ALGONOX is an enterprise-grade artificial intelligence dashboard utilizing Next.js 14 and FastAPI."),
            "document_id": "diag_test_doc_001",
            "metadata": {
                "filename": "diagnostic_spec.pdf",
                "page_number": 1,
                "section": "Overview"
            }
        },
        {
            "text": "The platform implements semantic chunking and CrossEncoder rerankers to ensure zero hallucination.",
            "embedding": embedder.embed_query("The platform implements semantic chunking and CrossEncoder rerankers to ensure zero hallucination."),
            "document_id": "diag_test_doc_001",
            "metadata": {
                "filename": "diagnostic_spec.pdf",
                "page_number": 2,
                "section": "Architecture"
            }
        }
    ]
    
    try:
        inserted = db.insert_chunks(test_chunks)
        print(f"-> Successfully inserted {inserted} test chunks into Atlas collection.")
    except Exception as e:
        print(f"ERROR: Failed inserting test chunks: {e}")
        return False

    # 5. Search for inserted content
    print("\n[Step 5] Querying vector index...")
    try:
        results = db.search(query_vector=vector, limit=2, document_ids=["diag_test_doc_001"])
        print(f"-> Search retrieved {len(results)} matches.")
        for idx, match in enumerate(results):
            print(f"   Match #{idx+1} [Score: {round(match['score'], 4)}]:")
            print(f"   Text: '{match['text']}'")
            print(f"   Source: {match['metadata'].get('filename')} - Page {match['metadata'].get('page_number')}")
        
        if len(results) > 0:
            print("-> [SUCCESS] Vector retrieval and similarity calculation verification passed!")
        else:
            print("-> [FAIL] Vector query returned zero results.")
            return False
    except Exception as e:
        print(f"ERROR: Search execution failed: {e}")
        return False

    # 6. Cleanup diagnostic documents
    print("\n[Step 6] Cleaning up vector database...")
    try:
        deleted = db.delete_document("diag_test_doc_001")
        print(f"-> Successfully deleted {deleted} test chunks from Atlas database collection.")
        print("-> [SUCCESS] Database cleanup successful!")
    except Exception as e:
        print(f"WARNING: Cleanup failed: {e}")

    print("\n==================================================")
    print("ALGONOX DIAGNOSTIC VERIFICATION COMPLETED!")
    print("==================================================")
    return True

if __name__ == "__main__":
    success = run_rag_diagnostics()
    sys.exit(0 if success else 1)
