import logging
import time
from typing import Dict, Any, Optional

from app.core.config import settings
from app.services.router import get_intent_classifier, IntentType
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

class SlackAgent:
    """
    Agent for handling Slack events and bi-directional communication.
    """
    
    def __init__(self):
        try:
            from slack_sdk.web.async_client import AsyncWebClient
            from slack_sdk.signature import SignatureVerifier
            
            self.client = AsyncWebClient(token=settings.SLACK_BOT_TOKEN)
            self.verifier = SignatureVerifier(settings.SLACK_SIGNING_SECRET)
            self._available = True
        except ImportError:
            logger.warning("slack_sdk not installed. Slack Agent disabled.")
            self._available = False
        except Exception as e:
            logger.error(f"Failed to initialize Slack Agent: {e}")
            self._available = False

    def is_available(self) -> bool:
        return self._available and bool(settings.SLACK_BOT_TOKEN) and bool(settings.SLACK_SIGNING_SECRET)

    async def verify_signature(self, request_body: str, timestamp: str, signature: str) -> bool:
        """Verify Slack request signature."""
        if not self.is_available():
            return False
            
        try:
            return self.verifier.is_valid(
                body=request_body,
                timestamp=timestamp,
                signature=signature
            )
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

    async def handle_event(self, event_data: Dict[str, Any], background_tasks=None):
        """
        Handle incoming Slack event.
        Returns immediately to acknowledge Slack (within 3s), queues processing.
        """
        if not self.is_available():
            logger.warning("Slack Agent received event but is not configured.")
            return
            
        event = event_data.get("event", {})
        event_type = event.get("type")
        
        # Ignore bot messages to prevent loops
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return
            
        if event_type in ["message", "app_mention"]:
            # Queue background processing
            if background_tasks:
                background_tasks.add_task(self.process_and_reply, event)
            else:
                # Fallback if no background_tasks provided (shouldn't happen in API)
                await self.process_and_reply(event)

    async def process_and_reply(self, event: Dict[str, Any]):
        """
        Process message and send reply (Background Task).
        """
        channel_id = event.get("channel")
        user_id = event.get("user")
        text = event.get("text", "")
        # Remove mention if applicable e.g. <@U123>
        import re
        text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
        
        logger.info(f"Processing Slack message from {user_id}: {text}")
        
        try:
            # 1. Classify Intent / Route
            # Use Router for now to decide logic.
            # Simplified: Just chat response using heavy model (System 2) or generic chat.
            
            # Simple direct response logic for V1:
            
            # Create a simple "System 1 vs System 2" flow for Slack
            response_text = ""
            
            # Determine intent (optional, for now strictly chat)
            # intent_result = await get_intent_classifier().classify(text)
            
            # Use the LLM logic from GraphRAG reasoning or just simplified chat?
            # Let's reuse the router's chat logic if possible, or build a simple message chain.
            # For simplicity in V1: Reuse simple LLM wrapper or router.
            
            # Construct a response
            # Using Cognitive Router directly requires document context.
            # Here we act as a "Chatbot".
            
            response_text = await self._generate_response(text)
            
            # Reply to Thread if it exists, otherwise channel
            thread_ts = event.get("thread_ts") or event.get("ts")
            
            await self.client.chat_postMessage(
                channel=channel_id,
                text=response_text,
                thread_ts=thread_ts
            )
            
        except Exception as e:
            logger.error(f"Error processing Slack message: {e}")
            # Optional: Error reply?
            
    async def _generate_response(self, query: str) -> str:
        """Generate response using the configured Solver model."""
        # Use existing LLM infrastructure
        # Currently we can instantiate ChatOpenAI or Ollama based on config
        try:
            from app.core.config import settings
            
            if settings.OPENAI_API_KEY:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(model=settings.DEFAULT_LLM_MODEL, api_key=settings.OPENAI_API_KEY)
            else:
                from langchain_community.chat_models import ChatOllama
                llm = ChatOllama(model=settings.LLM_SOLVER_MODEL, base_url=settings.LLM_SOLVER_API_BASE)
                
            resp = await llm.ainvoke([HumanMessage(content=query)])
            return resp.content
            
        except ImportError:
            return "Error: LLM dependencies missing."
        except Exception as e:
            return f"I encountered an error processing that: {str(e)}"
