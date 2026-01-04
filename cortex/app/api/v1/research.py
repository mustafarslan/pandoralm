"""
Deep Research Endpoints
Streaming research with gpt-researcher
"""
import json
from typing import Optional, List
from enum import Enum
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.deep_research import (
    get_research_service,
    ResearchType,
    ResearchStatus,
)

router = APIRouter()


class ResearchTypeEnum(str, Enum):
    basic = "basic"
    comprehensive = "comprehensive"
    regulatory = "regulatory"
    technical = "technical"


class ResearchRequest(BaseModel):
    """Request to start research."""
    topic: str
    workspace_id: str
    research_type: ResearchTypeEnum = ResearchTypeEnum.comprehensive
    max_sources: int = 10
    include_domains: Optional[List[str]] = None


class ResearchStartResponse(BaseModel):
    """Response when research is started."""
    task_id: str
    topic: str
    status: str


class ResearchStatusResponse(BaseModel):
    """Research task status."""
    task_id: str
    status: str
    progress: float
    sources_found: int
    error: Optional[str] = None


class SourceResponse(BaseModel):
    """Research source."""
    url: str
    title: str
    relevance_score: float


class ReportResponse(BaseModel):
    """Research report."""
    task_id: str
    topic: str
    summary: str
    detailed_report: str
    key_findings: List[str]
    sources: List[SourceResponse]
    duration_seconds: float


@router.post("/start", response_model=ResearchStartResponse)
async def start_research(request: ResearchRequest) -> ResearchStartResponse:
    """
    Start a new deep research task.
    
    Returns a task_id for tracking progress via SSE stream.
    """
    service = get_research_service()
    
    # Map enum
    research_type_map = {
        ResearchTypeEnum.basic: ResearchType.BASIC,
        ResearchTypeEnum.comprehensive: ResearchType.COMPREHENSIVE,
        ResearchTypeEnum.regulatory: ResearchType.REGULATORY,
        ResearchTypeEnum.technical: ResearchType.TECHNICAL,
    }
    
    task_id = await service.start_research(
        topic=request.topic,
        research_type=research_type_map[request.research_type],
        max_sources=request.max_sources,
        include_domains=request.include_domains,
    )
    
    return ResearchStartResponse(
        task_id=task_id,
        topic=request.topic,
        status="pending",
    )


@router.get("/stream/{task_id}")
async def stream_research(task_id: str):
    """
    Stream research progress via Server-Sent Events (SSE).
    
    Connect to this endpoint after starting research to receive
    real-time progress updates.
    """
    service = get_research_service()
    
    # Check task exists
    task = service.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Research task not found")
    
    async def event_generator():
        """Generate SSE events."""
        async for progress in service.run_research(task_id):
            event_data = {
                "task_id": progress.task_id,
                "status": progress.status.value,
                "progress": progress.progress,
                "current_step": progress.current_step,
                "sources_found": progress.sources_found,
                "message": progress.message,
            }
            yield f"data: {json.dumps(event_data)}\n\n"
        
        # Send completion event
        yield f"data: {json.dumps({'type': 'complete', 'task_id': task_id})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/status/{task_id}", response_model=ResearchStatusResponse)
async def get_research_status(task_id: str) -> ResearchStatusResponse:
    """Get current status of a research task."""
    service = get_research_service()
    
    task = service.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Research task not found")
    
    return ResearchStatusResponse(
        task_id=task_id,
        status=task["status"].value if isinstance(task["status"], ResearchStatus) else task["status"],
        progress=task.get("progress", 0),
        sources_found=len(task.get("sources", [])),
        error=task.get("error"),
    )


@router.get("/report/{task_id}", response_model=ReportResponse)
async def get_research_report(task_id: str) -> ReportResponse:
    """
    Get completed research report.
    
    Only available after research status is 'completed'.
    """
    service = get_research_service()
    
    report = service.get_report(task_id)
    if not report:
        task = service.get_task_status(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Research task not found")
        raise HTTPException(
            status_code=400,
            detail=f"Report not ready. Status: {task.get('status', 'unknown')}"
        )
    
    return ReportResponse(
        task_id=report.task_id,
        topic=report.topic,
        summary=report.summary,
        detailed_report=report.detailed_report,
        key_findings=report.key_findings,
        sources=[
            SourceResponse(
                url=s.url,
                title=s.title,
                relevance_score=s.relevance_score,
            )
            for s in report.sources
        ],
        duration_seconds=report.duration_seconds,
    )


@router.get("/types")
async def list_research_types() -> dict:
    """List available research types."""
    return {
        "types": [
            {
                "id": "basic",
                "name": "Basic",
                "description": "Quick overview and key facts",
            },
            {
                "id": "comprehensive",
                "name": "Comprehensive",
                "description": "In-depth analysis from multiple perspectives",
            },
            {
                "id": "regulatory",
                "name": "Regulatory",
                "description": "Focus on regulations, compliance, and legal aspects",
            },
            {
                "id": "technical",
                "name": "Technical",
                "description": "Technical details, implementation, and architecture",
            },
        ]
    }
