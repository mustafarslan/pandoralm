from typing import List, Optional
from pydantic import BaseModel

class Layer(BaseModel):
    id: str
    name: str
    type: str  # SYSTEM, ORG, TEAM, USER
    color: str
    permissions: List[str]

class UserLayersResponse(BaseModel):
    layers: List[Layer]
