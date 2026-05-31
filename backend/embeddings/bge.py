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
            if isinstance(res, list) and len(res) > 0:
                if isinstance(res[0], list):
                    return res[0]
                return res  # 1D list already
            raise ValueError(f"Unexpected response format from HF API: {res}")

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
            if isinstance(res, list) and len(res) > 0:
                if isinstance(res[0], list):
                    return res
                return [res]  # 1D list to 2D
            raise ValueError(f"Unexpected response format from HF API: {res}")

        if not self.model:
            raise ValueError("Embedding model not loaded.")
            
        try:
            vectors = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            return [v.tolist() for v in vectors]
        except Exception as e:
            logger.error(f"Error encoding documents: {e}")
            raise e

