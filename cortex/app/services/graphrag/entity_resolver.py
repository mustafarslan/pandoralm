"""
Entity Resolution Service

Detects and suggests entity merges to prevent graph fragmentation.
Uses embedding similarity to identify potential duplicates.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

import numpy as np

from app.core.config import settings
from app.core.telemetry import trace_span

logger = logging.getLogger(__name__)


@dataclass
class MergeSuggestion:
    """A suggested entity merge."""
    source_id: str
    source_name: str
    target_id: str
    target_name: str
    similarity_score: float
    entity_type: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "similarity_score": self.similarity_score,
            "entity_type": self.entity_type,
        }


class EntityResolver:
    """
    Entity resolution service for detecting and merging duplicate entities.

    Uses cosine similarity of entity embeddings to identify potential duplicates.
    Provides suggestions for the Admin Console to review and approve merges.
    """

    def __init__(self, threshold: float = 0.95):
        """
        Initialize entity resolver.

        Args:
            threshold: Minimum similarity score to consider as duplicate (0.0-1.0)
        """
        self.threshold = threshold

    @trace_span("entity_resolver.find_duplicates")
    def find_duplicates(
        self,
        layer_id: str,
        threshold: Optional[float] = None,
    ) -> List[MergeSuggestion]:
        """
        Find potential duplicate entities using cosine similarity.

        Args:
            layer_id: Layer ID for scoping (security filter)
            threshold: Override default similarity threshold

        Returns:
            List of MergeSuggestion objects
        """
        if threshold is None:
            threshold = self.threshold

        try:
            from app.services.graphrag import get_graph_store
            from app.services.embedding import get_embedding_service

            graph_store = get_graph_store()
            embedding_service = get_embedding_service()

            # Get all entities for the layer
            entities = graph_store.get_entities_by_layer(layer_id)

            if len(entities) < 2:
                logger.info(f"Not enough entities to find duplicates in layer {layer_id}")
                return []

            # Get or compute embeddings for entity names
            embeddings = []
            entity_list = []

            for entity in entities:
                # Use entity name + type for better disambiguation
                text = f"{entity.name} ({entity.type})"
                embedding = embedding_service.embed_sync(text)
                embeddings.append(embedding)
                entity_list.append(entity)

            # Convert to numpy array
            embedding_matrix = np.array(embeddings)

            # Normalize for cosine similarity
            norms = np.linalg.norm(embedding_matrix, axis=1, keepdims=True)
            normalized = embedding_matrix / np.maximum(norms, 1e-10)

            # Compute similarity matrix
            similarity_matrix = np.dot(normalized, normalized.T)

            # Find pairs above threshold
            duplicates = []
            seen_pairs = set()

            for i in range(len(entity_list)):
                for j in range(i + 1, len(entity_list)):
                    similarity = similarity_matrix[i, j]

                    if similarity >= threshold:
                        # Only suggest merge if same entity type
                        if entity_list[i].type == entity_list[j].type:
                            pair_key = tuple(sorted([entity_list[i].id, entity_list[j].id]))

                            if pair_key not in seen_pairs:
                                seen_pairs.add(pair_key)

                                duplicates.append(MergeSuggestion(
                                    source_id=entity_list[j].id,
                                    source_name=entity_list[j].name,
                                    target_id=entity_list[i].id,
                                    target_name=entity_list[i].name,
                                    similarity_score=float(similarity),
                                    entity_type=entity_list[i].type,
                                ))

            # Sort by similarity (highest first)
            duplicates.sort(key=lambda x: x.similarity_score, reverse=True)

            logger.info(f"Found {len(duplicates)} potential duplicates in layer {layer_id}")
            return duplicates

        except Exception as e:
            logger.error(f"Failed to find duplicates: {e}")
            return []

    @trace_span("entity_resolver.suggest_merges")
    def suggest_merges(
        self,
        layer_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get merge suggestions ready for the Admin Console API.

        Args:
            layer_id: Layer ID for scoping
            limit: Maximum number of suggestions to return

        Returns:
            List of merge suggestion dicts
        """
        duplicates = self.find_duplicates(layer_id)
        return [d.to_dict() for d in duplicates[:limit]]

    @trace_span("entity_resolver.execute_merge")
    def execute_merge(
        self,
        source_id: str,
        target_id: str,
        layer_id: str,
    ) -> bool:
        """
        Execute an entity merge using Neo4j APOC.

        Merges source entity into target, transferring all relationships.

        Args:
            source_id: Entity to merge from (will be deleted)
            target_id: Entity to merge into (will be kept)
            layer_id: Layer for verification

        Returns:
            True if merge succeeded
        """
        try:
            from app.services.graphrag import get_graph_store

            graph_store = get_graph_store()

            # Execute merge via APOC
            success = graph_store.merge_entities(
                source_id=source_id,
                target_id=target_id,
                layer_id=layer_id,
            )

            if success:
                logger.info(f"Merged entity {source_id} into {target_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to merge entities {source_id} -> {target_id}: {e}")
            return False

    def find_similar_entities(
        self,
        entity_name: str,
        layer_id: str,
        limit: int = 5,
    ) -> List[Tuple[str, str, float]]:
        """
        Find entities similar to a given name.

        Useful for entity linking during ingestion.

        Args:
            entity_name: Name to search for
            layer_id: Layer to search in
            limit: Maximum results

        Returns:
            List of (entity_id, entity_name, similarity_score) tuples
        """
        try:
            from app.services.graphrag import get_graph_store
            from app.services.embedding import get_embedding_service

            graph_store = get_graph_store()
            embedding_service = get_embedding_service()

            # Embed the query name
            query_embedding = embedding_service.embed_sync(entity_name)
            query_embedding = np.array(query_embedding)
            query_embedding = query_embedding / np.linalg.norm(query_embedding)

            # Get all entities
            entities = graph_store.get_entities_by_layer(layer_id)

            results = []

            for entity in entities:
                entity_embedding = embedding_service.embed_sync(entity.name)
                entity_embedding = np.array(entity_embedding)
                entity_embedding = entity_embedding / np.linalg.norm(entity_embedding)

                similarity = float(np.dot(query_embedding, entity_embedding))
                results.append((entity.id, entity.name, similarity))

            # Sort by similarity
            results.sort(key=lambda x: x[2], reverse=True)

            return results[:limit]

        except Exception as e:
            logger.error(f"Failed to find similar entities: {e}")
            return []


# Singleton
_resolver: Optional[EntityResolver] = None


def get_entity_resolver() -> EntityResolver:
    """Get or create the entity resolver singleton."""
    global _resolver
    if _resolver is None:
        _resolver = EntityResolver()
    return _resolver
