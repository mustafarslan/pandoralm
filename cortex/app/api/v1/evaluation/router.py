from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import random

from app.core.security import require_admin

router = APIRouter()

class MetricScore(BaseModel):
    name: str
    score: float = Field(..., ge=0.0, le=1.0)
    threshold: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    timestamp: datetime

class GoldenSampleCreate(BaseModel):
    query: str
    response: str
    context_chunks: List[str] = []

class QualityGateStatus(BaseModel):
    status: str # "PASS", "FAIL", "WARNING"
    last_run: datetime
    metrics: List[MetricScore]
    hallucination_rate_history: List[float] # For the Regression Radar

@router.get("/debug")
async def debug_endpoint():
    return {"status": "Evaluation Router OK"}

@router.get(
    "/latest",
    response_model=QualityGateStatus,
    dependencies=[Depends(require_admin())]
)
async def get_quality_gate_status():
    """
    Get the latest RAG Quality metrics from DeepEval.
    (Mocked for Phase 5 MVP until CI pipeline is connected)
    """

    # Mock Data based on "real-world" scenarios
    return QualityGateStatus(
        status="PASS",
        last_run=datetime.utcnow(),
        metrics=[
            MetricScore(
                name="Faithfulness",
                score=0.92,
                threshold=0.8,
                reasoning="The answer strictly follows the retrieved context about 'Vector Databases'. No hallucinations detected.",
                timestamp=datetime.utcnow()
            ),
            MetricScore(
                name="Answer Relevancy",
                score=0.85,
                threshold=0.7,
                reasoning="The response directly answers the user's question about scaling, though it could be more concise.",
                timestamp=datetime.utcnow()
            ),
            MetricScore(
                name="Contextual Precision",
                score=0.78,
                threshold=0.7,
                reasoning="Retrieved chunks 1 and 3 were highly relevant, but chunk 2 was noise (marketing text).",
                timestamp=datetime.utcnow()
            )
        ],
        hallucination_rate_history=[0.05, 0.04, 0.02, 0.01, 0.00] # Decreasing trend
    )

@router.post("/runs/trigger")
async def trigger_evaluation_run(
    dependencies=[Depends(require_admin())]
):
    """
    Manually trigger a DeepEval evaluation run on the Golden Dataset.
    (Async Fire-and-Forget)
    """
    # In real implementation: celery_app.send_task("tasks.evaluate_golden_dataset")
    return {"status": "triggered", "job_id": "eval_job_123"}

class GoldenSample(BaseModel):
    id: str
    query: str
    response: str
    context_chunks: List[str]
    status: str # "PENDING", "VERIFIED", "REJECTED"
    created_at: datetime

@router.get(
    "/gold-standard/pending",
    response_model=List[GoldenSample],
    dependencies=[Depends(require_admin())]
)
async def get_pending_gold_samples():
    """
    Get list of high-quality responses pending manual verification for the Golden Dataset.
    (Mocked)
    """
    return [
        GoldenSample(
            id="g_1",
            query="How does the tiered inference work?",
            response="PandoraLM uses a tiered inference approach with a 'Router' (System 1, e.g., gemma3:1b) for fast classification and a 'Solver' (System 2, e.g., deepseek-r1:8b) for complex reasoning.",
            context_chunks=["Chunk X: Tiered Inference Architecture..."],
            status="PENDING",
            created_at=datetime.utcnow()
        ),
        GoldenSample(
            id="g_2",
            query="What is the KnowledgeRail?",
            response="The KnowledgeRail is the main navigation component that manages ReBAC layers.",
            context_chunks=["Chunk Y: UI/UX Overhaul..."],
            status="PENDING",
            created_at=datetime.utcnow()
        )
    ]

@router.post(
    "/gold-standard/{sample_id}/verify",
    dependencies=[Depends(require_admin())]
)
async def verify_gold_sample(sample_id: str, action: str):
    """
    Approve or Reject a sample for inclusion in the Golden Dataset.
    """
    return {"status": "success", "id": sample_id, "action": action, "dataset_size": 152}

@router.post(
    "/gold-standard/add",
    dependencies=[Depends(require_admin())]
)
async def add_gold_sample(sample: GoldenSampleCreate):
    """
    Manually add a high-quality conversation turn to the Golden Dataset queue.
    """
    return {
        "status": "queued",
        "sample": {
            "id": f"g_{random.randint(1000, 9999)}",
            "query": sample.query,
            "response": sample.response,
            "status": "PENDING"
        }
    }
