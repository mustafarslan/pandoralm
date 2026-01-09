"""
Memory Middleware

FastAPI middleware to inject user memories into request context.
Intercepts chat requests and enriches them with relevant past memories.
"""
import logging
import asyncio
from typing import Callable, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.services.memory.mem0_client import get_mem0_client

logger = logging.getLogger(__name__)

# Timeout for memory search (don't block chat if memory is slow)
MEMORY_SEARCH_TIMEOUT_SECONDS = 2.0


async def memory_middleware(request: Request, call_next: Callable):
    """
    Middleware to inject memories into request context for chat endpoints.

    Flow:
    1. Intercept POST /api/v1/chat or /api/v1/stream/chat
    2. Extract user_id from request.state.user
    3. Call mem0.search() with timeout protection
    4. Inject memories into request.state.memories

    Args:
        request: FastAPI request
        call_next: Next middleware/handler in chain

    Returns:
        Response from downstream handler
    """
    # Initialize memories as empty list
    request.state.memories = []

    # Only process chat endpoints
    if not _is_chat_endpoint(request):
        return await call_next(request)

    # Check if memory is enabled
    if not settings.ENABLE_MEMORY:
        return await call_next(request)

    # Extract user_id from auth state
    user_id = _get_user_id(request)
    if not user_id:
        logger.debug("No user_id found, skipping memory injection")
        return await call_next(request)

    # Extract query from request body (need to peek at body)
    query = await _extract_query(request)
    if not query:
        return await call_next(request)

    # Search memories with timeout protection
    try:
        memories = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: _search_memories(query, user_id)
            ),
            timeout=MEMORY_SEARCH_TIMEOUT_SECONDS
        )
        request.state.memories = memories

        if memories:
            logger.info(f"Injected {len(memories)} memories for user {user_id}")

    except asyncio.TimeoutError:
        logger.warning(f"Memory search timed out for user {user_id}")
    except Exception as e:
        logger.error(f"Memory middleware error: {e}")

    return await call_next(request)


def _is_chat_endpoint(request: Request) -> bool:
    """Check if this is a chat-related endpoint."""
    return (
        request.method == "POST" and
        request.url.path.startswith("/api/v1/") and
        ("chat" in request.url.path or "stream" in request.url.path)
    )


def _get_user_id(request: Request) -> Optional[str]:
    """Extract user_id from request state."""
    # Check various possible locations for user info
    if hasattr(request.state, "user"):
        user = request.state.user
        if hasattr(user, "id"):
            return user.id
        elif isinstance(user, dict):
            return user.get("id") or user.get("user_id") or user.get("sub")

    # Fallback: Check headers for dev mode
    if settings.DEV_MODE_SKIP_AUTH:
        return request.headers.get("X-User-Id", "dev-user")

    return None


async def _extract_query(request: Request) -> Optional[str]:
    """
    Extract query from request body.

    Note: This requires reading the body, which can only be done once.
    We store it back in request.state for the actual handler.
    """
    try:
        # Get body (this consumes it)
        body = await request.body()

        # Store for later use
        request.state._body = body

        if not body:
            return None

        import json
        try:
            data = json.loads(body)
            # Try common query field names
            return (
                data.get("query") or
                data.get("message") or
                data.get("content") or
                data.get("text")
            )
        except json.JSONDecodeError:
            return None

    except Exception as e:
        logger.error(f"Failed to extract query from request: {e}")
        return None


def _search_memories(query: str, user_id: str):
    """Synchronous memory search (for executor)."""
    client = get_mem0_client()
    return client.search(query, user_id)


def format_memories_for_prompt(memories: list) -> str:
    """
    Format memories for injection into system prompt.

    Args:
        memories: List of memory dicts from Mem0

    Returns:
        Formatted string for system prompt
    """
    if not memories:
        return ""

    lines = ["## User Context (from previous conversations)"]
    for mem in memories:
        text = mem.get("text", "")
        if text:
            lines.append(f"- {text}")

    return "\n".join(lines)
