"""create complaints table

Revision ID: 20260915_0001
Revises:
Create Date: 2026-09-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260915_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "complaints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("complaint_number", sa.String(length=32), nullable=False),
        sa.Column("complaint_source", sa.String(length=255), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("product_strength_grade", sa.String(length=255), nullable=True),
        sa.Column("batch_lot_number", sa.String(length=128), nullable=False),
        sa.Column("affected_quantity", sa.String(length=128), nullable=True),
        sa.Column("manufacturing_date", sa.String(length=64), nullable=True),
        sa.Column("expiry_date", sa.String(length=64), nullable=True),
        sa.Column("complaint_date", sa.String(length=64), nullable=True),
        sa.Column("complaint_category", sa.String(length=255), nullable=False),
        sa.Column("complaint_description", sa.Text(), nullable=False),
        sa.Column("originating_site_block", sa.String(length=255), nullable=True),
        sa.Column(
            "impacted_non_product_materials", sa.String(length=512), nullable=True
        ),
        sa.Column("initial_severity", sa.String(length=64), nullable=True),
        sa.Column("priority", sa.String(length=64), nullable=True),
        sa.Column("suggested_next_action", sa.Text(), nullable=True),
        sa.Column("initial_risk_assessment", sa.Text(), nullable=False),
        sa.Column("field_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("complaint_number"),
    )
    op.create_index(
        "ix_complaints_batch_lot_number", "complaints", ["batch_lot_number"]
    )
    op.create_index("ix_complaints_product_name", "complaints", ["product_name"])
    op.create_index("ix_complaints_committed_at", "complaints", ["committed_at"])


def downgrade() -> None:
    op.drop_index("ix_complaints_committed_at", table_name="complaints")
    op.drop_index("ix_complaints_product_name", table_name="complaints")
    op.drop_index("ix_complaints_batch_lot_number", table_name="complaints")
    op.drop_table("complaints")
