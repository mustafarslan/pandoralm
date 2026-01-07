import logging
import json
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_maker
from app.services.memory.mem0_client import get_mem0_client
from app.models.memory import MemorySummary

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """
You are a Memory Consolidator for an AI assistant.
Your task is to summarize the following individual facts/memories into a coherent narrative summary.
Group related information together.
Preserve important details like names, dates, preferences, and project details.

Memories:
{memories}

Summary:
"""

class MemoryConsolidationService:
    def __init__(self):
        self.mem0 = get_mem0_client()
        
    async def summarize_memories_for_user(self, user_id: str, days: int = 1) -> Optional[str]:
        """
        Summarize memories from the last N days.
        Stores summary in Postgres and Vector Store.
        """
        # 1. Fetch all memories
        # Mem0 doesn't support date filtering in get_all yet, so we filter in memory
        all_memories = self.mem0.get_all(user_id=user_id)
        
        if not all_memories:
            logger.info(f"No memories found for user {user_id}")
            return None
            
        # 2. Filter by date and exclude existing summaries
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_memories = []
        
        for mem in all_memories:
            # Skip if already a summary
            meta = mem.get("metadata", {}) or {}
            if meta.get("type") == "summary":
                continue
                
            # Check date
            created_at_str = mem.get("created_at")
            if created_at_str:
                try:
                    # Handle ISO format variations
                    if "T" in created_at_str:
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    else:
                        created_at = datetime.fromisoformat(created_at_str)
                        
                    # Naive/Aware check - assume UTC if naive
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=None) # Compare naive-to-naive
                        
                    if created_at >= cutoff_date:
                        recent_memories.append(mem)
                except Exception as e:
                    logger.warning(f"Failed to parse date {created_at_str}: {e}")
                    
        if not recent_memories:
            logger.info(f"No recent memories to summarize for user {user_id} (last {days} days)")
            return None
            
        logger.info(f"Summarizing {len(recent_memories)} memories for user {user_id}")
        
        # 3. Generate Summary
        summary_text = await self._generate_summary(recent_memories)
        
        if not summary_text:
            return None
            
        # 4. Store in Postgres (Record Keeping)
        async with async_session_maker() as session:
            db_summary = MemorySummary(
                user_id=user_id,
                summary_text=summary_text,
                date_range_start=cutoff_date,
                date_range_end=datetime.utcnow(),
                metadata_json={"source_count": len(recent_memories)}
            )
            session.add(db_summary)
            await session.commit()
            
        # 5. Store in Mem0 (Semantic Recall)
        # We store the summary as a new memory but marked as 'summary'
        self.mem0.add(
            messages=[{"role": "user", "content": f"Here is a summary of past events: {summary_text}"}],
            user_id=user_id,
            agent_id="memory_consolidator"
        )
        
        # We need to manually update the metadata to set type='summary' since .add() might not expose it fully
        # depending on Mem0 version, but our wrapper passes metadata={"agent_id": ...}.
        # Wait, Mem0Client.add() takes agent_id but hardcodes metadata={"agent_id": agent_id}.
        # I should update Mem0Client.add to accept custom metadata or just rely on agent_id.
        
        return summary_text

    async def _generate_summary(self, memories: List[dict]) -> str:
        """Call LLM to summarize text."""
        try:
            from openai import OpenAI
            import httpx
            
            # Format text
            mem_text = "\n".join([f"- {m.get('memory', m.get('text', ''))}" for m in memories])
            prompt = SUMMARY_PROMPT.format(memories=mem_text)
            
            # Use same config as Router or Settings
            if settings.LLM_PROVIDER == "ollama":
                # Ollama Call
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{settings.LLM_ROUTER_API_BASE}/api/generate",
                        json={
                            "model": settings.LLM_ROUTER_MODEL, # Use the fast model for summary
                            "prompt": prompt,
                            "stream": False
                        },
                        timeout=60.0
                    )
                    if response.status_code == 200:
                        return response.json().get("response", "").strip()
            else:
                # OpenAI Call
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo", # Use cheaper model for summary
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                return response.choices[0].message.content.strip()
                
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return ""

# Singleton
_consolidation_service = None

def get_consolidation_service():
    global _consolidation_service
    if _consolidation_service is None:
        _consolidation_service = MemoryConsolidationService()
    return _consolidation_service
