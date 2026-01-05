"""add workspaces table

Revision ID: 004_add_workspaces_table
Revises: 003_add_workspace_layer_mapping
Create Date: 2026-01-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


revision = '004_add_workspaces_table'
down_revision = '003_add_workspace_layer_mapping'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()

    if 'workspaces' not in tables:
        op.create_table('workspaces',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('slug', sa.String(), nullable=False),
            sa.Column('vector_tag', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('last_updated_at', sa.DateTime(), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_workspaces_id'), 'workspaces', ['id'], unique=False)
        op.create_index(op.f('ix_workspaces_slug'), 'workspaces', ['slug'], unique=True)


def downgrade() -> None:
    # Check bounds before dropping to be safe
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()
    
    if 'workspaces' in tables:
        op.drop_index(op.f('ix_workspaces_slug'), table_name='workspaces')
        op.drop_index(op.f('ix_workspaces_id'), table_name='workspaces')
        op.drop_table('workspaces')
