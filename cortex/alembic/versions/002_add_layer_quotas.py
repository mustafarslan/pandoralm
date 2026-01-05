"""Add layer quotas and lifecycle fields

Revision ID: 002_add_layer_quotas
Revises: 001_add_layers
Create Date: 2026-01-03

Phase 5-3: Enterprise Security & Governance
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_add_layer_quotas'
down_revision: Union[str, None] = '001_add_layers'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create QuotaTier enum idempotently
    op.execute("""
    DO $$ BEGIN
        CREATE TYPE quotatier AS ENUM ('FREE', 'PRO', 'ENTERPRISE');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """)

    quota_tier_enum = postgresql.ENUM(
        'FREE', 'PRO', 'ENTERPRISE',
        name='quotatier',
        create_type=False
    )

    # Add columns to layers table
    op.add_column('layers', sa.Column('owner_user_id', sa.String(255), nullable=True))
    op.add_column('layers', sa.Column('quota_tier', quota_tier_enum, server_default='FREE', nullable=False))
    op.add_column('layers', sa.Column('storage_quota_bytes', sa.BigInteger(), server_default='104857600', nullable=False))
    op.add_column('layers', sa.Column('storage_used_bytes', sa.BigInteger(), server_default='0', nullable=False))
    op.add_column('layers', sa.Column('is_soft_deleted', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('layers', sa.Column('deleted_at', sa.DateTime(), nullable=True))

    # Add index on owner_user_id
    op.create_index(op.f('ix_layers_owner_user_id'), 'layers', ['owner_user_id'], unique=False)


def downgrade() -> None:
    # Drop index
    op.drop_index(op.f('ix_layers_owner_user_id'), table_name='layers')
    
    # Drop columns
    op.drop_column('layers', 'deleted_at')
    op.drop_column('layers', 'is_soft_deleted')
    op.drop_column('layers', 'storage_used_bytes')
    op.drop_column('layers', 'storage_quota_bytes')
    op.drop_column('layers', 'quota_tier')
    op.drop_column('layers', 'owner_user_id')
    
    # Drop enum
    op.execute("DROP TYPE IF EXISTS quotatier")
