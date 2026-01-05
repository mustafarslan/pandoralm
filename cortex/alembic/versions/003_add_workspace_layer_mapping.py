"""Add workspace_layer_mappings and is_global flag

Revision ID: 003_add_workspace_layer_mapping
Revises: 002_add_layer_quotas
Create Date: 2026-01-05

Phase 5-3: Federated Knowledge Architecture
"""
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_add_workspace_layer_mapping'
down_revision: Union[str, None] = '002_add_layer_quotas'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add is_global column to layers table
    op.add_column('layers', sa.Column('is_global', sa.Boolean(), server_default='false', nullable=False))
    
    # 2. Create workspace_layer_mappings table
    op.create_table(
        'workspace_layer_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('workspace_id', sa.String(255), nullable=False),
        sa.Column('layer_id', postgresql.UUID(as_uuid=False), 
                  sa.ForeignKey('layers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('access_mode', sa.String(20), server_default='read', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # Create index on workspace_id for fast lookups
    op.create_index(
        'ix_workspace_layer_mappings_workspace_id',
        'workspace_layer_mappings',
        ['workspace_id'],
        unique=False
    )
    
    # 3. Update existing System Public layer to be global
    op.execute("""
        UPDATE layers 
        SET is_global = true 
        WHERE type = 'SYSTEM'
    """)
    
    # 4. Seed Global Organization Layer (if not exists)
    # Using fixed UUIDs for idempotency
    op.execute("""
        INSERT INTO layers (id, name, type, color, is_global, quota_tier, storage_quota_bytes)
        VALUES (
            'a0000000-0000-0000-0000-000000000002',
            'Global Organization',
            'ORGANIZATION',
            'violet',
            true,
            'ENTERPRISE',
            1099511627776  -- 1TB
        )
        ON CONFLICT (name) DO NOTHING
    """)
    
    # 5. Seed Global Engineering Layer (if not exists)
    op.execute("""
        INSERT INTO layers (id, name, type, color, is_global, quota_tier, storage_quota_bytes)
        VALUES (
            'a0000000-0000-0000-0000-000000000003',
            'Global Engineering',
            'TEAM',
            'blue',
            true,
            'ENTERPRISE',
            1099511627776  -- 1TB
        )
        ON CONFLICT (name) DO NOTHING
    """)


def downgrade() -> None:
    # Drop table
    op.drop_table('workspace_layer_mappings')
    
    # Drop column
    op.drop_column('layers', 'is_global')
