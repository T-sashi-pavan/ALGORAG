import re
import logging
import numpy as np

logger = logging.getLogger("algonox.chunking")

class SemanticChunker:
    def __init__(self, embedding_client=None, target_chunk_size=1000, min_chunk_size=200):
        """
        embedding_client: Instance of BGEEmbeddings to calculate sentence similarity.
        """
        self.embedding_client = embedding_client
        self.target_chunk_size = target_chunk_size
        self.min_chunk_size = min_chunk_size

    def split_into_sentences(self, text: str):
        """
        Split a block of text into sentences using simple regex.
        """
        # Split on sentence terminals followed by space
        sentence_endings = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s')
        sentences = sentence_endings.split(text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk_document(self, text: str, metadata_template: dict) -> list:
        """
        Splits a document text into variable-length chunks.
        If self.embedding_client is provided, utilizes Semantic Chunking:
          1. Split into sentences.
          2. Calculate sentence embeddings.
          3. Calculate cosine similarity between adjacent sentences.
          4. Place split boundaries where similarity drops below a threshold.
        Otherwise falls back to character-window based dynamic chunking.
        """
        if not text or not text.strip():
            return []
            
        sentences = self.split_into_sentences(text)
        if not sentences:
            return []
            
        chunks = []
        
        # Method A: Semantic Chunking using sentence embeddings
        if self.embedding_client and len(sentences) > 2:
            try:
                # Embed each sentence
                logger.info(f"Computing embeddings for {len(sentences)} sentences for semantic chunking...")
                sentence_embeddings = self.embedding_client.embed_documents(sentences)
                
                # Compute similarities between consecutive sentences
                similarities = []
                for i in range(len(sentence_embeddings) - 1):
                    vec1 = np.array(sentence_embeddings[i])
                    vec2 = np.array(sentence_embeddings[i+1])
                    norm1 = np.linalg.norm(vec1)
                    norm2 = np.linalg.norm(vec2)
                    if norm1 == 0 or norm2 == 0:
                        sim = 0.0
                    else:
                        sim = float(np.dot(vec1, vec2) / (norm1 * norm2))
                    similarities.append(sim)
                
                # Determine similarity threshold (e.g. 35th percentile of differences or standard threshold)
                if similarities:
                    threshold = np.percentile(similarities, 35) # split at lowest 35% similarity
                else:
                    threshold = 0.6
                
                current_chunk_sentences = []
                current_length = 0
                
                for idx, sentence in enumerate(sentences):
                    current_chunk_sentences.append(sentence)
                    current_length += len(sentence)
                    
                    # Split condition:
                    # - If similarity with next sentence is below the threshold, and we met the min size
                    # - Or if we exceeded the target_chunk_size
                    is_last = idx == len(sentences) - 1
                    should_split = False
                    
                    if not is_last:
                        sim_with_next = similarities[idx]
                        if sim_with_next < threshold and current_length >= self.min_chunk_size:
                            should_split = True
                            
                    if current_length >= self.target_chunk_size:
                        should_split = True
                        
                    if should_split or is_last:
                        chunk_text = " ".join(current_chunk_sentences).strip()
                        if chunk_text:
                            # Attach unique chunk index and context metadata
                            chunk_metadata = metadata_template.copy()
                            chunk_metadata["chunk_index"] = len(chunks)
                            chunk_metadata["word_count"] = len(chunk_text.split())
                            chunk_metadata["char_count"] = len(chunk_text)
                            
                            chunks.append({
                                "text": chunk_text,
                                "metadata": chunk_metadata
                            })
                            
                        current_chunk_sentences = []
                        current_length = 0
                        
                if chunks:
                    logger.info(f"Generated {len(chunks)} semantic chunks successfully.")
                    return chunks
            except Exception as e:
                logger.warning(f"Semantic chunking embedding computation failed: {e}. Falling back to dynamic window chunking.")

        # Method B: Dynamic window / fallback chunking
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_len = len(sentence)
            if current_size + sentence_len > self.target_chunk_size and current_size >= self.min_chunk_size:
                # Flush chunk
                chunk_text = " ".join(current_chunk).strip()
                if chunk_text:
                    chunk_metadata = metadata_template.copy()
                    chunk_metadata["chunk_index"] = len(chunks)
                    chunk_metadata["word_count"] = len(chunk_text.split())
                    chunk_metadata["char_count"] = len(chunk_text)
                    
                    chunks.append({
                        "text": chunk_text,
                        "metadata": chunk_metadata
                    })
                current_chunk = [sentence]
                current_size = sentence_len
            else:
                current_chunk.append(sentence)
                current_size += sentence_len
                
        # Final flush
        if current_chunk:
            chunk_text = " ".join(current_chunk).strip()
            if chunk_text:
                chunk_metadata = metadata_template.copy()
                chunk_metadata["chunk_index"] = len(chunks)
                chunk_metadata["word_count"] = len(chunk_text.split())
                chunk_metadata["char_count"] = len(chunk_text)
                
                chunks.append({
                    "text": chunk_text,
                    "metadata": chunk_metadata
                })
                
        logger.info(f"Generated {len(chunks)} dynamic chunks via fallback windowing.")
        return chunks
