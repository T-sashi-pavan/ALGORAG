import os
import logging

logger = logging.getLogger("algonox.reranker")

class BGEReranker:
    def __init__(self):
        self.model_name = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-large")
        self.model = None
        
        try:
            logger.info(f"Attempting to load reranker model: {self.model_name}")
            from sentence_transformers import CrossEncoder
            # CrossEncoder loads standard reranking models
            self.model = CrossEncoder(self.model_name)
            logger.info("Reranker model loaded successfully.")
        except Exception as e:
            logger.warning(f"Failed to load {self.model_name}: {e}. Attempting to load lightweight 'BAAI/bge-reranker-base'...")
            try:
                self.model = CrossEncoder("BAAI/bge-reranker-base")
                self.model_name = "BAAI/bge-reranker-base"
                logger.info("Lightweight reranker model loaded successfully.")
            except Exception as e2:
                logger.warning(f"Failed loading BGE reranker base: {e2}. Operating RAG without CrossEncoder (similarity scores only).")
                self.model = None

    def rerank(self, query: str, documents: list, top_k: int = 5):
        """
        documents: List of dicts, each with format:
          { "text": string, "metadata": dict, "score": float, "document_id": str }
        """
        if not documents:
            return []
            
        # If reranker model is not loaded, just return documents sorted by vector similarity
        if not self.model:
            logger.info("Reranker not active, skipping CrossEncoder scoring.")
            sorted_docs = sorted(documents, key=lambda x: x["score"], reverse=True)
            return sorted_docs[:top_k]
            
        try:
            pairs = [[query, doc["text"]] for doc in documents]
            # Compute cross-encoder scores
            scores = self.model.predict(pairs)
            
            # Update scores in-place
            for idx, score in enumerate(scores):
                # Sigmoid normalization for cleaner UI display
                norm_score = float(1 / (1 + os.sys.float_info.epsilon + os.sys.float_info.epsilon - score)) # standard sigmoid: 1 / (1 + exp(-x))
                # Wait, standard cross encoder output can be raw logits, let's use standard sigmoid
                import math
                try:
                    sig_score = 1 / (1 + math.exp(-score))
                except Exception:
                    sig_score = float(score)
                documents[idx]["rerank_score"] = sig_score
                
            # Sort by rerank score descending
            reranked_docs = sorted(documents, key=lambda x: x.get("rerank_score", 0.0), reverse=True)
            return reranked_docs[:top_k]
        except Exception as e:
            logger.error(f"Error during reranking: {e}. Returning raw similarity documents.")
            sorted_docs = sorted(documents, key=lambda x: x["score"], reverse=True)
            return sorted_docs[:top_k]
