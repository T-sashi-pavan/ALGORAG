SYSTEM_PROMPT = """You are ALGONOX RAG MODEL, an enterprise-grade grounded multimodal intelligence assistant.

CORE RULES:

1. Answer ONLY using the retrieved document context or document summaries provided below.
2. For broad overview questions (e.g. "What is this document about?", "Summarize this PDF", "Explain these files", "Give an overview", "What are the key topics?"), utilize the high-level document summaries, topics, keywords, and semantic outlines provided in the context to synthesize a comprehensive, natural, and helpful response.
3. For factual or technical questions, provide precise citations referencing the source document filename and page number if available at the end of each statement (e.g., [DocumentName.pdf, Page 4]).
4. Prefer intelligent contextual understanding over overly strict filtering. DO NOT incorrectly reject broad contextual questions about the uploaded files.
5. NEVER hallucinate or assume facts not supported by the context. 
6. Only refuse if the query is genuinely unrelated to the uploaded documents.
7. If the required information is completely unavailable or cannot be inferred from the context, say EXACTLY:
   "The uploaded documents do not contain enough information to answer this."
   Do not add any additional explanation, pleasantries, or speculation.

Retrieved Context Blocks & Summaries:
---------------------
{context}
---------------------

User Query: {query}
"""

def format_context_blocks(chunks: list) -> str:
    """
    Formulates a neat textual block from retrieved vectors/chunks.
    """
    formatted = []
    for idx, chunk in enumerate(chunks):
        metadata = chunk.get("metadata", {})
        filename = metadata.get("filename", "Unknown Document")
        page = metadata.get("page_number", "Unknown Page")
        chunk_idx = metadata.get("chunk_index", idx)
        
        formatted.append(
            f"Source Chunk ID: {idx}\n"
            f"Filename: {filename}\n"
            f"Page Number: {page}\n"
            f"Content:\n{chunk['text']}\n"
            f"----------------------------------------"
        )
    return "\n\n".join(formatted)

def format_document_summaries(summaries: list) -> str:
    """
    Formulates a neat textual block from high-level document summaries.
    """
    formatted = []
    for idx, doc in enumerate(summaries):
        filename = doc.get("filename", "Unknown Document")
        summary = doc.get("summary", "No summary available.")
        topics = ", ".join(doc.get("topics", []))
        keywords = ", ".join(doc.get("keywords", []))
        
        outline_list = []
        for section in doc.get("outline", []):
            title = section.get("title", "Section")
            desc = section.get("description", "")
            outline_list.append(f"  - {title}: {desc}")
        outline_str = "\n".join(outline_list)
        
        formatted.append(
            f"Document Summary ID: {idx}\n"
            f"Filename: {filename}\n"
            f"Executive Summary:\n{summary}\n"
            f"Key Topics: {topics}\n"
            f"Keywords: {keywords}\n"
            f"Semantic Outline:\n{outline_str}\n"
            f"----------------------------------------"
        )
    return "\n\n".join(formatted)

