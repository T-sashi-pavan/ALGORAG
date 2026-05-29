import logging
import uuid
import datetime
import tempfile
import os
import httpx
import PyPDF2
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional

# Import custom pipelines & scraping engine
from scraping.engine import PortalScraper
from embeddings.bge import BGEEmbeddings
from vectorstore.mongodb import MongoDBVectorStore
from chunking.semantic import SemanticChunker
from ocr.engine import OCREngine

logger = logging.getLogger("algonox.routes.search")
router = APIRouter(prefix="/api/search", tags=["search"])

class SearchRequest(BaseModel):
    keyword: str

class SearchResultCard(BaseModel):
    portal: str
    title: str
    url: str
    snippet: str
    published_date: str
    status: str
    relevance_score: Optional[float] = 0.0

# Initialize instances
try:
    embedding_client = BGEEmbeddings()
    scraper = PortalScraper(embedding_client=embedding_client)
    vectorstore = MongoDBVectorStore()
    semantic_chunker = SemanticChunker(embedding_client=embedding_client)
    ocr_engine = OCREngine()
except Exception as e:
    logger.error(f"Failed to initialize search route dependencies: {e}")


@router.post("", response_model=List[SearchResultCard])
async def search_portals(request: SearchRequest):
    """
    Triggers concurrent async searches across the 8 supported portals (PDF Drive, arXiv, DOAJ, etc.).
    Extracts documents, runs semantic embedding comparison, and returns sorted document cards.
    """
    keyword = request.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="Search keyword cannot be empty.")
        
    try:
        logger.info(f"Initiating multi-portal scrape for keyword: '{keyword}'")
        ranked_cards = await scraper.search_all_portals(keyword)
        
        # Serialize response to model structure
        cards = []
        for item in ranked_cards:
            cards.append(SearchResultCard(
                portal=item["portal"],
                title=item["title"],
                url=item["url"],
                snippet=item["snippet"],
                published_date=item["published_date"],
                status=item["status"],
                relevance_score=item.get("relevance_score", 0.0)
            ))
        return cards
    except Exception as e:
        logger.error(f"Error executing portal searches: {e}")
        raise HTTPException(status_code=500, detail="Failed to run scraping engines across target portals.")

def process_scraped_document_in_background(url: str, filename: str, document_id: str):
    """
    Downloads a document from url, parses it based on content type, chunks, embeds, and indexes it.
    """
    try:
        logger.info(f"Starting background scraping & indexing for URL: '{url}' (Document ID: {document_id})")
        
        # 1. Download document
        is_pdf = url.lower().endswith(".pdf") or "pdf" in url.lower()
        page_texts = []
        
        # User agent header to avoid bot-blocking blocks
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        with httpx.Client(follow_redirects=True, timeout=60.0) as client:
            logger.info(f"Downloading content from: {url}")
            response = client.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Failed downloading scraped document: HTTP status {response.status_code}")
                return
                
            content_type = response.headers.get("content-type", "").lower()
            if "pdf" in content_type:
                is_pdf = True
                
            if is_pdf:
                logger.info(f"Parsing downloaded PDF...")
                # Write response bytes out to a safe temporary file
                fd, temp_file_path = tempfile.mkstemp(suffix=".pdf")
                try:
                    with os.fdopen(fd, "wb") as f:
                        f.write(response.content)
                        
                    # Extract page layout blocks
                    with open(temp_file_path, "rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        num_pages = len(reader.pages)
                        for page_idx in range(num_pages):
                            page = reader.pages[page_idx]
                            page_text = page.extract_text() or ""
                            
                            # Checked scanned layout detection fallback
                            if len(page_text.strip()) < 50 and ocr_engine:
                                logger.info(f"PDF page {page_idx + 1} looks scanned. Extracting via OCR fallback...")
                                try:
                                    images_on_page = page.images
                                    ocr_results = []
                                    for img_idx, img_obj in enumerate(images_on_page):
                                        ocr_text = ocr_engine.extract_text_from_image_bytes(img_obj.data)
                                        if ocr_text:
                                            ocr_results.append(ocr_text)
                                    if ocr_results:
                                        page_text = "\n".join(ocr_results)
                                except Exception as ocr_ex:
                                    logger.error(f"Failed inline OCR on page: {ocr_ex}")
                                    
                            page_texts.append((page_idx + 1, page_text))
                finally:
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
            else:
                logger.info(f"Parsing downloaded content as HTML web page...")
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "html.parser")
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text(separator=" ")
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                cleaned_text = "\n".join(chunk for chunk in chunks if chunk)
                page_texts.append((1, cleaned_text))
                
        # 2. Chunking & Indexing Chunk by Chunk
        all_chunks = []
        for page_num, text_content in page_texts:
            if not text_content.strip():
                continue
                
            metadata = {
                "document_id": document_id,
                "filename": filename,
                "page_number": page_num,
                "created_at": datetime.datetime.utcnow().isoformat(),
                "file_type": "pdf" if is_pdf else "html",
                "source_url": url
            }
            
            chunks = semantic_chunker.chunk_document(text_content, metadata)
            all_chunks.extend(chunks)
            
        if not all_chunks:
            logger.warning(f"No text extracted or chunks generated for scraped document: {filename}")
            return
            
        # 3. Create Embeddings in Batches
        logger.info(f"Generating dense embeddings for {len(all_chunks)} chunks from '{filename}'")
        texts_to_embed = [c["text"] for c in all_chunks]
        embeddings = embedding_client.embed_documents(texts_to_embed)
        
        # 4. Assemble and Insert
        for idx, chunk in enumerate(all_chunks):
            chunk["embedding"] = embeddings[idx]
            chunk["document_id"] = document_id
            
        vectorstore.insert_chunks(all_chunks)
        logger.info(f"Background scraping indexing completed successfully for document: {filename}")
        
    except Exception as e:
        logger.error(f"Error in background scraped document processing: {e}")

@router.post("/index-scraped")
async def index_scraped_document(url: str, filename: str, background_tasks: BackgroundTasks):
    """
    Downloads, scrapes, and indexes a clicked scraped document into MongoDB in the background.
    """
    if not url:
        raise HTTPException(status_code=400, detail="Document URL is required.")
    if not filename:
        raise HTTPException(status_code=400, detail="Document filename is required.")
        
    document_id = str(uuid.uuid4())
    
    background_tasks.add_task(
        process_scraped_document_in_background,
        url,
        filename,
        document_id
    )
    
    return {
        "message": "Scraped document queue ingestion initiated.",
        "document_id": document_id,
        "filename": filename,
        "status": "Indexing"
    }
