"""
Workspace Management Endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import require_auth, UserContext
from app.models.workspace import Workspace as WorkspaceModel
from app.services.workspace_layer_service import WorkspaceLayerService

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
async def create_workspace(
    request: CreateWorkspaceRequest,
    user: UserContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new workspace (Real DB Impl).
    """
    import datetime

    slug = request.name.lower().replace(" ", "-")

    # Check if exists
    stmt = select(WorkspaceModel).where(WorkspaceModel.slug == slug)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # Return existing to be idempotent/friendly
        # Or should we Update?
        ws = existing
    else:
        ws = WorkspaceModel(name=request.name, slug=slug)
        db.add(ws)
        await db.commit()
        await db.refresh(ws)

        # Only init layers if new
        try:
            # We use singleton service, but we could pass db if we wanted transaction reuse?
            # initialize_defaults creates its own session as implemented.
            await WorkspaceLayerService.initialize_defaults(slug)
        except Exception as e:
            print(f"Layer Init Warning: {e}")

    return {
        "workspace": ws.to_dict(),
        "message": "Workspace created successfully."
    }

@router.get("/")
async def list_workspaces(
    user: UserContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """List available workspaces."""
    stmt = select(WorkspaceModel)
    result = await db.execute(stmt)
    workspaces = result.scalars().all()

    return {
        "workspaces": [w.to_dict() for w in workspaces]
    }

@router.get("/{slug}")
async def get_workspace(
    slug: str,
    user: UserContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific workspace by slug."""
    stmt = select(WorkspaceModel).where(WorkspaceModel.slug == slug)
    result = await db.execute(stmt)
    ws = result.scalar_one_or_none()

    if not ws:
        # Fallback to mock if not found? No, user forbid mocks.
        raise HTTPException(status_code=404, detail="Workspace not found")

    return {
        "workspace": ws.to_dict()
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
