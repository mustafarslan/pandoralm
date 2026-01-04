"""
System Utilities Endpoints
VRAM calculator, model info, and health checks
"""
from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services import get_vram_calculator, get_embedding_service, Precision

router = APIRouter()


# ========================================
# Request/Response Models
# ========================================

class VRAMEstimateRequest(BaseModel):
    """Request for VRAM estimation."""
    model_name: Optional[str] = None
    parameters_billions: Optional[float] = None
    precision: str = "fp16"
    context_length: int = 4096
    batch_size: int = 1


class VRAMEstimateResponse(BaseModel):
    """VRAM estimation result."""
    model_name: str
    precision: str
    model_size_gb: float
    kv_cache_gb: float
    overhead_gb: float
    total_vram_gb: float
    can_fit_gpus: List[str]
    warnings: List[str]


class ModelInfo(BaseModel):
    """Known model information."""
    id: str
    name: str
    parameters_billions: float
    context_length: int


# ========================================
# Endpoints
# ========================================

@router.post("/vram/estimate", response_model=VRAMEstimateResponse)
async def estimate_vram(request: VRAMEstimateRequest) -> VRAMEstimateResponse:
    """
    Estimate GPU VRAM requirements for running a model.
    
    Provide either model_name (for known models) or parameters_billions.
    """
    calculator = get_vram_calculator()
    
    # Parse precision
    try:
        precision = Precision(request.precision.lower())
    except ValueError:
        precision = Precision.FP16
    
    try:
        estimate = calculator.estimate_vram(
            model_name=request.model_name,
            parameters_billions=request.parameters_billions,
            precision=precision,
            context_length=request.context_length,
            batch_size=request.batch_size,
        )
        
        return VRAMEstimateResponse(
            model_name=estimate.model_name,
            precision=estimate.precision.value,
            model_size_gb=round(estimate.model_size_gb, 2),
            kv_cache_gb=round(estimate.kv_cache_gb, 2),
            overhead_gb=round(estimate.overhead_gb, 2),
            total_vram_gb=round(estimate.total_vram_gb, 2),
            can_fit_gpus=estimate.can_fit_gpus,
            warnings=estimate.warnings,
        )
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/vram/compare")
async def compare_precisions(
    model_name: Optional[str] = None,
    parameters_billions: Optional[float] = None,
    context_length: int = 4096,
) -> List[VRAMEstimateResponse]:
    """Compare VRAM requirements across all precision levels."""
    calculator = get_vram_calculator()
    
    estimates = calculator.compare_precisions(
        model_name=model_name,
        parameters_billions=parameters_billions,
        context_length=context_length,
    )
    
    return [
        VRAMEstimateResponse(
            model_name=e.model_name,
            precision=e.precision.value,
            model_size_gb=round(e.model_size_gb, 2),
            kv_cache_gb=round(e.kv_cache_gb, 2),
            overhead_gb=round(e.overhead_gb, 2),
            total_vram_gb=round(e.total_vram_gb, 2),
            can_fit_gpus=e.can_fit_gpus,
            warnings=e.warnings,
        )
        for e in estimates
    ]


@router.get("/vram/models", response_model=List[ModelInfo])
async def list_known_models() -> List[ModelInfo]:
    """List all known model specifications."""
    calculator = get_vram_calculator()
    models = calculator.list_known_models()
    
    return [
        ModelInfo(
            id=m["id"],
            name=m["name"],
            parameters_billions=m["parameters_billions"],
            context_length=m["context_length"],
        )
        for m in models
    ]


@router.get("/vram/precisions")
async def list_precisions() -> dict:
    """List available precision levels."""
    return {
        "precisions": [
            {"id": "fp32", "name": "Full Precision (32-bit)", "bits_per_param": 32},
            {"id": "fp16", "name": "Half Precision (16-bit)", "bits_per_param": 16},
            {"id": "bf16", "name": "Brain Float (16-bit)", "bits_per_param": 16},
            {"id": "int8", "name": "8-bit Quantization", "bits_per_param": 8},
            {"id": "int4", "name": "4-bit Quantization", "bits_per_param": 4},
            {"id": "q4_k_m", "name": "GGUF Q4_K_M (~4.5 bits)", "bits_per_param": 4.5},
            {"id": "q5_k_m", "name": "GGUF Q5_K_M (~5.5 bits)", "bits_per_param": 5.5},
            {"id": "q6_k", "name": "GGUF Q6_K (~6.5 bits)", "bits_per_param": 6.5},
            {"id": "q8_0", "name": "GGUF Q8_0 (8 bits)", "bits_per_param": 8},
        ]
    }


@router.get("/embedding/info")
async def get_embedding_info() -> dict:
    """Get information about the current embedding model."""
    service = get_embedding_service()
    return service.get_model_info()


@router.get("/models/available")
async def list_available_models(provider: Optional[str] = None) -> List[str]:
    """
    List available models from the configured provider (e.g., Ollama).
    """
    import httpx
    from app.core.config import settings
    
    target_provider = provider or settings.LLM_PROVIDER
    
    if target_provider == "ollama":
        urls_to_try = [
            f"{settings.LLM_ROUTER_API_BASE}/api/tags",
            "http://localhost:11434/api/tags",
            "http://127.0.0.1:11434/api/tags"
        ]
        # Deduplicate while preserving order
        urls_to_try = list(dict.fromkeys(urls_to_try))

        print(f"[DEBUG] Ollama Fetch: Trying URLs: {urls_to_try}")

        for url in urls_to_try:
            try:
                print(f"[DEBUG] Attempting connection to: {url}")
                async with httpx.AsyncClient(timeout=2.0) as client:
                    resp = await client.get(url)
                    print(f"[DEBUG] Response status for {url}: {resp.status_code}")
                    if resp.status_code == 200:
                        data = resp.json()
                        models = [m["name"] for m in data.get("models", [])]
                        print(f"[DEBUG] Success! Models found: {models}")
                        return models
            except Exception as e:
                print(f"[WARN] Failed to connect to {url}: {e}")
                continue
        
        print("[ERROR] All Ollama connection attempts failed.")
        return []


@router.post("/update-env")
async def update_env_stub(request: dict) -> dict:
    """
    Stub for updating system env variables (Pandora Frontend compatibility).
    """
    import json
    print(f"[DEBUG] System Update Request: {json.dumps(request, indent=2)}")
    return {"newValues": request, "error": None}

