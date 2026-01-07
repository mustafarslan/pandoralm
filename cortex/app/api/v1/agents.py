from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.agents.search import GoogleSearchAgent
from app.auth.keycloak import verifier
from app.services.audit_service import audit_log_background

router = APIRouter()

class AgentSearchRequest(BaseModel):
    query: str

class AgentSearchResponse(BaseModel):
    answer: str

@router.post("/search", response_model=AgentSearchResponse)
async def run_search_agent(
    request: AgentSearchRequest,
    token_payload: dict = Depends(verifier.verify_token)
):
    """
    Run the Google Search Agent (System 2 / Deep Research).
    Exposes the LangGraph-based agent.
    """
    try:
        agent = GoogleSearchAgent()
        answer = await agent.run(request.query)
        
        return AgentSearchResponse(answer=answer)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent failed: {str(e)}")


# -----------------------------------------------------------------------------
# Slack Webhook Endpoint
# -----------------------------------------------------------------------------
# Note: Slack calls this directly, so we DO NOT use verifier.verify_token.
# Instead, we verify the X-Slack-Signature header.

from fastapi import Request, BackgroundTasks
from app.agents.slack import SlackAgent

@router.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Slack Events API webhooks.
    """
    try:
        # Read body first (needed for signature verification)
        body_bytes = await request.body()
        body_str = body_bytes.decode("utf-8")
        json_data = await request.json()
        
        # 1. URL Verification (Handshake)
        if json_data.get("type") == "url_verification":
            return {"challenge": json_data.get("challenge")}
            
        # 2. Verify Signature
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")
        
        agent = SlackAgent()
        
        if not await agent.verify_signature(body_str, timestamp, signature):
            # If verification fails, return 401
            raise HTTPException(status_code=401, detail="Invalid Slack signature")
            
        # 3. Handle Event
        await agent.handle_event(json_data, background_tasks)
        
        # Immediate 200 OK for Slack
        return {"status": "ok"}
        
    except HTTPException:
        raise
    except Exception as e:
        # Log error but return 200 to prevent Slack from retrying repeatedly if it's a logic error
        # (Slack retries on 500s)
        print(f"Slack webhook error: {e}")
        return {"status": "error", "processing_failed": True}
