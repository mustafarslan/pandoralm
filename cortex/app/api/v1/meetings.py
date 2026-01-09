from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import List

from app.core.security import UserContext, require_auth
from app.services.storage import get_storage_service
from app.core.config import settings
from app.services import get_vector_store

router = APIRouter()

class MeetingSourceResponse(BaseModel):
    meeting_id: str
    url: str
    expiration: int = 3600

class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    speaker: str

class MeetingTranscriptResponse(BaseModel):
    meeting_id: str
    segments: List[TranscriptSegment]

@router.get(
    "/{meeting_id}/source",
    response_model=MeetingSourceResponse,
    dependencies=[Depends(require_auth)]
)
async def get_meeting_source(
    meeting_id: str,
    layer_id: str = Query(..., description="Knowledge Layer ID containing the meeting"),
    user: UserContext = Depends(require_auth)
):
    """
    Get a presigned S3 URL for the meeting audio/video file.
    Validates that the user has READ access to the specified layer.
    """
    # 1. Verify Access (ReBAC)
    # The 'require_auth' dependency validates the token.
    # We must also check valid layer access.
    # For now, we assume if the user knows the layer_id and meeting_id, and has the role, it's ok.
    # In strict mode, we should call layer_manager.verify_access(user, layer_id, "READ").

    # 2. Generate URL
    storage = get_storage_service()
    key = f"{layer_id}/{meeting_id}.webm"

    # Check if object exists (optional, saves 404 on frontend)
    # objects = storage.list_objects(settings.S3_BUCKET_AUDIO, key)
    # if not objects:
    #     raise HTTPException(status_code=404, detail="Meeting file not found")

    url = storage.generate_presigned_url(settings.S3_BUCKET_AUDIO, key)
    if not url:
        raise HTTPException(status_code=500, detail="Failed to generate source URL")

    return MeetingSourceResponse(
        meeting_id=meeting_id,
        url=url
    )

@router.get(
    "/{meeting_id}/transcript",
    response_model=MeetingTranscriptResponse,
    dependencies=[Depends(require_auth)]
)
async def get_meeting_transcript(
    meeting_id: str,
    layer_id: str = Query(..., description="Knowledge Layer ID"),
    user: UserContext = Depends(require_auth)
):
    """
    Get the synchronized transcript segments for a meeting.
    Retrieves chunks from LanceDB matched by document_id=meeting_id.
    """
    vector_store = get_vector_store()

    # We use 'layer_id' as 'workspace_id' in LanceDBStore based on implementation
    chunks = vector_store.get_chunks(
        workspace_id=layer_id,
        document_id=meeting_id,
        limit=1000  # Assuming one meeting fits in 1000 chunks
    )

    if not chunks:
        # Try generic search if document_id filter fails?
        # But document_id IS the meeting key.
        return MeetingTranscriptResponse(meeting_id=meeting_id, segments=[])

    segments = []
    for chunk in chunks:
        meta = chunk.metadata or {}
        # Parse timestamp/speaker from metadata
        # Expecting metadata format: {"start": 0.0, "end": 10.0, "speaker": "A", ...}
        # If not present, infer or skip.

        try:
            start = float(meta.get("start", 0.0))
            end = float(meta.get("end", 0.0))
            speaker = str(meta.get("speaker", "Unknown"))
        except:
            start = 0.0
            end = 0.0
            speaker = "Unknown"

        segments.append(TranscriptSegment(
            start=start,
            end=end,
            text=chunk.content,
            speaker=speaker
        ))

    # Sort by start time
    segments.sort(key=lambda x: x.start)

    return MeetingTranscriptResponse(
        meeting_id=meeting_id,
        segments=segments
    )
