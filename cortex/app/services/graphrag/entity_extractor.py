"""
GraphRAG Entity Extractor
LLM-based entity extraction from text chunks
"""
import uuid
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from app.core.config import settings


@dataclass
class ExtractedEntity:
    """An entity extracted from text."""
    name: str
    type: str
    description: str
    source_chunk_id: str
    confidence: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "source_chunk_id": self.source_chunk_id,
            "confidence": self.confidence,
            "properties": self.properties,
        }


@dataclass
class ExtractedRelationship:
    """A relationship between entities."""
    source_entity: str
    target_entity: str
    relationship_type: str
    description: str
    source_chunk_id: str
    weight: float = 1.0

    def to_dict(self) -> dict:
        return {
            "source_entity": self.source_entity,
            "target_entity": self.target_entity,
            "relationship_type": self.relationship_type,
            "description": self.description,
            "source_chunk_id": self.source_chunk_id,
            "weight": self.weight,
        }


# Entity extraction prompt
ENTITY_EXTRACTION_PROMPT = """You are an expert at extracting structured entities from text.

Given the following text, extract all important entities (people, organizations, concepts, regulations, technologies, locations, etc.).

For each entity, provide:
- name: The entity name
- type: The category (PERSON, ORGANIZATION, CONCEPT, REGULATION, TECHNOLOGY, LOCATION, EVENT, DOCUMENT, OTHER)
- description: A brief description based on the context

Text:
{text}

Respond with a JSON array of entities:
[
  {{"name": "...", "type": "...", "description": "..."}}
]

Only output valid JSON, no other text."""


# Relationship extraction prompt
RELATIONSHIP_EXTRACTION_PROMPT = """You are an expert at extracting relationships between entities.

Given the following text and list of entities, identify relationships between them.

Entities:
{entities}

Text:
{text}

For each relationship, provide:
- source: The name of the source entity
- target: The name of the target entity
- type: The relationship type (RELATES_TO, PART_OF, REGULATES, CONFLICTS_WITH, DEPENDS_ON, CREATED_BY, LOCATED_IN, etc.)
- description: Brief description of the relationship

Respond with a JSON array:
[
  {{"source": "...", "target": "...", "type": "...", "description": "..."}}
]

Only output valid JSON, no other text."""


class EntityExtractor:
    """
    Extracts entities and relationships from text using LLM.

    Uses Ollama's OpenAI-compatible API (via LLM_SOLVER_MODEL) to identify:
    - Named entities (people, orgs, concepts, etc.)
    - Relationships between entities
    """

    def __init__(self):
        self._client = None

    @property
    def client(self):
        """Lazy initialization of OpenAI-compatible client (pointing to Ollama)."""
        if self._client is None:
            try:
                from openai import OpenAI
                # Use Ollama's OpenAI-compatible endpoint
                base_url = settings.LLM_SOLVER_API_BASE
                if not base_url.endswith("/v1"):
                    base_url = f"{base_url}/v1"
                self._client = OpenAI(
                    base_url=base_url,
                    api_key="ollama",  # Ollama doesn't need a real key
                )
            except ImportError:
                raise ImportError("openai package required for entity extraction")
        return self._client

    async def extract_entities(
        self,
        text: str,
        chunk_id: str,
        model: str = None,
    ) -> List[ExtractedEntity]:
        """Extract entities from a text chunk."""
        # Use dedicated GraphRAG model (faster, better at JSON) instead of reasoning model
        model = model or settings.LLM_GRAPHRAG_MODEL

        prompt = ENTITY_EXTRACTION_PROMPT.format(text=text[:4000])  # Limit text length

        try:
            import asyncio
            loop = asyncio.get_event_loop()

            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=2000,
                )
            )

            content = response.choices[0].message.content.strip()

            # Parse JSON response
            entities_data = self._parse_json_response(content)

            entities = []
            for ent in entities_data:
                entities.append(ExtractedEntity(
                    name=ent.get("name", "Unknown"),
                    type=ent.get("type", "OTHER"),
                    description=ent.get("description", ""),
                    source_chunk_id=chunk_id,
                ))

            return entities

        except Exception as e:
            print(f"Entity extraction failed: {e}")
            return []

    async def extract_relationships(
        self,
        text: str,
        entities: List[ExtractedEntity],
        chunk_id: str,
        model: str = None,
    ) -> List[ExtractedRelationship]:
        """Extract relationships between entities."""
        if len(entities) < 2:
            return []

        model = model or settings.LLM_GRAPHRAG_MODEL

        entity_list = "\n".join([f"- {e.name} ({e.type})" for e in entities])
        prompt = RELATIONSHIP_EXTRACTION_PROMPT.format(
            entities=entity_list,
            text=text[:4000],
        )

        try:
            import asyncio
            loop = asyncio.get_event_loop()

            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=2000,
                )
            )

            content = response.choices[0].message.content.strip()

            # Parse JSON response
            rels_data = self._parse_json_response(content)

            # Create entity name set for validation
            entity_names = {e.name.lower() for e in entities}

            relationships = []
            for rel in rels_data:
                source = rel.get("source", "")
                target = rel.get("target", "")

                # Validate entities exist
                if source.lower() in entity_names and target.lower() in entity_names:
                    relationships.append(ExtractedRelationship(
                        source_entity=source,
                        target_entity=target,
                        relationship_type=rel.get("type", "RELATES_TO"),
                        description=rel.get("description", ""),
                        source_chunk_id=chunk_id,
                    ))

            return relationships

        except Exception as e:
            print(f"Relationship extraction failed: {e}")
            return []

    def _parse_json_response(self, content: str) -> List[dict]:
        """Parse JSON from LLM response."""
        # Try to find JSON array in response
        content = content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1])

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON array
            import re
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return []


# Singleton
_extractor: Optional[EntityExtractor] = None

def get_entity_extractor() -> EntityExtractor:
    global _extractor
    if _extractor is None:
        _extractor = EntityExtractor()
    return _extractor
