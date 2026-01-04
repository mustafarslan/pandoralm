"""
Workspace Management Endpoints
"""
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class CreateWorkspaceRequest(BaseModel):
    name: str
    
    class Config:
        extra = "allow"

class Workspace(BaseModel):
    id: int
    name: str
    slug: str
    vectorTag: Optional[str] = None
    createdAt: str
    lastUpdatedAt: str

@router.post("/new")
async def create_workspace(request: CreateWorkspaceRequest):
    """
    Create a new workspace.
    For the Python backend, we store this in Postgres/Neo4j, 
    but for now we mock the response to unblock onboarding.
    """
    import datetime
    
    slug = request.name.lower().replace(" ", "-")
    now = datetime.datetime.now().isoformat()
    
    return {
        "workspace": {
            "id": 1,
            "name": request.name,
            "slug": slug,
            "vectorTag": slug,
            "createdAt": now,
            "lastUpdatedAt": now
        },
        "message": "Workspace created successfully."
    }

@router.get("/")
async def list_workspaces():
    """List available workspaces."""
    return {
        "workspaces": [
            {
                "id": 1,
                "name": "My First Workspace",
                "slug": "my-first-workspace",
                "vectorTag": "my-first-workspace",
                "createdAt": "2024-01-01T00:00:00.000Z",
                "lastUpdatedAt": "2024-01-01T00:00:00.000Z"
            }
        ]
    }

@router.get("/{slug}")
async def get_workspace(slug: str):
    """Get a specific workspace by slug."""
    return {
        "workspace": {
            "id": 1,
            "name": "My First Workspace",
            "slug": slug,
            "vectorTag": slug,
            "createdAt": "2024-01-01T00:00:00.000Z",
            "lastUpdatedAt": "2024-01-01T00:00:00.000Z"
        }
    }

@router.get("/{slug}/threads")
async def list_threads(slug: str):
    """List threads for a workspace."""
    return {
        "threads": [
            {
                "id": 1,
                "name": "default",
                "slug": "default",
                "createdAt": "2024-01-01T00:00:00.000Z"
            }
        ]
    }

@router.post("/{slug}/thread/new")
async def create_thread(slug: str):
    """Create a new thread in a workspace."""
    import datetime
    now = datetime.datetime.now().isoformat()
    return {
        "thread": {
            "id": 2,
            "name": "New Thread",
            "slug": f"thread-{now[:10]}",
            "createdAt": now
        },
        "error": None
    }

@router.get("/{slug}/chats")
async def get_workspace_chats(slug: str):
    """Get chat history for a workspace (default thread)."""
    return {
        "history": []
    }

@router.get("/{slug}/thread/{thread_slug}/chats")
async def get_thread_chats(slug: str, thread_slug: str):
    """Get chat history for a specific thread."""
    return {
        "history": []
    }

@router.get("/{slug}/parsed-files")
async def get_parsed_files(slug: str, threadSlug: str = None):
    """Get parsed files for a workspace (attachments)."""
    return {
        "files": [],
        "contextWindow": 128000,
        "currentContextTokenCount": 0
    }

@router.get("/{slug}/pfp")
async def get_workspace_pfp(slug: str):
    """Get workspace profile picture."""
    return {"pfpUrl": None}

@router.get("/{slug}/suggested-messages")
async def get_suggested_messages(slug: str):
    """Get suggested messages for a workspace."""
    return {"suggestedMessages": []}
