import os
import uuid
import datetime
import logging
import asyncio
import httpx
import smtplib
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional

# Import dependencies
from scraping.engine import PortalScraper
from embeddings.bge import BGEEmbeddings
from vectorstore.mongodb import MongoDBVectorStore

logger = logging.getLogger("algonox.routes.priority")
router = APIRouter(prefix="/api/priority", tags=["priority"])

# Request-Response Models
class PriorityRequest(BaseModel):
    keyword: str

class PriorityDocumentCard(BaseModel):
    document_id: str
    priority_rank: int
    filename: str
    portal: str
    relevance_score: float
    published_date: str
    ai_summary: str
    keywords_matched: List[str]
    confidence_score: float
    why_selected: str
    url: str
    status: str
    
    # Sub-scores
    semantic_similarity: float
    keyword_match: float
    recency: float
    source_quality: float
    document_completeness: float
    final_score: float

class EmailDraftRequest(BaseModel):
    document_ids: List[str]
    keyword: str

class SendEmailRequest(BaseModel):
    document_ids: List[str]
    recipient_email: str
    subject: str
    body: str
    custom_message: Optional[str] = ""

class ReviewActionRequest(BaseModel):
    document_id: str
    action_type: str  # override_rank, previewed, compared, selected
    metadata: Optional[dict] = None

# Initialize instances
try:
    embedding_client = BGEEmbeddings()
    scraper = PortalScraper(embedding_client=embedding_client)
    vectorstore = MongoDBVectorStore()
except Exception as e:
    logger.error(f"Failed to load priority dependencies: {e}")

# Helper to generate AI enrichment concurrently
async def enrich_document_details(card: dict, keyword: str) -> dict:
    """
    Queries Groq to concurrently generate:
    - a concise executive AI summary
    - precise keywords matched
    - a logical, compliance-ready semantic reason for selecting this document.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        # Fallback details if Groq is not configured
        return {
            "ai_summary": card.get("snippet", "Detailed summary is currently being parsed."),
            "keywords_matched": [keyword.split()[0]] if keyword.split() else ["Data"],
            "why_selected": "This document matches the compliance and relevance constraints of the portal query."
        }

    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""You are an enterprise document intelligence triage assistant.
Analyze this retrieved search result from portal "{card['portal']}":
Title: "{card['title']}"
Snippet: "{card['snippet']}"
Published: "{card['published_date']}"

Based on the original search keyword "{keyword}", generate:
1. A concise, highly professional AI Summary (exactly 1-2 paragraphs).
2. A list of 3-6 key terms/tags directly matched.
3. A brief, logical explanation (1-2 sentences) of exactly why this document is highly relevant to "{keyword}" (recruitment, research, or compliance context).

You MUST respond strictly with a valid JSON matching this schema:
{{
  "ai_summary": "Professional executive summary...",
  "keywords_matched": ["keyword1", "keyword2", "keyword3"],
  "why_selected": "This document was selected because it contains..."
}}
Return ONLY the raw JSON object. Do not include any markdown fences or surrounding chat comments.
"""
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                import json
                parsed = json.loads(data["choices"][0]["message"]["content"].strip())
                return {
                    "ai_summary": parsed.get("ai_summary", card.get("snippet", "")),
                    "keywords_matched": parsed.get("keywords_matched", [keyword]),
                    "why_selected": parsed.get("why_selected", "Matches search query constraints.")
                }
    except Exception as e:
        logger.error(f"Failed to enrich document details via Groq: {e}")

    return {
        "ai_summary": card.get("snippet", ""),
        "keywords_matched": [keyword],
        "why_selected": "Matches requested compliance and research themes."
    }

@router.post("/rank", response_model=List[PriorityDocumentCard])
async def calculate_priority_rankings(request: PriorityRequest):
    """
    Main priority triage gateway.
    1. Scrapes concurrently across all 8 portals.
    2. Filters valid document matches.
    3. Calculates exact weighted PRIORITY_SCORE.
    4. Enriches top results using Groq concurrently.
    5. Saves priority structures in MongoDB logs.
    """
    keyword = request.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    try:
        # 1. Scrape all portals
        logger.info(f"Priority rank scraping triggered for: '{keyword}'")
        raw_results = await scraper.search_all_portals(keyword)
        
        # 2. Filter down to valid documents with direct URLs
        valid_docs = [r for r in raw_results if r.get("url")]
        
        scored_docs = []
        
        # 3. Calculate mathematically precise priority scores
        keyword_tokens = [t.lower() for t in keyword.split() if len(t) > 2]
        
        for item in valid_docs:
            semantic_similarity = float(item.get("relevance_score", 0.0))
            
            # Keyword match intersection density
            match_count = 0
            text_pool = (item["title"] + " " + item["snippet"]).lower()
            for token in keyword_tokens:
                if token in text_pool:
                    match_count += 1
            keyword_match = float(match_count / len(keyword_tokens) * 100.0) if keyword_tokens else 60.0
            
            # Recency factor decays
            recency = 50.0
            pub_date = item.get("published_date", "")
            if "recent" in pub_date.lower() or "2026" in pub_date:
                recency = 100.0
            elif "2025" in pub_date:
                recency = 95.0
            elif "2024" in pub_date:
                recency = 90.0
            elif "2023" in pub_date:
                recency = 80.0
            elif "2022" in pub_date:
                recency = 70.0
            elif any(yr in pub_date for yr in ["2021", "2020", "2019"]):
                recency = 60.0
                
            # Domain authority quality trust values
            portal = item.get("portal", "")
            source_quality = 65.0
            if portal in ("arXiv", "Semantic Scholar"):
                source_quality = 95.0
            elif portal == "DOAJ":
                source_quality = 90.0
            elif portal in ("Internet Archive", "Open Library"):
                source_quality = 85.0
            elif portal == "PDF Drive":
                source_quality = 70.0
                
            # Structural Completeness
            document_completeness = 0.0
            if item.get("url"):
                document_completeness += 40.0
            if item.get("title") and "No document found" not in item["title"]:
                document_completeness += 30.0
            if item.get("snippet") and "No direct matches found" not in item["snippet"]:
                document_completeness += 20.0
            if item.get("published_date") and item["published_date"] != "N/A":
                document_completeness += 10.0
                
            # Apply exact priority formula
            final_score = (
                0.40 * semantic_similarity +
                0.25 * keyword_match +
                0.20 * recency +
                0.10 * source_quality +
                0.05 * document_completeness
            )
            
            scored_docs.append({
                "item": item,
                "sub_scores": {
                    "semantic_similarity": round(semantic_similarity, 2),
                    "keyword_match": round(keyword_match, 2),
                    "recency": round(recency, 2),
                    "source_quality": round(source_quality, 2),
                    "document_completeness": round(document_completeness, 2),
                    "final_score": round(final_score, 2)
                }
            })
            
        # Sort documents by final priority score descending
        scored_docs.sort(key=lambda x: x["sub_scores"]["final_score"], reverse=True)
        
        # Take top 5 candidates for dynamic AI enrichment to remain lightning-fast
        candidates = scored_docs[:5]
        
        enrichment_tasks = [
            enrich_document_details(cand["item"], keyword) for cand in candidates
        ]
        enrichments = await asyncio.gather(*enrichment_tasks)
        
        priority_cards = []
        timestamp = datetime.datetime.utcnow().isoformat()
        
        for idx, cand in enumerate(candidates):
            item = cand["item"]
            scores = cand["sub_scores"]
            enrich = enrichments[idx]
            
            doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, item["url"]))
            
            card = PriorityDocumentCard(
                document_id=doc_id,
                priority_rank=idx + 1,
                filename=item["title"] if item["title"].lower().endswith(".pdf") else f"{item['title'][:40]}.pdf",
                portal=item["portal"],
                relevance_score=scores["final_score"],
                published_date=item["published_date"],
                ai_summary=enrich["ai_summary"],
                keywords_matched=enrich["keywords_matched"],
                confidence_score=scores["semantic_similarity"],
                why_selected=enrich["why_selected"],
                url=item["url"],
                status=item["status"],
                semantic_similarity=scores["semantic_similarity"],
                keyword_match=scores["keyword_match"],
                recency=scores["recency"],
                source_quality=scores["source_quality"],
                document_completeness=scores["document_completeness"],
                final_score=scores["final_score"]
            )
            priority_cards.append(card)
            
            # Persist individual document details in priority_documents MongoDB collection
            vectorstore.save_priority_document(card.dict())
            
        # Log rank calculation event in MongoDB document_rankings collection
        ranking_log = {
            "query_keyword": keyword,
            "calculated_at": timestamp,
            "total_ranked": len(priority_cards),
            "documents": [c.document_id for c in priority_cards]
        }
        vectorstore.log_document_ranking(ranking_log)
        
        return priority_cards
    except Exception as e:
        logger.error(f"Priority rankings calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-email")
async def generate_hr_email_draft(request: EmailDraftRequest):
    """
    Dynamically drafts a custom recruitment/compliance style email using Groq.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        return {
            "subject": f"High Relevance Document Retrieved: Action Required",
            "body": "Hello HR Team,\n\nThe ALGONOX RAG MODEL identified documents that strongly match the requested search profiles."
        }

    # Fetch document metadata from DB
    docs = []
    for doc_id in request.document_ids:
        doc = vectorstore.priority_documents.find_one({"document_id": doc_id})
        if doc:
            docs.append(doc)
            
    if not docs:
        raise HTTPException(status_code=404, detail="No selected documents found in priority database.")
        
    doc_details_str = ""
    for idx, d in enumerate(docs):
        doc_details_str += f"""
Document #{idx+1}:
- Name: {d.get('filename')}
- Portal: {d.get('portal')}
- Priority Score: {d.get('relevance_score')}%
- Summary: {d.get('ai_summary')}
- Why Selected: {d.get('why_selected')}
"""

    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""You are a professional corporate recruiter and document compliance triage agent.
Draft a highly professional, concise, and intelligent executive HR review email for the following selected documents:
{doc_details_str}

The email is sent on behalf of "ALGONOX RAG MODEL".
It must contain:
1. A clear corporate review Subject line.
2. A formal greeting to the HR/Compliance team.
3. A structured, easy-to-read layout outlining the selected files, their relevance scores, matched tags, and exact AI reasons for prioritization.
4. An intelligent executive recruitment/compliance styled summary.

You MUST respond strictly with a valid JSON matching this schema:
{{
  "subject": "Professional email subject line...",
  "body": "Complete email body string with line breaks..."
}}
Output ONLY the raw JSON object. Do not format with markdown or surround with chat notes.
"""
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=12.0
            )
            if response.status_code == 200:
                import json
                data = response.json()
                parsed = json.loads(data["choices"][0]["message"]["content"].strip())
                return parsed
    except Exception as e:
        logger.error(f"Email drafting request failed: {e}")

    # Fallback template
    doc_name = docs[0].get("filename", "Document.pdf")
    portal_name = docs[0].get("portal", "Public Portal")
    relevance_score = docs[0].get("relevance_score", 90.0)
    keywords = ", ".join(docs[0].get("keywords_matched", [request.keyword]))
    summary = docs[0].get("ai_summary", "Summary matches selected criteria.")
    why = docs[0].get("why_selected", "Strong semantic fit.")

    subject = f"High Relevance Document Retrieved from {portal_name}"
    body = f"""Hello HR Team,

The ALGONOX RAG MODEL system identified a highly relevant document based on the requested search criteria.

Document Details:
- Document Name: {doc_name}
- Portal Source: {portal_name}
- AI Relevance Score: {relevance_score}%
- Keywords Matched: {keywords}
- Retrieval Date: {datetime.datetime.utcnow().strftime('%Y-%m-%d')}

AI Summary:
{summary}

Reason For Selection:
{why}

The document is attached for review.

Regards,
ALGONOX RAG MODEL"""

    return {"subject": subject, "body": body}

def send_email_in_background(
    delivery_id: str,
    recipient_email: str,
    subject: str,
    body: str,
    doc_urls: List[str],
    filenames: List[str]
):
    """
    Downloads documents in a separate background thread, wraps them inside a MIME message,
    and dispatches via SMTP or gracefully logs to Mock persistence mode.
    """
    logger.info(f"Background email delivery triggered (Delivery ID: {delivery_id})")
    vectorstore.update_delivery_status(delivery_id, "Sending")

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER") or os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASS") or os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", "algonox-rag@enterprise.com")

    attachments = []
    
    # 1. Download document attachments in background thread
    for idx, url in enumerate(doc_urls):
        name = filenames[idx]
        try:
            logger.info(f"Downloading attachment for email: {name} from {url}")
            headers = {"User-Agent": "Mozilla/5.0"}
            with httpx.Client(follow_redirects=True, timeout=30.0) as client:
                res = client.get(url, headers=headers)
                if res.status_code == 200:
                    # Write attachment to temp file
                    temp_file = tempfile.NamedTemporaryFile(delete=False)
                    temp_file.write(res.content)
                    temp_file.close()
                    attachments.append((temp_file.name, name))
                    logger.info(f"Successfully downloaded attachment: {name}")
                else:
                    logger.warning(f"Download returned status code {res.status_code} for: {name}")
        except Exception as dl_err:
            logger.error(f"Failed downloading attachment {name}: {dl_err}")

    # 2. Check if SMTP configuration exists
    if smtp_host and smtp_port:
        try:
            # Construct standard MIME Email
            msg = MIMEMultipart()
            msg["From"] = smtp_from
            msg["To"] = recipient_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            # Attach standard file buffers
            for path, name in attachments:
                if os.path.exists(path):
                    with open(path, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename= {name}",
                        )
                        msg.attach(part)

            # Send via SMTP connection
            server = smtplib.SMTP(smtp_host, int(smtp_port))
            server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
            
            vectorstore.update_delivery_status(delivery_id, "Delivered")
            logger.info(f"Email successfully delivered via SMTP to {recipient_email}")
        except Exception as smtp_ex:
            logger.error(f"SMTP relay failed: {smtp_ex}")
            vectorstore.update_delivery_status(delivery_id, "Failed", str(smtp_ex))
    else:
        # Graceful fallback to Mock Persistence Mode
        logger.info("No SMTP configuration found in environment. Running inside MOCK persisting mode...")
        # Artificially wait 2 seconds to simulate network latency
        import time
        time.sleep(2.0)
        vectorstore.update_delivery_status(delivery_id, "Mock-Delivered")
        logger.info(f"Email details staged inside mock database collection for recipient: {recipient_email}")

    # Clean up temp file shims
    for path, _ in attachments:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as clean_ex:
                logger.error(f"Failed removing temp attachment shim: {clean_ex}")

@router.post("/send-email")
async def send_documents_to_hr(request: SendEmailRequest, background_tasks: BackgroundTasks):
    """
    Dispatches document summaries and attachments to the HR department.
    Saves initial status log in MongoDB and launches background mailer threads.
    """
    recipient = request.recipient_email.strip()
    if not recipient:
        raise HTTPException(status_code=400, detail="Recipient email is required.")

    # Retrieve selected documents from MongoDB priority center collection
    docs = []
    doc_urls = []
    filenames = []
    
    for doc_id in request.document_ids:
        doc = vectorstore.priority_documents.find_one({"document_id": doc_id})
        if doc:
            docs.append(doc)
            doc_urls.append(doc["url"])
            filenames.append(doc["filename"])
            
    if not docs:
        raise HTTPException(status_code=404, detail="No selected documents resolved in priority center database.")

    delivery_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat()
    
    email_body = request.body
    if request.custom_message:
        email_body = f"Operator Note:\n{request.custom_message}\n\n=========================================\n\n" + email_body

    # 1. Create immediate Transaction status record in MongoDB
    delivery_record = {
        "_id": delivery_id,
        "delivery_id": delivery_id,
        "recipient": recipient,
        "subject": request.subject,
        "status": "Queued",
        "created_at": timestamp,
        "updated_at": timestamp
    }
    vectorstore.log_delivery_status(delivery_record)

    # 2. Log full transaction inside email logs collection
    email_log = {
        "_id": delivery_id,
        "delivery_id": delivery_id,
        "recipient": recipient,
        "subject": request.subject,
        "body": email_body,
        "document_ids": request.document_ids,
        "filenames": filenames,
        "sent_at": timestamp,
        "status": "Queued"
    }
    vectorstore.log_email(email_log)

    # 3. Dispatch secure background task
    background_tasks.add_task(
        send_email_in_background,
        delivery_id,
        recipient,
        request.subject,
        email_body,
        doc_urls,
        filenames
    )

    return {
        "message": "Email delivery queue transaction initialized.",
        "delivery_id": delivery_id,
        "status": "Queued"
    }

@router.get("/email-logs")
async def get_email_logs():
    """
    Fetches sent email logs for history panels.
    """
    logs = vectorstore.get_email_logs()
    return {"logs": logs}

@router.post("/review-action")
async def log_user_review_action(request: ReviewActionRequest):
    """
    Logs document triage review interactions (rank override, expand summary, inline compare, etc.)
    """
    action_doc = {
        "document_id": request.document_id,
        "action_type": request.action_type,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "metadata": request.metadata or {}
    }
    vectorstore.log_review_action(action_doc)
    return {"message": "Review triage action recorded successfully."}
