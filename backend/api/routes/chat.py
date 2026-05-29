import os
import logging
import datetime
import uuid
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# Import pipelines
from vectorstore.mongodb import MongoDBVectorStore
from embeddings.bge import BGEEmbeddings
from reranker.bge_rerank import BGEReranker
from prompts.system import SYSTEM_PROMPT, format_context_blocks, format_document_summaries

logger = logging.getLogger("algonox.routes.chat")
router = APIRouter(prefix="/api/chat", tags=["chat"])

# Request-Response Models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    document_ids: Optional[List[str]] = None
    similarity_threshold: Optional[float] = 0.40
    session_id: Optional[str] = None

class Citation(BaseModel):
    filename: str
    page_number: Optional[int] = None
    chunk_index: int
    text: str

class ChatResponse(BaseModel):
    answer: str
    confidence_score: float
    citations: List[Citation]
    grounded: bool

# Stateful Sessions Request-Response Models
class CreateSessionRequest(BaseModel):
    title: str
    document_ids: Optional[List[str]] = None

class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    pinned: Optional[bool] = None
    document_ids: Optional[List[str]] = None

# Instances
try:
    vectorstore = MongoDBVectorStore()
    embedding_client = BGEEmbeddings()
    reranker = BGEReranker()
except Exception as e:
    logger.error(f"Failed to initialize chat route dependencies: {e}")

def classify_query(query: str) -> str:
    """
    Lightweight, high-speed LLM classifier to determine query intent.
    Routes queries to broad, general, or ultra-factual retrieval filters.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        return "FACTUAL_QUERY"
    
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""You are an intelligent query intent classifier for a document RAG search system.
Classify the following user query into exactly one of these categories:
1. DOCUMENT_OVERVIEW: Broad high-level questions about the document's overall theme, purpose, structure, or what it is about (e.g. "what is this document about?", "explain this PDF", "tell me about these files").
2. SUMMARY_REQUEST: Requests to summarize the document, write executive summaries, list key takeaways or main highlights (e.g. "summarize this PDF", "give me a summary").
3. CROSS_DOCUMENT_QUERY: Queries asking to combine, compare, or retrieve across multiple files.
4. COMPARISON_QUERY: Queries that ask to compare different parts of the document or multiple files.
5. FACTUAL_QUERY: Specific technical questions searching for exact dates, numbers, names, parameters, compliance fields, formulas, or strict detailed facts (e.g. "what is the revenue on page 5?", "when was this signed?", "what is the temperature limit?").
6. GENERAL_CONTEXT_QUERY: Conversational follow-ups, general context questions, or generic chat.

Return ONLY the single category name in uppercase, without any formatting, markdown, or other text.
Query: "{query}"
Category:"""

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 10
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=5.0
            )
            if response.status_code == 200:
                data = response.json()
                category = data["choices"][0]["message"]["content"].strip().upper()
                valid_categories = {"DOCUMENT_OVERVIEW", "SUMMARY_REQUEST", "CROSS_DOCUMENT_QUERY", "COMPARISON_QUERY", "FACTUAL_QUERY", "GENERAL_CONTEXT_QUERY"}
                for cat in valid_categories:
                    if cat in category:
                        return cat
    except Exception as e:
        logger.error(f"Failed to classify query: {e}")
        
    return "FACTUAL_QUERY"

@router.post("", response_model=ChatResponse)
async def grounded_chat(request: ChatRequest):
    """
    Enterprise grounded chat endpoint.
    Applies Query Classification -> Three-Layer Retrieval -> LLM Grounding with Citations.
    Synchronizes sessions and logs automatically to MongoDB.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Empty conversation transcript.")
        
    query = request.messages[-1].content
    
    # 1. Save user message to persistent DB if session is active
    if request.session_id:
        user_msg = {
            "session_id": request.session_id,
            "role": "user",
            "content": query,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        vectorstore.insert_message(user_msg)

    # 2. Scope selection: resolve document selection from request or active session metadata
    document_ids = request.document_ids
    if not document_ids and request.session_id:
        session = vectorstore.get_chat_session(request.session_id)
        if session:
            document_ids = session.get("document_ids", [])

    # 3. Classify User Question
    category = classify_query(query)
    logger.info(f"Classified user query '{query}' as '{category}'")

    # 4. Three-Layer Retrieval Dispatcher
    retrieved_chunks = []
    valid_chunks = []
    confidence_score = 0.0
    citations_list = []
    context_str = ""
    grounded = True

    if category in ("DOCUMENT_OVERVIEW", "SUMMARY_REQUEST", "CROSS_DOCUMENT_QUERY", "COMPARISON_QUERY") and document_ids:
        # LAYER 1: Broad Document Summarization Level Retrieval
        summaries = vectorstore.get_summaries(document_ids)
        context_str = format_document_summaries(summaries)
        
        # Also fetch top chunks with ultra low similarity threshold for supplemental context
        try:
            query_vector = embedding_client.embed_query(query)
            retrieved_chunks = vectorstore.search(query_vector=query_vector, limit=6, document_ids=document_ids)
            if retrieved_chunks:
                ranked_chunks = reranker.rerank(query=query, documents=retrieved_chunks, top_k=3)
                valid_chunks = ranked_chunks
                context_str += "\n\nSupplementary Details:\n" + format_context_blocks(valid_chunks)
        except Exception as ex:
            logger.warning(f"Failed to fetch auxiliary chunks for broad query: {ex}")
        
        confidence_score = 0.90  # Default high confidence score for global document summary contexts
    else:
        # LAYER 2 or 3: Dense Chunk level / Factual Precision Retrieval
        try:
            query_vector = embedding_client.embed_query(query)
            retrieved_chunks = vectorstore.search(query_vector=query_vector, limit=12, document_ids=document_ids)
        except Exception as e:
            logger.error(f"Embedding query failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to encode user search query.")

        if retrieved_chunks:
            # Rerank retrieved candidate nodes using BAAI/bge-reranker-base
            ranked_chunks = reranker.rerank(query=query, documents=retrieved_chunks, top_k=4)
            
            # Select adaptive similarity thresholds based on query classification
            threshold = request.similarity_threshold or 0.40
            if category == "FACTUAL_QUERY":
                threshold = 0.50  # Enforce strict compliance factual checks
            elif category == "GENERAL_CONTEXT_QUERY":
                threshold = 0.25  # Allow relaxed follow-ups
                
            total_score = 0.0
            for chunk in ranked_chunks:
                score = chunk.get("rerank_score", chunk.get("score", 0.0))
                if score >= threshold:
                    valid_chunks.append(chunk)
                    total_score += score
                    
            if valid_chunks:
                confidence_score = round(total_score / len(valid_chunks), 2)
                context_str = format_context_blocks(valid_chunks)
        
        # BALANCED GROUNDING FALLBACK:
        if not valid_chunks:
            if document_ids:
                # If factual query failed but document is selected, fallback to Global summaries
                summaries = vectorstore.get_summaries(document_ids)
                if summaries:
                    logger.info("Factual chunks fell below strict threshold. Falling back to global summaries to avoid over-rejections.")
                    context_str = format_document_summaries(summaries)
                    confidence_score = 0.40
                else:
                    grounded = False
            else:
                grounded = False

    # 5. Formulate Grounded response
    if not grounded or not context_str.strip():
        answer_text = "The uploaded documents do not contain enough information to answer this."
        confidence_score = 0.0
        grounded = False
    else:
        formatted_prompt = SYSTEM_PROMPT.format(context=context_str, query=query)
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured on the backend server.")

        messages_payload = []
        
        # Prepend conversation history (loaded from DB or requested)
        if request.session_id:
            history = vectorstore.get_messages(request.session_id)
            # Exclude current query which was just inserted
            for msg in history[:-1]:
                messages_payload.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        else:
            for msg in request.messages[:-1]:
                messages_payload.append({
                    "role": msg.role,
                    "content": msg.content
                })
                
        messages_payload.append({
            "role": "user",
            "content": formatted_prompt
        })

        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": os.getenv("MODEL_NAME", "llama-3.3-70b-versatile"),
            "messages": messages_payload,
            "temperature": float(os.getenv("TEMPERATURE", 0.0)),
            "top_p": float(os.getenv("TOP_P", 0.1)),
            "max_tokens": 1024
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=45.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Groq API returned error status: {response.status_code}. Response: {response.text}")
                    raise HTTPException(status_code=502, detail="Error communicating with LLM generation engine.")
                    
                data = response.json()
                answer_text = data["choices"][0]["message"]["content"].strip()
                
                # Hallucination prevention trigger: check if the model itself returns a fallback refusal
                if "do not contain enough information to answer" in answer_text.lower() or "not contain this information" in answer_text.lower():
                    grounded = False

                # Extract Citations
                for chunk in valid_chunks:
                    meta = chunk.get("metadata", {})
                    citations_list.append(Citation(
                        filename=meta.get("filename", "Unknown"),
                        page_number=meta.get("page_number"),
                        chunk_index=meta.get("chunk_index", 0),
                        text=chunk["text"][:300] + "..."
                    ))
        except httpx.RequestError as exc:
            logger.error(f"HTTP connection to Groq API failed: {exc}")
            raise HTTPException(status_code=503, detail="Grounded Chat LLM service currently offline.")
        except Exception as e:
            logger.error(f"Error formulating chat response: {e}")
            raise HTTPException(status_code=500, detail="Internal chat pipeline failure.")

    # 6. Save assistant message bubble to DB if session is active
    if request.session_id:
        assistant_msg = {
            "session_id": request.session_id,
            "role": "assistant",
            "content": answer_text,
            "confidence_score": confidence_score,
            "citations": [c.dict() for c in citations_list],
            "grounded": grounded,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        vectorstore.insert_message(assistant_msg)

    return ChatResponse(
        answer=answer_text,
        confidence_score=confidence_score,
        citations=citations_list,
        grounded=grounded
    )

# --- Stateful CRUD Chat Session Endpoints ---

@router.post("/sessions")
async def create_session(request: CreateSessionRequest):
    """
    Creates a new stateful conversation session.
    """
    session_id = str(uuid.uuid4())
    session = vectorstore.create_chat_session(session_id, request.title, request.document_ids)
    if not session:
        raise HTTPException(status_code=500, detail="Failed to create chat session.")
    return {"message": "Chat session created successfully.", "data": session}

@router.get("/sessions")
async def list_sessions():
    """
    Lists all stored chat sessions, sorted by pin and update time.
    """
    sessions = vectorstore.get_chat_sessions()
    return {"sessions": sessions}

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """
    Retrieves metadata of a single chat session.
    """
    session = vectorstore.get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return {"session": session}

@router.put("/sessions/{session_id}")
async def update_session(session_id: str, request: UpdateSessionRequest):
    """
    Updates session settings (rename, pin state, active document ids).
    """
    updated = vectorstore.update_chat_session(
        session_id, 
        title=request.title, 
        pinned=request.pinned, 
        document_ids=request.document_ids
    )
    if not updated:
        # Check if session exists
        session = vectorstore.get_chat_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found.")
    return {"message": "Chat session updated successfully."}

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Deletes the session and cleans up nested thread messages.
    """
    deleted = vectorstore.delete_chat_session(session_id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete chat session.")
    return {"message": "Chat session deleted successfully."}

@router.get("/sessions/{session_id}/messages")
async def list_messages(session_id: str):
    """
    Retrieves the chronological chat transcript (messages thread) for a session.
    """
    # Verify session exists
    session = vectorstore.get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
        
    messages = vectorstore.get_messages(session_id)
    # Serialize ObjectId to str
    for msg in messages:
        if "_id" in msg:
            msg["_id"] = str(msg["_id"])
    return {"messages": messages}

