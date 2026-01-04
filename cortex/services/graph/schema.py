from pydantic import BaseModel, Field
from typing import List, Optional

class GraphNode(BaseModel):
    layer_id: str
    element_id: str
    
class MeetingNode(GraphNode):
    url: str
    date: str
    
class PersonNode(GraphNode):
    name: str
    speaker_id: str
    
class TranscriptChunkNode(GraphNode):
    text: str
    start: float
    end: float
    speaker_id: str

# Cypher constraints creation helper
# In a real app this might be a migration script
def get_schema_constraints():
    return [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Meeting) REQUIRE m.element_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.element_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (t:TranscriptChunk) REQUIRE t.element_id IS UNIQUE"
    ]
