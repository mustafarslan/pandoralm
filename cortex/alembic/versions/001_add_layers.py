"""Create layers and layer_permissions tables

Revision ID: 001_add_layers
Revises:
Create Date: 2025-12-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_add_layers'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create LayerType enum idempotently
    op.execute("""
    DO $$ BEGIN
        CREATE TYPE layertype AS ENUM ('SYSTEM', 'ORGANIZATION', 'TEAM', 'USER');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """)

    layer_type_enum = postgresql.ENUM(
        'SYSTEM', 'ORGANIZATION', 'TEAM', 'USER',
        name='layertype',
        create_type=False
    )

    # Create AccessLevel enum idempotently
    op.execute("""
    DO $$ BEGIN
        CREATE TYPE accesslevel AS ENUM ('READ', 'WRITE', 'ADMIN');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """)

    access_level_enum = postgresql.ENUM(
        'READ', 'WRITE', 'ADMIN',
        name='accesslevel',
        create_type=False
    )

    # Create layers table
    op.create_table(
        'layers',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(255), unique=True, nullable=False),
        sa.Column('type', layer_type_enum, nullable=False, server_default='TEAM'),
        sa.Column('color', sa.String(50), server_default='slate'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Create layer_permissions table
    op.create_table(
        'layer_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('layer_id', postgresql.UUID(as_uuid=False),
                  sa.ForeignKey('layers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_pattern', sa.String(255), nullable=False),
        sa.Column('access_level', access_level_enum, nullable=False, server_default='READ'),
    )

    # Create B-Tree index on role_pattern for fast lookups
    op.create_index(
        'ix_layer_permissions_role_pattern_btree',
        'layer_permissions',
        ['role_pattern'],
        unique=False
    )

    # Seed default system layer
    op.execute("""
        INSERT INTO layers (id, name, type, color)
        VALUES (
            'a0000000-0000-0000-0000-000000000001',
            'System Public',
            'SYSTEM',
            'slate'
        )
        ON CONFLICT (name) DO NOTHING
    """)

    # Seed default permission (everyone can read system public)
    op.execute("""
        INSERT INTO layer_permissions (id, layer_id, role_pattern, access_level)
        VALUES (
            'b0000000-0000-0000-0000-000000000001',
            'a0000000-0000-0000-0000-000000000001',
            '*',
            'READ'
        )
    """)


def downgrade() -> None:
    # Drop tables
    op.drop_table('layer_permissions')
    op.drop_table('layers')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS accesslevel")
    op.execute("DROP TYPE IF EXISTS layertype")
