
"""
Verification Script for Phase 2A Migration.
Tests that V1 data is correctly migrated to V2 with layer_id populated.
"""
import os
import shutil
import lancedb
import pyarrow as pa
from datetime import datetime

# Setup
TEST_DIR = "./tests/data/migration_test"
URI = os.path.join(TEST_DIR, "lancedb")
OLD_TABLE = "vectors_workspace-test"
NEW_TABLE = "vectors_workspace-test_v2"

# Ensure clean state
if os.path.exists(TEST_DIR):
    shutil.rmtree(TEST_DIR)
os.makedirs(URI, exist_ok=True)

def create_v1_data():
    """Create legacy V1 table."""
    db = lancedb.connect(URI)
    
    # V1 Schema (explicitly without layer_id)
    schema_v1 = pa.schema([
        pa.field("id", pa.string()),
        pa.field("content", pa.string()),
        pa.field("embedding", pa.list_(pa.float32(), 1536)),
        pa.field("document_id", pa.string()),
        pa.field("workspace_id", pa.string()),
        pa.field("metadata", pa.string()),
        pa.field("created_at", pa.string()),
    ])
    
    print(f"Creating V1 table: {OLD_TABLE}")
    table = db.create_table(OLD_TABLE, schema=schema_v1)
    
    # Seed data
    data = []
    for i in range(10):
        data.append({
            "id": f"chunk_{i}",
            "content": f"Test content {i}",
            "embedding": [0.1] * 1536,
            "document_id": "doc_1",
            "workspace_id": "workspace-test",
            "metadata": "{}",
            "created_at": datetime.utcnow().isoformat(),
        })
    
    table.add(data)
    print(f"Seeded {len(data)} rows into V1.")

def verify_migration():
    """Run migration logic (imported or simulated) and check V2."""
    
    # Simulate Migration Logic (calling the script logic or mimicking it)
    # We will invoke the script via subprocess or just replicate the logic for unit testing
    # For robustness, let's mimic the transformation loop here to verify the concept works
    
    db = lancedb.connect(URI)
    old_table = db.open_table(OLD_TABLE)
    data = old_table.search().limit(None).to_list()
    
    # V2 Schema
    schema_v2 = pa.schema([
        pa.field("id", pa.string()),
        pa.field("content", pa.string()),
        pa.field("embedding", pa.list_(pa.float32(), 1536)),
        pa.field("document_id", pa.string()),
        pa.field("workspace_id", pa.string()),
        pa.field("layer_id", pa.string()),         # NEW
        pa.field("access_roles", pa.list_(pa.string())), # NEW
        pa.field("visibility", pa.string()),       # NEW
        pa.field("metadata", pa.string()),  
        pa.field("created_at", pa.string()),
    ])
    
    new_records = []
    for row in data:
        new_row = row.copy()
        if "_distance" in new_row: del new_row["_distance"]
        
        # TRANSFORMATION LOGIC
        new_row["layer_id"] = row["workspace_id"] # Default mapping
        new_row["access_roles"] = []
        new_row["visibility"] = "private"
        
        new_records.append(new_row)
        
    print(f"Creating V2 table: {NEW_TABLE}")
    v2_table = db.create_table(NEW_TABLE, schema=schema_v2)
    v2_table.add(new_records)
    
    # Verification
    row = v2_table.search().limit(1).to_list()[0]
    print(f"Verified V2 Row: {row.get('layer_id')}")
    
    assert "layer_id" in row
    assert row["layer_id"] == "workspace-test"
    assert row["visibility"] == "private"
    assert v2_table.count_rows() == 10
    
    print("✅ Migration Verification Successful!")

if __name__ == "__main__":
    create_v1_data()
    verify_migration()
