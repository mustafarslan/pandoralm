"""
Community Detection using Leiden Algorithm
Groups related entities into hierarchical communities
"""
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from app.services.graphrag.neo4j_store import Entity, Relationship, Community


@dataclass
class CommunityNode:
    """A node in the community structure."""
    entity_id: str
    entity_name: str
    community_id: Optional[str] = None
    level: int = 0


class CommunityDetector:
    """
    Detects communities in a knowledge graph using the Leiden algorithm.
    
    The Leiden algorithm improves on Louvain by:
    - Guaranteeing connected communities
    - Better optimization of modularity
    - Faster convergence
    
    This implementation uses networkx for graph operations and 
    leidenalg for community detection when available.
    """
    
    def __init__(self, resolution: float = 1.0, n_iterations: int = 10):
        """
        Initialize community detector.
        
        Args:
            resolution: Resolution parameter for community detection.
                       Higher = more smaller communities
            n_iterations: Number of optimization iterations
        """
        self.resolution = resolution
        self.n_iterations = n_iterations
    
    def detect_communities(
        self,
        entities: List[Entity],
        relationships: List[Relationship],
        max_levels: int = 3,
    ) -> List[Community]:
        """
        Detect hierarchical communities from entities and relationships.
        
        Args:
            entities: List of graph entities
            relationships: List of relationships between entities
            max_levels: Maximum hierarchy levels (0 = most aggregated)
            
        Returns:
            List of detected communities
        """
        if not entities or len(entities) < 2:
            return []
        
        # Build adjacency structure
        entity_map = {e.id: e for e in entities}
        entity_name_to_id = {e.name.lower(): e.id for e in entities}
        
        # Build graph as adjacency list
        adjacency: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
        
        for rel in relationships:
            # Map entity names to IDs
            source_id = entity_name_to_id.get(rel.source_id.lower()) or rel.source_id
            target_id = entity_name_to_id.get(rel.target_id.lower()) or rel.target_id
            
            if source_id in entity_map and target_id in entity_map:
                adjacency[source_id].append((target_id, rel.weight))
                adjacency[target_id].append((source_id, rel.weight))
        
        # Try using leidenalg if available
        try:
            return self._detect_with_leiden(entities, adjacency, entity_map, max_levels)
        except ImportError:
            # Fallback to simple modularity-based detection
            return self._detect_simple(entities, adjacency, entity_map, max_levels)
    
    def _detect_with_leiden(
        self,
        entities: List[Entity],
        adjacency: Dict[str, List[Tuple[str, float]]],
        entity_map: Dict[str, Entity],
        max_levels: int,
    ) -> List[Community]:
        """Detect communities using Leiden algorithm via igraph/leidenalg."""
        import igraph as ig
        import leidenalg
        
        # Build igraph graph
        entity_ids = list(entity_map.keys())
        id_to_idx = {eid: i for i, eid in enumerate(entity_ids)}
        
        edges = []
        weights = []
        seen_edges = set()
        
        for source_id, neighbors in adjacency.items():
            for target_id, weight in neighbors:
                if source_id in id_to_idx and target_id in id_to_idx:
                    edge = tuple(sorted([source_id, target_id]))
                    if edge not in seen_edges:
                        seen_edges.add(edge)
                        edges.append((id_to_idx[source_id], id_to_idx[target_id]))
                        weights.append(weight)
        
        if not edges:
            return self._create_single_community(entities, 0)
        
        g = ig.Graph(n=len(entity_ids), edges=edges)
        g.es['weight'] = weights
        
        # Run hierarchical Leiden
        communities = []
        
        for level in range(max_levels):
            # Adjust resolution for each level
            resolution = self.resolution * (2 ** level)
            
            partition = leidenalg.find_partition(
                g,
                leidenalg.RBConfigurationVertexPartition,
                weights='weight',
                resolution_parameter=resolution,
                n_iterations=self.n_iterations,
            )
            
            # Create community objects
            for comm_idx, member_indices in enumerate(partition):
                if len(member_indices) >= 2:  # Only keep communities with 2+ members
                    member_ids = [entity_ids[i] for i in member_indices]
                    member_entities = [entity_map[eid] for eid in member_ids if eid in entity_map]
                    
                    community = self._create_community(
                        entities=member_entities,
                        level=level,
                        community_index=comm_idx,
                    )
                    communities.append(community)
        
        return communities
    
    def _detect_simple(
        self,
        entities: List[Entity],
        adjacency: Dict[str, List[Tuple[str, float]]],
        entity_map: Dict[str, Entity],
        max_levels: int,
    ) -> List[Community]:
        """Simple community detection using connected components and clustering."""
        # Find connected components
        visited = set()
        components = []
        
        def dfs(node: str) -> List[str]:
            stack = [node]
            component = []
            while stack:
                n = stack.pop()
                if n not in visited:
                    visited.add(n)
                    component.append(n)
                    for neighbor, _ in adjacency.get(n, []):
                        if neighbor not in visited:
                            stack.append(neighbor)
            return component
        
        for entity_id in entity_map:
            if entity_id not in visited:
                component = dfs(entity_id)
                if component:
                    components.append(component)
        
        # Create communities from components
        communities = []
        
        for comp_idx, component_ids in enumerate(components):
            if len(component_ids) >= 2:
                member_entities = [entity_map[eid] for eid in component_ids if eid in entity_map]
                
                # Level 0: Most aggregated (entire component)
                community = self._create_community(
                    entities=member_entities,
                    level=0,
                    community_index=comp_idx,
                )
                communities.append(community)
                
                # Level 1+: Split large components by degree
                if len(member_entities) > 5 and max_levels > 1:
                    sub_communities = self._split_by_centrality(
                        member_entities, adjacency, comp_idx, level=1
                    )
                    communities.extend(sub_communities)
        
        # If no multi-entity components, create single community
        if not communities:
            return self._create_single_community(entities, 0)
        
        return communities
    
    def _split_by_centrality(
        self,
        entities: List[Entity],
        adjacency: Dict[str, List[Tuple[str, float]]],
        base_index: int,
        level: int,
    ) -> List[Community]:
        """Split community by node centrality."""
        # Calculate degree centrality
        degrees = {}
        for e in entities:
            degrees[e.id] = len(adjacency.get(e.id, []))
        
        # Sort by degree
        sorted_entities = sorted(entities, key=lambda e: degrees.get(e.id, 0), reverse=True)
        
        # Split into high-degree hub and periphery
        mid = len(sorted_entities) // 2
        hubs = sorted_entities[:mid]
        periphery = sorted_entities[mid:]
        
        communities = []
        
        if len(hubs) >= 2:
            communities.append(self._create_community(hubs, level, base_index * 10))
        
        if len(periphery) >= 2:
            communities.append(self._create_community(periphery, level, base_index * 10 + 1))
        
        return communities
    
    def _create_community(
        self,
        entities: List[Entity],
        level: int,
        community_index: int,
    ) -> Community:
        """Create a community object from entities."""
        # Generate title from entity types
        type_counts = defaultdict(int)
        for e in entities:
            type_counts[e.type] += 1
        
        dominant_type = max(type_counts, key=type_counts.get) if type_counts else "MIXED"
        
        # Generate summary from entity descriptions
        descriptions = [e.description for e in entities if e.description][:5]
        summary = " ".join(descriptions) if descriptions else f"Community of {len(entities)} {dominant_type} entities"
        
        return Community(
            id=f"comm_{level}_{community_index}_{uuid.uuid4().hex[:8]}",
            level=level,
            title=f"{dominant_type} Community ({len(entities)} entities)",
            summary=summary[:500],  # Limit summary length
            entity_ids=[e.id for e in entities],
        )
    
    def _create_single_community(self, entities: List[Entity], level: int) -> List[Community]:
        """Create a single community containing all entities."""
        if not entities:
            return []
        
        return [Community(
            id=f"comm_{level}_0_{uuid.uuid4().hex[:8]}",
            level=level,
            title=f"All Entities ({len(entities)} total)",
            summary="Single community containing all extracted entities.",
            entity_ids=[e.id for e in entities],
        )]
    
    async def generate_community_summary(
        self,
        entities: List[Entity],
    ) -> Tuple[str, str]:
        """
        Generate an AI-powered summary and title for a community.
        
        Uses LLM to synthesize entity information into a coherent
        community summary.
        
        Args:
            entities: List of entities in the community
            
        Returns:
            Tuple of (summary, title)
        """
        from app.services.llm import get_llm_service
        
        if not entities:
            return ("Empty community", "Empty Community")
        
        # Build entity context
        entity_descriptions = []
        type_counts = defaultdict(int)
        
        for e in entities:
            type_counts[e.type] += 1
            if e.description:
                entity_descriptions.append(f"- {e.name} ({e.type}): {e.description}")
        
        dominant_type = max(type_counts, key=type_counts.get) if type_counts else "MIXED"
        
        # Limit context length
        entity_context = "\n".join(entity_descriptions[:20])
        
        prompt = f"""Analyze the following entities from a knowledge graph community and generate:
1. A concise title (max 50 chars) describing the community's theme
2. A comprehensive summary (max 500 chars) explaining what these entities have in common and their significance

Entities ({len(entities)} total, dominant type: {dominant_type}):
{entity_context}

Respond in valid JSON format:
{{"title": "...", "summary": "..."}}"""

        try:
            llm_service = get_llm_service()
            response = await llm_service.generate(prompt, max_tokens=300)
            
            # Parse JSON response
            import json
            result = json.loads(response)
            
            return (
                result.get("summary", f"Community of {len(entities)} {dominant_type} entities")[:500],
                result.get("title", f"{dominant_type} Community")[:50],
            )
            
        except Exception as e:
            # Fallback to simple generation
            import logging
            logging.getLogger(__name__).warning(f"LLM summary generation failed: {e}")
            
            descriptions = [e.description for e in entities if e.description][:5]
            summary = " ".join(descriptions) if descriptions else f"Community of {len(entities)} {dominant_type} entities"
            
            return (summary[:500], f"{dominant_type} Community ({len(entities)} entities)")

    def index_community_summaries(
        self,
        communities: List[Community],
        layer_id: str,
    ) -> int:
        """
        Embed and index community summaries into LanceDB for Global Search.
        
        This enables the system to answer high-level thematic queries by
        searching community summaries rather than individual chunks.
        
        Args:
            communities: List of communities to index
            layer_id: Layer ID for ReBAC filtering (CRITICAL for security)
            
        Returns:
            Number of communities indexed
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not communities:
            logger.info("No communities to index")
            return 0
        
        try:
            from app.services.embedding import get_embedding_service
            from app.services.vector_store import VectorStore
            
            embedding_service = get_embedding_service()
            vector_store = VectorStore()
            
            records = []
            
            for community in communities:
                if not community.summary:
                    continue
                
                # Embed the summary
                embedding = embedding_service.embed(community.summary)
                
                # Create record with security metadata
                record = {
                    "id": f"comm_summary_{community.id}",
                    "vector": embedding,
                    "content": community.summary,
                    "title": community.title,
                    "layer_id": layer_id,  # CRITICAL: Enables ReBAC filtering
                    "level": community.level,
                    "entity_ids": community.entity_ids,
                    "source_type": "community_summary",
                }
                records.append(record)
            
            if records:
                # Insert into dedicated community_summaries table
                vector_store.add_chunks(
                    records, 
                    table_name="community_summaries"
                )
                logger.info(f"Indexed {len(records)} community summaries for layer {layer_id}")
            
            return len(records)
            
        except Exception as e:
            logger.error(f"Failed to index community summaries: {e}")
            return 0


# Singleton
_detector: Optional[CommunityDetector] = None

def get_community_detector() -> CommunityDetector:
    global _detector
    if _detector is None:
        _detector = CommunityDetector()
    return _detector

