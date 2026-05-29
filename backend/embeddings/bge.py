import os
import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("algonox.embeddings")

class BGEEmbeddings:
    def __init__(self):
        self.model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
        self.model = None
        
        # Load model with automatic lightweight fallbacks
        try:
            logger.info(f"Attempting to load local embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Local BGE embedding model loaded successfully.")
        except Exception as e:
            logger.warning(f"Failed to load {self.model_name} due to: {e}. Attempting lightweight fallback 'BAAI/bge-small-en-v1.5'...")
            try:
                self.model = SentenceTransformer("BAAI/bge-small-en-v1.5")
                self.model_name = "BAAI/bge-small-en-v1.5"
                logger.info("Lightweight BGE small embedding model loaded successfully.")
            except Exception as e2:
                logger.error(f"Failed loading BGE small model: {e2}. Falling back to 'all-MiniLM-L6-v2'...")
                try:
                    self.model = SentenceTransformer("all-MiniLM-L6-v2")
                    self.model_name = "all-MiniLM-L6-v2"
                    logger.info("Standard MiniLM model loaded successfully as final fallback.")
                except Exception as e3:
                    logger.error(f"Critical error: All embedding model loading failed: {e3}")
                    raise e3

    def embed_query(self, text: str):
        """
        Embeds a single query string.
        For BGE models, standard query instruction might be needed:
        "Represent this sentence for searching relevant passages: "
        """
        if not self.model:
            raise ValueError("Embedding model not loaded.")
        
        # If it's a BGE model, prepend search query prefix for maximum similarity accuracy
        input_text = text
        if "bge" in self.model_name.lower():
            input_text = f"Represent this sentence for searching relevant passages: {text}"
            
        try:
            vector = self.model.encode(input_text, normalize_embeddings=True)
            return vector.tolist()
        except Exception as e:
            logger.error(f"Error encoding query: {e}")
            raise e

    def embed_documents(self, texts: list):
        """
        Embeds a list of document strings.
        """
        if not self.model:
            raise ValueError("Embedding model not loaded.")
            
        try:
            vectors = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            return [v.tolist() for v in vectors]
        except Exception as e:
            logger.error(f"Error encoding documents: {e}")
            raise e
