import os
import sys

# Force UTF-8 encoding on Windows to prevent UnicodeEncodeErrors from external console output (e.g. easyocr/tqdm)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load all configurations from .env
load_dotenv()

# Setup professional logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("algonox.main")

# Initialize FastAPI App
app = FastAPI(
    title="ALGONOX RAG MODEL Backend API",
    description="Enterprise-grade Multimodal Retrieval-Augmented Generation & Intelligent Scraping Engine Platform",
    version="1.0.0"
)

# Configure Premium CORS Policies for secure Next.js interactions
allowed_origins = [
    "http://localhost:3000",
    "https://algonox-rag-frontend.onrender.com"
]
env_origins = os.getenv("ALLOWED_ORIGINS")
if env_origins:
    for o in env_origins.split(","):
        o_clean = o.strip()
        if o_clean and o_clean not in allowed_origins:
            allowed_origins.append(o_clean)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import route handlers
from api.routes.upload import router as upload_router
from api.routes.chat import router as chat_router
from api.routes.search import router as search_router
from api.routes.priority import router as priority_router

# Register routers
app.include_router(upload_router)
app.include_router(chat_router)
app.include_router(search_router)
app.include_router(priority_router)

@app.get("/")
async def root():
    return {
        "status": "Online",
        "service": "ALGONOX RAG MODEL API",
        "timestamp": os.getenv("LANGCHAIN_PROJECT", "RAGINI"),
        "features": [
            "Multimodal Upload Validation",
            "Scanned OCR Document Parsing",
            "Variable-length Semantic Chunking",
            "MongoDB Atlas Dense Vector Querying",
            "Tavily & ScraperAPI Concurrent Search Portals"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    # Run development server
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
