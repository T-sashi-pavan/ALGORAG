import os
import asyncio
import logging
import httpx
from urllib.parse import urlparse

logger = logging.getLogger("algonox.scraping")

class PortalScraper:
    def __init__(self, embedding_client=None):
        self.tavily_api_key = os.getenv("TAVILY_API_KEY", "")
        self.scraper_api_key = os.getenv("SCRAPER_API_KEY", "")
        if not self.tavily_api_key:
            logger.warning("TAVILY_API_KEY environment variable is not set. Portal searches will be unavailable.")
        if not self.scraper_api_key:
            logger.warning("SCRAPER_API_KEY environment variable is not set. Portal scrapers will fail.")
        self.embedding_client = embedding_client
        
        # Supported portals list
        self.portals = {
            "arXiv": "arxiv.org",
            "Semantic Scholar": "semanticscholar.org",
            "Internet Archive": "archive.org",
            "Open Library": "openlibrary.org",
            "DOAJ": "doaj.org",
            "PDF Drive": "pdfdrive.com",
            "PDF Search": "pdf-search-engine.com",
            "PDF Room": "pdfroom.com"
        }

    async def search_portal(self, keyword: str, portal_name: str, site_domain: str) -> dict:
        """
        Executes a targeted search on a portal domain using Tavily Search.
        """
        query = f"site:{site_domain} {keyword}"
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_api_key,
            "query": query,
            "search_depth": "advanced",
            "max_results": 3
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=15.0)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    if results:
                        # Extract the best document card
                        best_match = results[0]
                        # Scrape snippet metadata
                        snippet = best_match.get("content", "")
                        match_url = best_match.get("url", "")
                        title = best_match.get("title", f"Document from {portal_name}")
                        
                        return {
                            "portal": portal_name,
                            "title": title,
                            "url": match_url,
                            "snippet": snippet,
                            "published_date": best_match.get("published_date", "Recent"),
                            "status": "Available"
                        }
                return {
                    "portal": portal_name,
                    "title": f"No document found on {portal_name}",
                    "url": "",
                    "snippet": f"No direct matches found for keyword: {keyword}",
                    "published_date": "N/A",
                    "status": "No matches"
                }
        except Exception as e:
            logger.error(f"Error searching portal {portal_name}: {e}")
            return {
                "portal": portal_name,
                "title": f"Error loading {portal_name}",
                "url": "",
                "snippet": str(e),
                "published_date": "N/A",
                "status": "Error"
            }

    async def search_all_portals(self, keyword: str) -> list:
        """
        Searches all 8 supported portals concurrently.
        """
        tasks = []
        for portal_name, domain in self.portals.items():
            tasks.append(self.search_portal(keyword, portal_name, domain))
            
        results = await asyncio.gather(*tasks)
        
        # Rank documents semantically using our local embedding client if active
        valid_results = [r for r in results if r["url"]]
        if not valid_results:
            return results # return fallback lists
            
        if self.embedding_client:
            try:
                logger.info(f"Reranking scraped portal results using semantic similarity for keyword: '{keyword}'")
                # Embed query keyword
                query_emb = np_array = self.embedding_client.embed_query(keyword)
                
                # Embed each result snippet
                snippets = [r["title"] + " " + r["snippet"] for r in valid_results]
                doc_embs = self.embedding_client.embed_documents(snippets)
                
                import numpy as np
                q_vec = np.array(query_emb)
                q_norm = np.linalg.norm(q_vec)
                
                for idx, r in enumerate(valid_results):
                    d_vec = np.array(doc_embs[idx])
                    d_norm = np.linalg.norm(d_vec)
                    if d_norm == 0 or q_norm == 0:
                        score = 0.0
                    else:
                        score = float(np.dot(q_vec, d_vec) / (q_norm * d_norm))
                    r["relevance_score"] = round(score * 100, 2)
                    
                # Sort by score descending
                valid_results.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)
                
                # Reconstruct full list (ranked ones first)
                unmatched = [r for r in results if not r["url"]]
                for r in unmatched:
                    r["relevance_score"] = 0.0
                return valid_results + unmatched
                
            except Exception as e:
                logger.error(f"Error reranking portal results semantically: {e}")
                
        # If no embedding client is present, return results directly
        return results

    async def scrape_document_content(self, url: str) -> str:
        """
        Scrapes detailed content from a URL via ScraperAPI rotation proxies.
        """
        if not url:
            return ""
            
        scraper_url = "http://api.scraperapi.com"
        params = {
            "api_key": self.scraper_api_key,
            "url": url,
            "render": "true" # Enables full JS rendering if using Playwright equivalents in ScraperAPI
        }
        
        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"Scraping document content from URL {url} via ScraperAPI...")
                response = await client.get(scraper_url, params=params, timeout=30.0)
                if response.status_code == 200:
                    # Parse text from HTML
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    # Remove script/style blocks
                    for script in soup(["script", "style"]):
                        script.decompose()
                        
                    text = soup.get_text(separator=" ")
                    # Cleanup whitespace
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    cleaned_text = "\n".join(chunk for chunk in chunks if chunk)
                    return cleaned_text
                    
                logger.warning(f"ScraperAPI returned status code: {response.status_code}")
                return ""
        except Exception as e:
            logger.error(f"Failed to scrape document content: {e}")
            return ""
