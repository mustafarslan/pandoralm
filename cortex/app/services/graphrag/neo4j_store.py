"""
Neo4j GraphStore Adapter for GraphRAG
Implements persistent graph storage using Neo4j instead of NetworkX
"""
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable

from app.core.config import settings


@dataclass
class Entity:
    """A knowledge graph entity."""
    id: str
    name: str
    type: str
    description: str
    source_documents: List[str]
    properties: Dict[str, Any] = None
    
    def model_dump(self) -> dict:
        # Neo4j doesn't support nested Maps - serialize to JSON string
        props_json = json.dumps(self.properties) if self.properties else "{}"
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "source_documents": self.source_documents,
            "properties_json": props_json,  # Serialized as string for Neo4j
        }


@dataclass
class Relationship:
    """A relationship between entities."""
    id: str
    source_id: str
    target_id: str
    type: str
    description: str
    weight: float = 1.0
    
    def model_dump(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type,
            "description": self.description,
            "weight": self.weight,
        }


@dataclass
class Community:
    """A detected community in the graph."""
    id: str
    level: int
    title: str
    summary: str
    entity_ids: List[str]
    
    def model_dump(self) -> dict:
        return {
            "id": self.id,
            "level": self.level,
            "title": self.title,
            "summary": self.summary,
            "entity_ids": self.entity_ids,
        }


class Neo4jGraphStore:
    """
    Neo4j-backed graph store for GraphRAG.
    
    Replaces in-memory NetworkX with persistent Neo4j storage.
    Provides Cypher queries for graph traversal and community queries.
    """
    
    def __init__(
        self,
        uri: str = None,
        user: str = None,
        password: str = None,
    ):
        self.uri = uri or settings.NEO4J_URI
        self.user = user or settings.NEO4J_USER
        self.password = password or settings.NEO4J_PASSWORD
        self._driver: Optional[Driver] = None
    
    @property
    def driver(self) -> Driver:
        """Lazy initialization of Neo4j driver."""
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
        return self._driver
    
    def close(self) -> None:
        """Close the database connection."""
        if self._driver:
            self._driver.close()
            self._driver = None
    
    def verify_connectivity(self) -> bool:
        """Verify connection to Neo4j."""
        try:
            self.driver.verify_connectivity()
            return True
        except ServiceUnavailable:
            return False
    
    # ========================================
    # Schema Management
    # ========================================
    
    def create_indexes(self, workspace_id: str) -> None:
        """Create indexes for efficient queries."""
        queries = [
            # Entity indexes
            "CREATE INDEX entity_id IF NOT EXISTS FOR (e:Entity) ON (e.id)",
            "CREATE INDEX entity_workspace IF NOT EXISTS FOR (e:Entity) ON (e.workspace_id)",
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            # Community indexes
            "CREATE INDEX community_id IF NOT EXISTS FOR (c:Community) ON (c.id)",
            "CREATE INDEX community_workspace IF NOT EXISTS FOR (c:Community) ON (c.workspace_id)",
            "CREATE INDEX community_level IF NOT EXISTS FOR (c:Community) ON (c.level)",
        ]
        with self.driver.session() as session:
            for query in queries:
                session.run(query)
    
    # ========================================
    # Entity Operations
    # ========================================
    
    def upsert_entity(self, entity: Entity, workspace_id: str) -> None:
        """Insert or update an entity."""
        props_json = json.dumps(entity.properties) if entity.properties else "{}"
        query = """
        MERGE (e:Entity {id: $id, workspace_id: $workspace_id})
        SET e.name = $name,
            e.type = $type,
            e.description = $description,
            e.source_documents = $source_documents,
            e.properties_json = $properties_json,
            e.layer_id = $workspace_id,  
            e.updated_at = datetime()
        """
        with self.driver.session() as session:
            session.run(
                query,
                id=entity.id,
                workspace_id=workspace_id,
                name=entity.name,
                type=entity.type,
                description=entity.description,
                source_documents=entity.source_documents,
                properties_json=props_json,
            )
    
    def upsert_entities_batch(self, entities: List[Entity], workspace_id: str) -> None:
        """Batch insert/update entities."""
        query = """
        UNWIND $entities AS ent
        MERGE (e:Entity {id: ent.id, workspace_id: $workspace_id})
        SET e.name = ent.name,
            e.type = ent.type,
            e.description = ent.description,
            e.source_documents = ent.source_documents,
            e.properties_json = ent.properties_json,
            e.layer_id = $workspace_id,
            e.updated_at = datetime()
        """
        with self.driver.session() as session:
            session.run(
                query,
                entities=[e.model_dump() for e in entities],
                workspace_id=workspace_id,
            )
    
    def get_entity(self, entity_id: str, workspace_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        query = """
        MATCH (e:Entity {id: $id, workspace_id: $workspace_id})
        RETURN e
        """
        with self.driver.session() as session:
            result = session.run(query, id=entity_id, workspace_id=workspace_id)
            record = result.single()
            if record:
                node = record["e"]
                return Entity(
                    id=node["id"],
                    name=node["name"],
                    type=node["type"],
                    description=node["description"],
                    source_documents=node.get("source_documents", []),
                    properties=node.get("properties", {}),
                )
        return None
    
    def get_entities(
        self,
        workspace_id: str,
        entity_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Entity]:
        """Get entities with optional type filter."""
        if workspace_id == "*":
            # Global Query
            if entity_type:
                query = """
                MATCH (e:Entity {type: $type})
                RETURN e
                LIMIT $limit
                """
                params = {"type": entity_type, "limit": limit}
            else:
                query = """
                MATCH (e:Entity)
                RETURN e
                LIMIT $limit
                """
                params = {"limit": limit}
        elif entity_type:
             query = """
             MATCH (e:Entity {workspace_id: $workspace_id, type: $type})
             RETURN e
             LIMIT $limit
             """
             params = {"workspace_id": workspace_id, "type": entity_type, "limit": limit}
        else:
            query = """
            MATCH (e:Entity {workspace_id: $workspace_id})
            RETURN e
            LIMIT $limit
            """
            params = {"workspace_id": workspace_id, "limit": limit}
        
        entities = []
        with self.driver.session() as session:
            result = session.run(query, **params)
            for record in result:
                node = record["e"]
                entities.append(Entity(
                    id=node["id"],
                    name=node["name"],
                    type=node["type"],
                    description=node["description"],
                    source_documents=node.get("source_documents", []),
                    properties=node.get("properties", {}),
                ))
        return entities
    
    # ========================================
    # Relationship Operations
    # ========================================
    
    def upsert_relationship(self, rel: Relationship, workspace_id: str) -> None:
        """Insert or update a relationship between entities."""
        query = """
        MATCH (a:Entity {id: $source_id, workspace_id: $workspace_id})
        MATCH (b:Entity {id: $target_id, workspace_id: $workspace_id})
        MERGE (a)-[r:RELATES_TO {id: $rel_id}]->(b)
        SET r.type = $rel_type,
            r.description = $description,
            r.weight = $weight,
            r.layer_id = $workspace_id,
            r.updated_at = datetime()
        """
        with self.driver.session() as session:
            session.run(
                query,
                rel_id=rel.id,
                source_id=rel.source_id,
                target_id=rel.target_id,
                workspace_id=workspace_id,
                rel_type=rel.type,
                description=rel.description,
                weight=rel.weight,
            )
    
    def upsert_relationships_batch(self, relationships: List[Relationship], workspace_id: str) -> None:
        """Batch insert/update relationships."""
        query = """
        UNWIND $relationships AS rel
        MATCH (a:Entity {id: rel.source_id, workspace_id: $workspace_id})
        MATCH (b:Entity {id: rel.target_id, workspace_id: $workspace_id})
        MERGE (a)-[r:RELATES_TO {id: rel.id}]->(b)
        SET r.type = rel.type,
            r.description = rel.description,
            r.weight = rel.weight,
            r.layer_id = $workspace_id,
            r.updated_at = datetime()
        """
        with self.driver.session() as session:
            session.run(
                query,
                relationships=[r.model_dump() for r in relationships],
                workspace_id=workspace_id,
            )
    
    def get_relationships(
        self,
        workspace_id: str,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Relationship]:
        """Get relationships with optional filters."""
        conditions = ["e.workspace_id = $workspace_id"]
        params: Dict[str, Any] = {"workspace_id": workspace_id, "limit": limit}
        
        if source_id:
            conditions.append("a.id = $source_id")
            params["source_id"] = source_id
        if target_id:
            conditions.append("b.id = $target_id")
            params["target_id"] = target_id
        
        if workspace_id == "*":
             query = f"""
             MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity)
             WHERE 1=1
             {"AND a.id = $source_id" if source_id else ""}
             {"AND b.id = $target_id" if target_id else ""}
             RETURN r, a.id AS source_id, b.id AS target_id
             LIMIT $limit
             """
        else:
             query = f"""
             MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity)
             WHERE a.workspace_id = $workspace_id
             {"AND a.id = $source_id" if source_id else ""}
             {"AND b.id = $target_id" if target_id else ""}
             RETURN r, a.id AS source_id, b.id AS target_id
             LIMIT $limit
             """
        
        relationships = []
        with self.driver.session() as session:
            result = session.run(query, **params)
            for record in result:
                rel = record["r"]
                relationships.append(Relationship(
                    id=rel["id"],
                    source_id=record["source_id"],
                    target_id=record["target_id"],
                    type=rel["type"],
                    description=rel["description"],
                    weight=rel.get("weight", 1.0),
                ))
        return relationships
    
    # ========================================
    # Community Operations
    # ========================================
    
    def upsert_community(self, community: Community, workspace_id: str) -> None:
        """Insert or update a community."""
        query = """
        MERGE (c:Community {id: $id, workspace_id: $workspace_id})
        SET c.level = $level,
            c.title = $title,
            c.summary = $summary,
            c.entity_ids = $entity_ids,
            c.updated_at = datetime()
        """
        with self.driver.session() as session:
            session.run(
                query,
                id=community.id,
                workspace_id=workspace_id,
                level=community.level,
                title=community.title,
                summary=community.summary,
                entity_ids=community.entity_ids,
            )
    
    def get_communities(
        self,
        workspace_id: str,
        level: Optional[int] = None,
    ) -> List[Community]:
        """Get communities with optional level filter."""
        if level is not None:
            query = """
            MATCH (c:Community {workspace_id: $workspace_id, level: $level})
            RETURN c
            ORDER BY size(c.entity_ids) DESC
            """
            params = {"workspace_id": workspace_id, "level": level}
        else:
            query = """
            MATCH (c:Community {workspace_id: $workspace_id})
            RETURN c
            ORDER BY c.level, size(c.entity_ids) DESC
            """
            params = {"workspace_id": workspace_id}
        
        communities = []
        with self.driver.session() as session:
            result = session.run(query, **params)
            for record in result:
                node = record["c"]
                communities.append(Community(
                    id=node["id"],
                    level=node["level"],
                    title=node["title"],
                    summary=node["summary"],
                    entity_ids=node.get("entity_ids", []),
                ))
        return communities
    
    def get_communities_for_entities(
        self,
        entity_ids: List[str],
        workspace_id: str,
    ) -> List[Community]:
        """
        Find communities that contain any of the given entities.
        
        Used for dirty flagging during incremental indexing - identifies
        which communities are affected by newly added/updated entities.
        
        Args:
            entity_ids: List of entity IDs to check
            workspace_id: Workspace to search in
            
        Returns:
            List of communities containing at least one of the entities
        """
        if not entity_ids:
            return []
        
        query = """
        MATCH (c:Community {workspace_id: $workspace_id})
        WHERE ANY(eid IN c.entity_ids WHERE eid IN $entity_ids)
        RETURN DISTINCT c
        ORDER BY c.level
        """
        
        communities = []
        with self.driver.session() as session:
            result = session.run(
                query,
                workspace_id=workspace_id,
                entity_ids=entity_ids,
            )
            for record in result:
                node = record["c"]
                communities.append(Community(
                    id=node["id"],
                    level=node["level"],
                    title=node["title"],
                    summary=node["summary"],
                    entity_ids=node.get("entity_ids", []),
                ))
        return communities
    
    def get_community_by_id(
        self,
        community_id: str,
        workspace_id: str,
    ) -> Optional[Community]:
        """
        Get a single community by ID.
        
        Args:
            community_id: Community ID to fetch
            workspace_id: Workspace the community belongs to
            
        Returns:
            Community if found, None otherwise
        """
        query = """
        MATCH (c:Community {id: $id, workspace_id: $workspace_id})
        RETURN c
        """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                id=community_id,
                workspace_id=workspace_id,
            )
            record = result.single()
            if record:
                node = record["c"]
                return Community(
                    id=node["id"],
                    level=node["level"],
                    title=node["title"],
                    summary=node["summary"],
                    entity_ids=node.get("entity_ids", []),
                )
        return None
    
    def update_community_summary(
        self,
        community_id: str,
        workspace_id: str,
        new_summary: str,
        new_title: Optional[str] = None,
    ) -> bool:
        """
        Update a community's summary (and optionally title).
        
        Used by the nightly summarizer to regenerate stale community summaries.
        
        Args:
            community_id: Community to update
            workspace_id: Workspace the community belongs to
            new_summary: New AI-generated summary
            new_title: Optional new title
            
        Returns:
            True if community was updated, False if not found
        """
        if new_title:
            query = """
            MATCH (c:Community {id: $id, workspace_id: $workspace_id})
            SET c.summary = $summary,
                c.title = $title,
                c.updated_at = datetime()
            RETURN c
            """
            params = {
                "id": community_id,
                "workspace_id": workspace_id,
                "summary": new_summary,
                "title": new_title,
            }
        else:
            query = """
            MATCH (c:Community {id: $id, workspace_id: $workspace_id})
            SET c.summary = $summary,
                c.updated_at = datetime()
            RETURN c
            """
            params = {
                "id": community_id,
                "workspace_id": workspace_id,
                "summary": new_summary,
            }
        
        with self.driver.session() as session:
            result = session.run(query, **params)
            return result.single() is not None
    
    # ========================================
    # GraphRAG Query Methods
    # ========================================
    
    def local_search(
        self,
        query_entities: List[str],
        workspace_id: str,
        allowed_layers: List[str] = None, # New
        hops: int = 2,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Local search: Find entities and their immediate neighborhood.
        """
        # Security Filter
        layer_filter = ""
        if allowed_layers:
             layer_filter = "AND e.layer_id IN $allowed_layers"
        else:
             # Default to public/default if no context (or strict deny)
             layer_filter = "AND e.layer_id IN ['default', 'public']"
             
        cypher = f"""
        MATCH (e:Entity {{workspace_id: $workspace_id}})
        WHERE (e.name IN $query_entities OR e.id IN $query_entities)
        {layer_filter}
        CALL {{
            WITH e
            MATCH path = (e)-[*1..$hops]-(related:Entity)
            WHERE related.layer_id IN $allowed_layers OR related.layer_id IN ['default', 'public']
            RETURN related, relationships(path) AS rels
        }}
        WITH e, collect(DISTINCT related) AS neighborhood, collect(rels) AS all_rels
        RETURN e, neighborhood, all_rels
        LIMIT $limit
        """
        
        with self.driver.session() as session:
            result = session.run(
                cypher,
                query_entities=query_entities,
                workspace_id=workspace_id,
                allowed_layers=allowed_layers or ['default', 'public'],
                hops=hops,
                limit=limit,
            )
            
            entities = []
            relationships = []
            
            for record in result:
                # Add seed entity
                node = record["e"]
                entities.append(Entity(
                    id=node["id"],
                    name=node["name"],
                    type=node["type"],
                    description=node["description"],
                    source_documents=node.get("source_documents", []),
                ))
                
                # Add neighborhood
                for neighbor in record["neighborhood"]:
                    entities.append(Entity(
                        id=neighbor["id"],
                        name=neighbor["name"],
                        type=neighbor["type"],
                        description=neighbor["description"],
                        source_documents=neighbor.get("source_documents", []),
                    ))
            
            return {
                "entities": entities,
                "relationships": relationships,
                "search_type": "local",
            }
    
    def global_search(
        self,
        workspace_id: str,
        allowed_layers: List[str] = None, # New
        query_keywords: List[str] = None,
        top_communities: int = 5,
    ) -> Dict[str, Any]:
        """
        Global search: Query community summaries for high-level themes.
        """
        # Security: Communities aggregate entities. 
        # A community is visible if ANY of its entities are visible? 
        # Or should communities inherit layer?
        # Assuming Communities are generated PER LAYER or have mixed visibility.
        # For MVP, we check if the Community itself belongs to the workspace.
        # Ideally, Community Summaries should filter out sensitive info during generation.
        
        # NOTE: Community nodes don't currently have layer_id in schema.
        # We rely on workspace isolation for now, or assume communities share layer of their entities.
        # Phase 2B Goal: If we added layer_id to Entity, we should check entity membership.
        
        cypher = """
        MATCH (c:Community {workspace_id: $workspace_id})
        WHERE c.level = 0
        RETURN c
        ORDER BY size(c.entity_ids) DESC
        LIMIT $limit
        """
        
        communities = []
        with self.driver.session() as session:
            result = session.run(
                cypher,
                workspace_id=workspace_id,
                limit=top_communities,
            )
            
            for record in result:
                node = record["c"]
                communities.append(Community(
                    id=node["id"],
                    level=node["level"],
                    title=node["title"],
                    summary=node["summary"],
                    entity_ids=node.get("entity_ids", []),
                ))
        
        return {
            "communities": communities,
            "search_type": "global",
            "context": "\n\n".join([c.summary for c in communities]),
        }
    
    # ========================================
    # Utility Methods
    # ========================================
    
    def get_stats(self, workspace_id: str) -> Dict[str, Any]:
        """Get graph statistics for a workspace."""
        with self.driver.session() as session:
            entity_count = session.run(
                "MATCH (e:Entity {workspace_id: $ws}) RETURN count(e) AS count",
                ws=workspace_id,
            ).single()["count"]
            
            rel_count = session.run(
                """
                MATCH (a:Entity {workspace_id: $ws})-[r:RELATES_TO]->(b)
                RETURN count(r) AS count
                """,
                ws=workspace_id,
            ).single()["count"]
            
            community_count = session.run(
                "MATCH (c:Community {workspace_id: $ws}) RETURN count(c) AS count",
                ws=workspace_id,
            ).single()["count"]
            
            entity_types = session.run(
                "MATCH (e:Entity {workspace_id: $ws}) RETURN DISTINCT e.type AS type",
                ws=workspace_id,
            )
            
            return {
                "entity_count": entity_count,
                "relationship_count": rel_count,
                "community_count": community_count,
                "entity_types": [r["type"] for r in entity_types],
            }

    def get_total_stats(self) -> Dict[str, Any]:
        """Get global graph statistics (across all workspaces)."""
        try:
            # OPTIMIZATION: Removed expensive verify_connectivity() check here
            # to prevent pool exhaustion timeouts during heavy indexing.
            # We just try the query directly.
            
            with self.driver.session() as session:
                entity_count = session.run("MATCH (e:Entity) RETURN count(e) AS count").single()["count"]
                rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"]
                community_count = session.run("MATCH (c:Community) RETURN count(c) AS count").single()["count"]
                
                return {
                    "total_nodes": entity_count,
                    "total_relationships": rel_count,
                    "total_communities": community_count
                }
        except Exception as e:
            print(f"Global Stats Error: {e}")
            return {"total_nodes": 0, "total_communities": 0}
    
    def clear_workspace(self, workspace_id: str) -> None:
        """Delete all graph data for a workspace."""
        with self.driver.session() as session:
            # Delete relationships first
            session.run(
                """
                MATCH (a:Entity {workspace_id: $ws})-[r]->(b)
                DELETE r
                """,
                ws=workspace_id,
            )
            # Delete entities
            session.run(
                "MATCH (e:Entity {workspace_id: $ws}) DELETE e",
                ws=workspace_id,
            )
            # Delete communities
            session.run(
                "MATCH (c:Community {workspace_id: $ws}) DELETE c",
                ws=workspace_id,
            )


# Singleton instance
_graph_store: Optional[Neo4jGraphStore] = None


def get_graph_store() -> Neo4jGraphStore:
    """Get or create the Neo4j graph store instance."""
    global _graph_store
    if _graph_store is None:
        _graph_store = Neo4jGraphStore()
    return _graph_store

get_neo4j_store = get_graph_store
