"""
Blue/Green Migration: Workspaces → Knowledge Layers
Phase 5-3: Enterprise Security & Governance

Workflow:
1. Initialize: Connect to Postgres + LanceDB
2. Setup Green: Create vectors_v2 table with VectorSchemaV2
3. Backfill: Create Layer entities from legacy workspaces
4. Transfer: Batch migrate vectors with layer_id injection
5. Index: Create scalar index on layer_id in Green table
6. Verify: Row count comparison (Old vs New)

Usage:
    python scripts/migration/phase5_migrate_rbac.py
    
Environment Variables:
    DATABASE_URL: Postgres connection string
    LANCEDB_URI: S3 or local path to LanceDB
    OLD_TABLE_PATTERN: Pattern for source tables (default: "vectors_*")
    NEW_TABLE_SUFFIX: Suffix for new tables (default: "_v2")
"""
import os
import sys
import asyncio
import logging
from typing import Dict, List, Optional
from uuid import uuid4
from datetime import datetime

import lancedb
import pyarrow as pa

# Add cortex to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("migration.phase5")


# Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://pandora:pandora@localhost:5432/pandora"
)
LANCEDB_URI = os.getenv("LANCEDB_URI", "./storage/lancedb")
OLD_TABLE_PATTERN = os.getenv("OLD_TABLE_PATTERN", "vectors_")
NEW_TABLE_SUFFIX = os.getenv("NEW_TABLE_SUFFIX", "_v2")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))


# V2 Schema for Green table
SCHEMA_V2 = pa.schema([
    pa.field("id", pa.string()),
    pa.field("content", pa.string()),
    pa.field("embedding", pa.list_(pa.float32())),
    pa.field("document_id", pa.string()),
    pa.field("workspace_id", pa.string()),
    pa.field("layer_id", pa.string()),
    pa.field("access_permissions", pa.list_(pa.string())),
    pa.field("visibility", pa.string()),
    pa.field("metadata", pa.string()),
    pa.field("created_at", pa.string()),
])


def get_async_url(url: str) -> str:
    """Convert sync PostgreSQL URL to async."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def connect_lancedb():
    """Connect to LanceDB (S3 or local)."""
    if LANCEDB_URI.startswith("s3://"):
        storage_options = {
            "aws_endpoint": os.getenv("AWS_ENDPOINT_URL"),
            "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "aws_region": os.getenv("AWS_REGION", "us-east-1"),
            "allow_http": "true" if "http://" in os.getenv("AWS_ENDPOINT_URL", "") else "false",
        }
        storage_options = {k: v for k, v in storage_options.items() if v}
        return lancedb.connect(LANCEDB_URI, storage_options=storage_options)
    else:
        return lancedb.connect(LANCEDB_URI)


async def create_layer_from_workspace(
    workspace_id: str,
    workspace_name: Optional[str],
    engine
) -> str:
    """Create a Layer entity in Postgres from a workspace."""
    from cortex.app.models.layer import Layer, LayerPermission, LayerType, AccessLevel
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    layer_id = str(uuid4())
    
    async with async_session() as session:
        # Check if layer already exists for this workspace
        result = await session.execute(
            text("SELECT id FROM layers WHERE name = :name"),
            {"name": workspace_name or workspace_id}
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.info(f"Layer already exists for workspace {workspace_id}: {existing}")
            return existing
        
        # Create new layer
        await session.execute(
            text("""
                INSERT INTO layers (id, name, type, color, created_at)
                VALUES (:id, :name, :type, :color, :created_at)
            """),
            {
                "id": layer_id,
                "name": workspace_name or workspace_id,
                "type": "TEAM",
                "color": "blue",
                "created_at": datetime.utcnow()
            }
        )
        
        # Create default permission (workspace members can read/write)
        perm_id = str(uuid4())
        await session.execute(
            text("""
                INSERT INTO layer_permissions (id, layer_id, role_pattern, access_level)
                VALUES (:id, :layer_id, :role_pattern, :access_level)
            """),
            {
                "id": perm_id,
                "layer_id": layer_id,
                "role_pattern": f"workspace:{workspace_id}",
                "access_level": "WRITE"
            }
        )
        
        await session.commit()
        logger.info(f"Created layer {layer_id} for workspace {workspace_id}")
        
    return layer_id


async def migrate():
    """Main migration workflow."""
    logger.info("=" * 60)
    logger.info("Phase 5-3: Blue/Green Migration - Workspaces → Layers")
    logger.info("=" * 60)
    
    # 1. Initialize connections
    logger.info("\n[Step 1] Initializing connections...")
    
    engine = create_async_engine(get_async_url(DATABASE_URL), echo=False)
    db = connect_lancedb()
    
    logger.info(f"  ✓ PostgreSQL: {DATABASE_URL.split('@')[-1]}")
    logger.info(f"  ✓ LanceDB: {LANCEDB_URI}")
    
    # 2. Discover tables to migrate
    logger.info("\n[Step 2] Discovering tables...")
    
    all_tables = db.table_names()
    migration_targets = [
        t for t in all_tables 
        if t.startswith(OLD_TABLE_PATTERN) and not t.endswith(NEW_TABLE_SUFFIX)
    ]
    
    if not migration_targets:
        logger.warning("  ⚠ No tables found to migrate.")
        return
    
    logger.info(f"  Found {len(migration_targets)} table(s) to migrate:")
    for t in migration_targets:
        logger.info(f"    - {t}")
    
    # 3. Migrate each table
    workspace_layer_map: Dict[str, str] = {}
    total_migrated = 0
    total_original = 0
    
    for old_table_name in migration_targets:
        workspace_id = old_table_name.replace(OLD_TABLE_PATTERN, "")
        workspace_id = workspace_id.replace("_", "-")  # Restore dashes
        new_table_name = f"{old_table_name}{NEW_TABLE_SUFFIX}"
        
        logger.info(f"\n[Step 3] Migrating: {old_table_name} → {new_table_name}")
        
        try:
            # 3a. Create Layer entity
            layer_id = await create_layer_from_workspace(
                workspace_id=workspace_id,
                workspace_name=workspace_id.replace("-", " ").title(),
                engine=engine
            )
            workspace_layer_map[workspace_id] = layer_id
            
            # 3b. Open source table
            old_table = db.open_table(old_table_name)
            original_count = old_table.count_rows()
            total_original += original_count
            
            logger.info(f"  Source rows: {original_count}")
            
            # 3c. Create destination table (drop if exists)
            if new_table_name in db.table_names():
                logger.warning(f"  ⚠ Dropping existing table: {new_table_name}")
                db.drop_table(new_table_name)
            
            new_table = db.create_table(new_table_name, schema=SCHEMA_V2)
            
            # 3d. Migrate in batches
            data = old_table.search().limit(None).to_arrow()
            records = data.to_pylist()
            
            new_records = []
            for row in records:
                new_row = {
                    "id": row.get("id", str(uuid4())),
                    "content": row.get("content", ""),
                    "embedding": row.get("embedding", []),
                    "document_id": row.get("document_id", ""),
                    "workspace_id": row.get("workspace_id", workspace_id),
                    "layer_id": layer_id,  # NEW: Inject layer_id
                    "access_permissions": [],  # NEW: Empty ACL
                    "visibility": "private",  # NEW: Default private
                    "metadata": row.get("metadata", "{}"),
                    "created_at": row.get("created_at", datetime.utcnow().isoformat()),
                }
                # Remove distance field if present
                if "_distance" in new_row:
                    del new_row["_distance"]
                new_records.append(new_row)
            
            if new_records:
                new_table.add(new_records)
                total_migrated += len(new_records)
            
            logger.info(f"  ✓ Migrated {len(new_records)} rows")
            
            # 3e. Create index on layer_id
            try:
                new_table.create_index("layer_id", index_type="scalar")
                logger.info(f"  ✓ Created scalar index on layer_id")
            except Exception as e:
                logger.warning(f"  ⚠ Could not create index: {e}")
            
        except Exception as e:
            logger.error(f"  ✗ Failed to migrate {old_table_name}: {e}")
            continue
    
    # 4. Verification
    logger.info("\n[Step 4] Verification")
    logger.info(f"  Original rows: {total_original}")
    logger.info(f"  Migrated rows: {total_migrated}")
    
    if total_original == total_migrated:
        logger.info("  ✓ Row counts match!")
    else:
        logger.warning(f"  ⚠ Row count mismatch! Delta: {total_original - total_migrated}")
    
    # Print workspace → layer mapping
    logger.info("\n[Step 5] Layer Mapping")
    for ws, layer in workspace_layer_map.items():
        logger.info(f"  {ws} → {layer}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Migration Complete!")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("  1. Update LANCEDB_TABLE env var to use '_v2' tables")
    logger.info("  2. Restart cortex service")
    logger.info("  3. Verify search works with layer filtering")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
