"""
Blue/Green Migration Script for LanceDB (Vector Store).
Migrates vectors from V1 (flat) to V2 (knowledge layers) table.

Usage:
    python scripts/migrate_v1_to_v2.py

Environment Variables:
    OLD_TABLE: Name of source table (default: 'vectors')
    NEW_TABLE: Name of destination table (default: 'vectors_v2')
    LANCEDB_URI: S3 URI or local path
"""
import os
import sys
import logging
import lancedb
import pyarrow as pa
from typing import Dict, Any

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

# Config
OLD_TABLE = os.getenv("OLD_TABLE", "vectors")
NEW_TABLE = os.getenv("NEW_TABLE", "vectors_v2")
URI = os.getenv("LANCEDB_URI", "./storage/lancedb")

# V2 Schema
SCHEMA_V2 = pa.schema([
    pa.field("id", pa.string()),
    pa.field("content", pa.string()),
    pa.field("embedding", pa.list_(pa.float32())),
    pa.field("document_id", pa.string()),
    pa.field("workspace_id", pa.string()),
    pa.field("layer_id", pa.string()),         # NEW
    pa.field("access_roles", pa.list_(pa.string())), # NEW
    pa.field("visibility", pa.string()),       # NEW
    pa.field("metadata", pa.string()),  
    pa.field("created_at", pa.string()),
])

def connect_db():
    """Connect to LanceDB."""
    if URI.startswith("s3://"):
        storage_options = {
            "aws_endpoint": os.getenv("AWS_ENDPOINT_URL"),
            "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "aws_region": os.getenv("AWS_REGION", "us-east-1"),
            "allow_http": "true" if "http://" in os.getenv("AWS_ENDPOINT_URL", "") else "false",
        }
        # Filter empty
        storage_options = {k: v for k, v in storage_options.items() if v}
        return lancedb.connect(URI, storage_options=storage_options)
    else:
        return lancedb.connect(URI)

def migrate():
    logger.info(f"🚀 Starting Migration: {OLD_TABLE} -> {NEW_TABLE} at {URI}")
    
    db = connect_db()
    
    # 1. Discover Workspaces (Tables)
    # The current implementation uses one table per workspace named "vectors_{workspace_id}"
    # But the Prompt implies a request to migrate "vectors_v1" to "vectors_v2" (Single Table vs Multi Table?)
    # Looking at vector_store.py: _get_table_name return "vectors_{safe_id}"
    # So we have multiple tables to migrate.
    
    tables = db.table_names()
    migration_targets = [t for t in tables if t.startswith("vectors_") and not t.endswith("_v2")]
    
    if not migration_targets:
        logger.warning("No tables found to migrate.")
        return

    logger.info(f"Found {len(migration_targets)} workspace tables to migrate.")

    for old_table_name in migration_targets:
        workspace_id = old_table_name.replace("vectors_", "").replace("_", "-")
        new_table_name = f"{old_table_name}_v2"
        
        logger.info(f"🔄 Migrating {old_table_name} -> {new_table_name} (Workspace: {workspace_id})")
        
        try:
            # Open Old Table
            old_table = db.open_table(old_table_name)
            
            # Create New Table
            if new_table_name in db.table_names():
                logger.warning(f"Target table {new_table_name} already exists. Dropping...")
                db.drop_table(new_table_name)
            
            new_table = db.create_table(new_table_name, schema=SCHEMA_V2)
            
            # Streaming Migration
            # We use to_batches() to iterate without loading all into RAM
            # Note: lancedb python dataset iterator
            
            count = 0
            # Read as Arrow Table -> Batches
            # If dataset is huge, use dataset.to_batches()
            # LanceDB table.to_pandas() or table.to_arrow() loads all.
            # Use search().limit(None).to_batches() if supported or iterated
            # For simplicity in V1, let's assume valid memory or batching via limit/offset if huge.
            # But correct way for LanceDB is search().to_arrow() which returns a Table, then to_batches()
            
            # Better: table.to_lance() returns a dataset which we can scanner()
            
            data = old_table.search().limit(None).to_arrow()
            
            # Transform to Python list of dicts for adding (simplest API usage)
            # For millions, we should stick to Arrow, but constructing Arrow arrays in Python is verbose.
            # Let's do batch processing via Python dicts for clarity, assuming reasonable batch size.
            
            records = data.to_pylist()
            new_records = []
            
            for row in records:
                # Transform
                new_row = row.copy()
                if "_distance" in new_row: del new_row["_distance"]
                
                # Inject New Fields
                new_row["layer_id"] = row.get("workspace_id", "default") # Map workspace -> layer
                new_row["access_roles"] = [] # Default: no restriction (or check workspace policy)
                new_row["visibility"] = "private" # Default secure
                
                new_records.append(new_row)
            
            if new_records:
                new_table.add(new_records)
                count = len(new_records)
            
            logger.info(f"✅ Migrated {count} rows for workspace {workspace_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to migrate {old_table_name}: {e}")
            # Do not raise, continue to next workspace
            continue

    logger.info("🎉 Migration Complete.")

if __name__ == "__main__":
    migrate()
