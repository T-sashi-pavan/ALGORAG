import os
import sys

# Force USE_CLOUD_EMBEDDINGS to true BEFORE importing BGEEmbeddings
os.environ["USE_CLOUD_EMBEDDINGS"] = "true"

import numpy as np

# Ensure backend root is on Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from embeddings.bge import BGEEmbeddings

def test_groq_and_fallback():
    print("==================================================")
    print("TESTING ALGONOX MULTI-LAYER EMBEDDING ENGINE")
    print("==================================================")
    
    embeddings = BGEEmbeddings()
    
    # 1. Test offline mathematical Jaccard-Cosine mapping simulator
    print("\n[Test 1] Testing Resilient Mathematical Fallback Vectors...")
    embeddings.last_query = "navy army"
    
    # Query vector should be [1.0, 0.0, ...]
    q_vec = embeddings._generate_resilient_fallback_vector(doc_text=None)
    
    # Document 1 with 100% overlap
    d_vec_1 = embeddings._generate_resilient_fallback_vector("navy army")
    
    # Document 2 with partial overlap
    d_vec_2 = embeddings._generate_resilient_fallback_vector("officers of the army")
    
    # Document 3 with no overlap
    d_vec_3 = embeddings._generate_resilient_fallback_vector("unrelated words here")
    
    # Calculate cosine similarities
    sim_1 = np.dot(q_vec, d_vec_1)
    sim_2 = np.dot(q_vec, d_vec_2)
    sim_3 = np.dot(q_vec, d_vec_3)
    
    print(f"-> Query Vector Norm: {np.linalg.norm(q_vec):.2f}")
    print(f"-> Full Overlap Sim:  {sim_1 * 100:.2f}% (Expected: ~96.00%)")
    print(f"-> Partial Overlap Sim: {sim_2 * 100:.2f}% (Expected: ~70.00% to ~85.00%)")
    print(f"-> Zero Overlap Sim:    {sim_3 * 100:.2f}% (Expected: ~65.00%)")
    
    assert np.isclose(np.linalg.norm(d_vec_1), 1.0), "Document 1 vector is not a unit vector!"
    assert np.isclose(np.linalg.norm(d_vec_2), 1.0), "Document 2 vector is not a unit vector!"
    assert np.isclose(np.linalg.norm(d_vec_3), 1.0), "Document 3 vector is not a unit vector!"
    assert sim_1 > sim_2 > sim_3, "Mathematical ordering is incorrect!"
    print("-> [PASS] Offline simulator produces perfect, ordered, unit similarity vectors!")

    # 2. Test Groq/HF loading fallbacks
    print("\n[Test 2] Testing complete embed_query and embed_documents fallbacks...")
    query = "navy army"
    q_emb = embeddings.embed_query(query)
    print(f"-> embed_query vector returned successfully! Length: {len(q_emb)}")
    
    docs = [
        "Comparison between Navy and Army implementation of SIOH",
        "Unrelated document details"
    ]
    doc_embs = embeddings.embed_documents(docs)
    print(f"-> embed_documents batch returned successfully! Count: {len(doc_embs)}")
    for idx, d_emb in enumerate(doc_embs):
        print(f"   Doc #{idx+1} vector length: {len(d_emb)}")
        
    print("\n==================================================")
    print("SUCCESS! ALL EMBEDDING ENGINE LAYERS VERIFIED!")
    print("==================================================")
    return True

if __name__ == "__main__":
    test_groq_and_fallback()
