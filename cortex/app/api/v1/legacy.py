"""
Legacy Compatibility Endpoints
Stubs to support the migration from Node.js Core to Python Cortex.
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

@router.get("/setup-complete")
async def setup_complete() -> dict:
    """
    Mock setup completion status.
    The Python backend is pre-configured via env vars, so setup is always complete.
    """
    return {
        "results": {
            "DisableViewChatHistory": False,
            "MultiUserMode": False
        }
    }

@router.get("/ping")
async def ping() -> dict:
    """Health check for frontend."""
    return {"online": True}

class TokenRequest(BaseModel):
    username: str
    password: str

@router.post("/request-token")
async def request_token(request: dict) -> dict:
    """
    Mock token request.
    In dev mode with DEV_MODE_SKIP_AUTH, this shouldn't block, 
    but we provide a structured response just in case.
    """
    return {
        "valid": True,
        "token": "dev-token-legacy",
        "user": {
            "id": 1,
            "username": "admin",
            "role": "admin"
        }
    }

@router.post("/setup-complete")
async def validation_setup_complete(request: dict) -> dict:
    return {"success": True}

@router.post("/system/custom-models")
async def custom_models(request: dict) -> dict:
    """Stub to prevent 404"""
    return {"models": []}

@router.get("/system/custom-models")
async def get_custom_models() -> dict:
    return {"models": []}
