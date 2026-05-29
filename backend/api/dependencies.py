import logging

logger = logging.getLogger("algonox.dependencies")

_vectorstore = None
_embedding_client = None
_reranker = None
_scraper = None
_semantic_chunker = None
_ocr_engine = None

def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        logger.info("Lazily initializing MongoDBVectorStore...")
        from vectorstore.mongodb import MongoDBVectorStore
        _vectorstore = MongoDBVectorStore()
    return _vectorstore

def get_embedding_client():
    global _embedding_client
    if _embedding_client is None:
        logger.info("Lazily initializing BGEEmbeddings (loading PyTorch/SentenceTransformers)...")
        from embeddings.bge import BGEEmbeddings
        _embedding_client = BGEEmbeddings()
    return _embedding_client

def get_reranker():
    global _reranker
    if _reranker is None:
        logger.info("Lazily initializing BGEReranker...")
        from reranker.bge_rerank import BGEReranker
        _reranker = BGEReranker()
    return _reranker

def get_scraper():
    global _scraper
    if _scraper is None:
        logger.info("Lazily initializing PortalScraper...")
        from scraping.engine import PortalScraper
        _scraper = PortalScraper(embedding_client=get_embedding_client())
    return _scraper

def get_semantic_chunker():
    global _semantic_chunker
    if _semantic_chunker is None:
        logger.info("Lazily initializing SemanticChunker...")
        from chunking.semantic import SemanticChunker
        _semantic_chunker = SemanticChunker(embedding_client=get_embedding_client())
    return _semantic_chunker

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        logger.info("Lazily initializing OCREngine...")
        from ocr.engine import OCREngine
        _ocr_engine = OCREngine()
    return _ocr_engine

class LazyProxy:
    """
    Advanced Python Meta-programming Proxy to resolve resources dynamically at runtime,
    allowing FastAPI to start instantly in production environments.
    """
    def __init__(self, getter):
        object.__setattr__(self, "_getter", getter)
    
    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_getter")(), name)
        
    def __setattr__(self, name, value):
        return setattr(object.__getattribute__(self, "_getter")(), name, value)
