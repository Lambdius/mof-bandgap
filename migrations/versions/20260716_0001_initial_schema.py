"""Create the initial database schema.

Revision ID: 20260716_0001
Revises:
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260716_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mof_structures",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("has_file", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("metal", sa.String(), nullable=True),
        sa.Column("linker_code", sa.String(), nullable=True),
        sa.Column("group", sa.String(), nullable=True),
        sa.Column("metal2", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.Column("density", sa.Float(), nullable=True),
        sa.Column("av_void_fraction", sa.Float(), nullable=True),
        sa.Column("gsa", sa.Float(), nullable=True),
        sa.Column("vsa", sa.Float(), nullable=True),
        sa.Column("lcd", sa.Float(), nullable=True),
        sa.Column("poav_void_fraction", sa.Float(), nullable=True),
        sa.Column("e_f", sa.Float(), nullable=True),
        sa.Column("e_b", sa.Float(), nullable=True),
        sa.Column("band_gap", sa.Float(), nullable=True),
        sa.Column("dbc_up", sa.Float(), nullable=True),
        sa.Column("dbc_down", sa.Float(), nullable=True),
        sa.Column("metal_center", sa.String(), nullable=True),
        sa.Column("linker", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mof_structures_name"), "mof_structures", ["name"], unique=True)

    op.create_table(
        "datasets",
        sa.Column("mof_structure_id", sa.Uuid(), nullable=False),
        sa.Column("metal_descriptors", postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column("metal2_descriptors", postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column("linker_descriptors", postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column("edge_index", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("edge_distances", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("linker_fingerprint", sa.LargeBinary(), nullable=False),
        sa.Column("atomic_numbers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("has_interior_metal", sa.Boolean(), nullable=False),
        sa.Column("smiles", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["mof_structure_id"], ["mof_structures.id"]),
        sa.PrimaryKeyConstraint("mof_structure_id"),
    )


def downgrade() -> None:
    op.drop_table("datasets")
    op.drop_index(op.f("ix_mof_structures_name"), table_name="mof_structures")
    op.drop_table("mof_structures")
