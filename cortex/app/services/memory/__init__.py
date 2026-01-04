"""
Memory Service Module

Provides persistent memory capabilities using Mem0 SDK with LanceDB backend.
Enables PandoraLM to remember user preferences across sessions.
"""
from app.services.memory.mem0_client import Mem0Client, get_mem0_client
from app.services.memory.middleware import memory_middleware

__all__ = [
    "Mem0Client",
    "get_mem0_client",
    "memory_middleware",
]
