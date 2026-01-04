from celery import shared_task
from playwright.sync_api import sync_playwright
import trafilatura
from app.workers.celery_app import celery_app
# from app.services.ingest import ingest_service # Future integration

@celery_app.task(name="scraper.perform_scrape_task", queue="research")
def perform_scrape_task(url: str, layer_id: str = "user_private"):
    """
    Scrape a URL using Playwright (in a worker) and convert to Markdown.
    Then trigger ingestion (Vector + Graph).
    """
    html_content = ""
    title = ""
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            html_content = page.content()
            title = page.title()
            browser.close()
            
        # Convert to Markdown
        markdown_content = trafilatura.extract(html_content) or ""
        
        # TODO: Trigger ingestion pipeline here
        # For now, we just return the result which might be picked up by the caller
        # In a real event-driven flow, we would call:
        # ingest_service.process_web_content(doc_id, markdown, layer_id)
        
        return {
            "status": "success",
            "url": url,
            "title": title,
            "content": markdown_content,
            "layer_id": layer_id
        }

    except Exception as e:
        return {
            "status": "failed",
            "url": url,
            "error": str(e)
        }
