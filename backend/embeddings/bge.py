import os
import logging
import time
import httpx

logger = logging.getLogger("algonox.embeddings")

class BGEEmbeddings:
    def __init__(self):
        self.model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        self.model = None
        self.use_cloud = os.getenv("USE_CLOUD_EMBEDDINGS", "false").lower() == "true"
        
        if self.use_cloud:
            logger.info(f"Using Cloud-based Serverless Hugging Face embeddings ({self.model_name}) to preserve RAM on Render.")
            return

        # Load model with automatic lightweight fallbacks
        try:
            logger.info(f"Attempting to load local embedding model: {self.model_name}")
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            logger.info("Local BGE embedding model loaded successfully.")
        except Exception as e:
            logger.warning(f"Failed to load local model {self.model_name} due to: {e}. Falling back to cloud-based Serverless Hugging Face API to prevent OOM crash...")
            self.use_cloud = True

    def _query_hf_api(self, texts: list) -> list:
        """
        Helper to call Hugging Face Inference API for feature extraction.
        """
        api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model_name}"
        headers = {}
        token = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        # Standard retry loop for API spin-up / model loading
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(
                        api_url, 
                        headers=headers, 
                        json={"inputs": texts, "options": {"wait_for_model": True}}
                    )
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 503:
                        # Model is loading, wait and retry
                        logger.warning(f"Hugging Face model is loading (503). Retrying in 5 seconds... (Attempt {attempt+1}/{max_retries})")
                        time.sleep(5)
                        continue
                    else:
                        raise ValueError(f"HF API returned status {response.status_code}: {response.text}")
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"HF API embedding extraction failed after {max_retries} attempts: {e}")
                    raise e
                time.sleep(2)
        raise ValueError("HF API failed to return embeddings.")

    def _pool_response(self, res, expect_batch: bool):
        """
        Custom Mean Pooling Parser for Hugging Face Inference API feature-extraction pipeline.
        BERT/BGE feature extraction returns unpooled token-level hidden states in a 3D/2D array:
          - Single text unpooled: depth 2 of shape [seq_len, embedding_dim]
          - Batch text unpooled: depth 3 of shape [batch_size, seq_len, embedding_dim]
        We pool along the sequence dimension using numpy.mean to obtain perfect 1D/2D sentence vectors.
        """
        import numpy as np
        if not isinstance(res, list) or len(res) == 0:
            raise ValueError("Invalid response from Hugging Face Inference API.")
            
        # Dynamically determine the nesting depth of the returned JSON list
        depth = 0
        curr = res
        while isinstance(curr, list) and len(curr) > 0:
            depth += 1
            curr = curr[0]
            
        logger.info(f"Hugging Face response parsed with depth={depth} (expect_batch={expect_batch})")
        
        # Case 1: depth is 3 -> shape is [batch_size, seq_len, embedding_dim]
        if depth == 3:
            pooled = []
            for batch_item in res:
                arr = np.array(batch_item)  # shape: [seq_len, embedding_dim]
                mean_vec = np.mean(arr, axis=0)  # shape: [embedding_dim]
                pooled.append(mean_vec.tolist())
            
            if expect_batch:
                return pooled
            else:
                return pooled[0]
                
        # Case 2: depth is 2 -> shape could be [seq_len, embedding_dim] or already pooled [batch_size, embedding_dim]
        elif depth == 2:
            if expect_batch:
                # If we expect a batch, and it is depth 2, it is already a pooled batch: [batch_size, embedding_dim]
                return res
            else:
                # If we expect a single vector, and it is depth 2, it is unpooled: [seq_len, embedding_dim]
                arr = np.array(res)
                mean_vec = np.mean(arr, axis=0)
                return mean_vec.tolist()
                
        # Case 3: depth is 1 -> shape is [embedding_dim]
        elif depth == 1:
            if expect_batch:
                return [res]
            else:
                return res
                
        raise ValueError(f"Unsupported embedding response shape from HF: depth {depth}")

    def embed_query(self, text: str):
        """
        Embeds a single query string.
        """
        # If it's a BGE model, prepend search query prefix for maximum similarity accuracy
        input_text = text
        if "bge" in self.model_name.lower():
            input_text = f"Represent this sentence for searching relevant passages: {text}"
            
        if self.use_cloud:
            res = self._query_hf_api([input_text])
            return self._pool_response(res, expect_batch=False)

        if not self.model:
            raise ValueError("Embedding model not loaded.")
            
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
        if not texts:
            return []

        if self.use_cloud:
            res = self._query_hf_api(texts)
            return self._pool_response(res, expect_batch=True)

        if not self.model:
            raise ValueError("Embedding model not loaded.")
            
        try:
            vectors = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            return [v.tolist() for v in vectors]
        except Exception as e:
            logger.error(f"Error encoding documents: {e}")
            raise e

