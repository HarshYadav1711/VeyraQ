import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class Complaint(Base):
    """Persisted committed complaint record (immutable via current assessment API)."""

    __tablename__ = "complaints"
    __table_args__ = (
        Index("ix_complaints_batch_lot_number", "batch_lot_number"),
        Index("ix_complaints_product_name", "product_name"),
        Index("ix_complaints_committed_at", "committed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    complaint_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)

    complaint_source: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)

    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_strength_grade: Mapped[str | None] = mapped_column(String(255), nullable=True)
    batch_lot_number: Mapped[str] = mapped_column(String(128), nullable=False)
    affected_quantity: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manufacturing_date: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expiry_date: Mapped[str | None] = mapped_column(String(64), nullable=True)

    complaint_date: Mapped[str | None] = mapped_column(String(64), nullable=True)
    complaint_category: Mapped[str] = mapped_column(String(255), nullable=False)
    complaint_description: Mapped[str] = mapped_column(Text, nullable=False)

    originating_site_block: Mapped[str | None] = mapped_column(String(255), nullable=True)
    impacted_non_product_materials: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )

    initial_severity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(64), nullable=True)
    suggested_next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    initial_risk_assessment: Mapped[str] = mapped_column(Text, nullable=False)

    # Provenance/confidence/evidence only — values live in the columns above.
    field_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
