"""
Insert fictional committed complaint history for demo / future duplicate detection.

Idempotent: skips records whose CMP-DEMO-* complaint numbers already exist.

Usage (from backend/ with venv active):

    python -m app.scripts.seed_demo_complaints

Does not run automatically on API startup.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.models.complaint import Complaint
from app.db.session import SessionLocal

# Fixed demo complaint numbers — distinct from runtime CMP-{year}-{suffix} ids.
SEED_COMPLAINTS: list[dict] = [
    {
        "id": uuid.UUID("11111111-1111-4111-8111-111111111101"),
        "complaint_number": "CMP-DEMO-0001",
        "complaint_source": "Email",
        "customer_name": "Northbridge Pharmacy",
        "product_name": "Cefixime Capsules",
        "product_strength_grade": "200 mg",
        "batch_lot_number": "CFX260481",
        "affected_quantity": "120 capsules",
        "manufacturing_date": "January 2026",
        "expiry_date": "December 2027",
        "complaint_date": "10 March 2026",
        "complaint_category": "Product Defect – Discoloration",
        "complaint_description": (
            "Brown discoloration observed on multiple Cefixime Capsules 200 mg "
            "from batch CFX260481."
        ),
        "originating_site_block": "Block B",
        "impacted_non_product_materials": None,
        "initial_severity": "Medium",
        "priority": "High",
        "suggested_next_action": "Quarantine remaining stock and investigate batch CFX260481.",
        "initial_risk_assessment": (
            "Potential batch-related appearance defect; advisory investigation recommended."
        ),
        "offset_days": 20,
    },
    {
        "id": uuid.UUID("11111111-1111-4111-8111-111111111102"),
        "complaint_number": "CMP-DEMO-0002",
        "complaint_source": "Phone",
        "customer_name": "Lakeside Distributors",
        "product_name": "Cefixime Capsules",
        "product_strength_grade": "200 mg",
        "batch_lot_number": "CFX260481",
        "affected_quantity": "60 capsules",
        "manufacturing_date": "January 2026",
        "expiry_date": "December 2027",
        "complaint_date": "14 March 2026",
        "complaint_category": "Product Defect – Discoloration",
        "complaint_description": (
            "Similar brown discoloration reported on Cefixime Capsules 200 mg, "
            "batch CFX260481, received by a different customer."
        ),
        "originating_site_block": "Block B",
        "impacted_non_product_materials": None,
        "initial_severity": "Medium",
        "priority": "High",
        "suggested_next_action": "Link to related discoloration complaints for batch CFX260481.",
        "initial_risk_assessment": (
            "Recurring appearance concern on the same batch; escalate batch review."
        ),
        "offset_days": 16,
    },
    {
        "id": uuid.UUID("11111111-1111-4111-8111-111111111103"),
        "complaint_number": "CMP-DEMO-0003",
        "complaint_source": "Document",
        "customer_name": "Apex Hospital Pharmacy",
        "product_name": "Metformin Hydrochloride Tablets",
        "product_strength_grade": "500 mg",
        "batch_lot_number": "MTH250912",
        "affected_quantity": "2 bottles",
        "manufacturing_date": "September 2025",
        "expiry_date": "August 2027",
        "complaint_date": "2 March 2026",
        "complaint_category": "Packaging Defect",
        "complaint_description": "Bottle seal incomplete; cotton insert missing on receipt.",
        "originating_site_block": "Packaging Line 3",
        "impacted_non_product_materials": "Bottle seal, cotton insert",
        "initial_severity": "Low",
        "priority": "Medium",
        "suggested_next_action": "Review packaging line checks for MTH250912.",
        "initial_risk_assessment": "Localized packaging integrity issue; limited patient exposure risk.",
        "offset_days": 28,
    },
    {
        "id": uuid.UUID("11111111-1111-4111-8111-111111111104"),
        "complaint_number": "CMP-DEMO-0004",
        "complaint_source": "Email",
        "customer_name": "Summit API Trading",
        "product_name": "Ibuprofen API",
        "product_strength_grade": "Ph. Eur. grade",
        "batch_lot_number": "IBU-API-260118",
        "affected_quantity": "25 kg",
        "manufacturing_date": "January 2026",
        "expiry_date": None,
        "complaint_date": "5 March 2026",
        "complaint_category": "Foreign Particulate",
        "complaint_description": "Dark particulate matter observed in sampled Ibuprofen API drums.",
        "originating_site_block": "API Plant 2",
        "impacted_non_product_materials": "Drum liner",
        "initial_severity": "High",
        "priority": "High",
        "suggested_next_action": "Hold batch and open investigation for foreign matter.",
        "initial_risk_assessment": "API contamination risk; halt further release pending findings.",
        "offset_days": 25,
    },
    {
        "id": uuid.UUID("11111111-1111-4111-8111-111111111105"),
        "complaint_number": "CMP-DEMO-0005",
        "complaint_source": "Email",
        "customer_name": "Riverdale Clinic Store",
        "product_name": "Amoxicillin Capsules",
        "product_strength_grade": "500 mg",
        "batch_lot_number": "AMX240811",
        "affected_quantity": "30 capsules",
        "manufacturing_date": "August 2024",
        "expiry_date": "July 2026",
        "complaint_date": "18 February 2026",
        "complaint_category": "Capsule Integrity",
        "complaint_description": "Several capsules found cracked or empty in blister pack.",
        "originating_site_block": "FDF Suite A",
        "impacted_non_product_materials": "Blister foil",
        "initial_severity": "Medium",
        "priority": "Medium",
        "suggested_next_action": "Inspect retained samples for AMX240811.",
        "initial_risk_assessment": "Dose integrity concern for affected packs; review filling process.",
        "offset_days": 40,
    },
]


def _metadata_for(row: dict) -> dict:
    keys = [
        "complaint_source",
        "customer_name",
        "product_name",
        "product_strength_grade",
        "batch_lot_number",
        "affected_quantity",
        "manufacturing_date",
        "expiry_date",
        "complaint_date",
        "complaint_category",
        "complaint_description",
        "originating_site_block",
        "impacted_non_product_materials",
        "initial_severity",
        "priority",
        "suggested_next_action",
        "initial_risk_assessment",
    ]
    metadata: dict[str, dict] = {}
    for key in keys:
        value = row.get(key)
        metadata[key] = {
            "provenance": "missing" if value is None else "source",
            "confidence": None if value is None else 0.9,
            "evidence": None,
        }
    return metadata


def seed_demo_complaints() -> int:
    inserted = 0
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        for row in SEED_COMPLAINTS:
            exists = session.scalar(
                select(Complaint.id).where(
                    Complaint.complaint_number == row["complaint_number"]
                )
            )
            if exists is not None:
                continue

            committed_at = now - timedelta(days=int(row["offset_days"]))
            complaint = Complaint(
                id=row["id"],
                complaint_number=row["complaint_number"],
                complaint_source=row["complaint_source"],
                customer_name=row["customer_name"],
                product_name=row["product_name"],
                product_strength_grade=row["product_strength_grade"],
                batch_lot_number=row["batch_lot_number"],
                affected_quantity=row["affected_quantity"],
                manufacturing_date=row["manufacturing_date"],
                expiry_date=row["expiry_date"],
                complaint_date=row["complaint_date"],
                complaint_category=row["complaint_category"],
                complaint_description=row["complaint_description"],
                originating_site_block=row["originating_site_block"],
                impacted_non_product_materials=row["impacted_non_product_materials"],
                initial_severity=row["initial_severity"],
                priority=row["priority"],
                suggested_next_action=row["suggested_next_action"],
                initial_risk_assessment=row["initial_risk_assessment"],
                field_metadata=_metadata_for(row),
                created_at=committed_at,
                committed_at=committed_at,
            )
            session.add(complaint)
            inserted += 1
        session.commit()
    return inserted


def main() -> None:
    count = seed_demo_complaints()
    print(f"Seeded {count} demo complaint(s).")


if __name__ == "__main__":
    main()
