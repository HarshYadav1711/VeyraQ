import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.repositories.complaint_repository import ComplaintRepository
from app.services.complaint_service import ComplaintService


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _field(
    value: str | None,
    provenance: str = "source",
    confidence: float | None = 0.9,
    evidence: str | None = None,
) -> dict:
    if value is None:
        return {
            "value": None,
            "provenance": "missing",
            "confidence": None,
            "evidence": None,
        }
    return {
        "value": value,
        "provenance": provenance,
        "confidence": confidence,
        "evidence": evidence,
    }


def valid_commit_payload(**overrides: str | None) -> dict:
    values = {
        "complaint_source": "Email",
        "customer_name": "Northbridge Pharmacy",
        "product_name": "Amoxicillin Capsules",
        "product_strength_grade": "500 mg",
        "batch_lot_number": "BMX240602",
        "affected_quantity": "48 capsules",
        "manufacturing_date": "March 2026",
        "expiry_date": "February 2028",
        "complaint_date": "15 March 2026",
        "complaint_category": "Packaging Defect",
        "complaint_description": "Blister seal incomplete on receipt.",
        "originating_site_block": "Block A",
        "impacted_non_product_materials": "Blister foil",
        "initial_severity": "Medium",
        "priority": "High",
        "suggested_next_action": "Inspect retained samples.",
        "initial_risk_assessment": "Limited packaging integrity risk; investigate batch.",
    }
    values.update(overrides)
    fields = {
        key: _field(value, provenance="user" if key == "batch_lot_number" else "source")
        for key, value in values.items()
    }
    fields["batch_lot_number"] = _field(
        values["batch_lot_number"],
        provenance="user",
        confidence=None,
        evidence=None,
    )
    return {"fields": fields}


def test_commit_returns_201_with_identifiers_and_fields(client: TestClient) -> None:
    response = client.post("/api/v1/complaints/commit", json=valid_commit_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "committed"
    assert body["complaint_number"].startswith("CMP-")
    assert body["id"]
    assert body["created_at"]
    assert body["committed_at"]
    assert body["fields"]["batch_lot_number"]["value"] == "BMX240602"
    assert body["fields"]["batch_lot_number"]["provenance"] == "user"
    assert body["fields"]["manufacturing_date"]["value"] == "March 2026"
    assert body["fields"]["expiry_date"]["value"] == "February 2028"


def test_missing_batch_lot_number_returns_422(client: TestClient) -> None:
    payload = valid_commit_payload(batch_lot_number=None)
    response = client.post("/api/v1/complaints/commit", json=payload)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "batch_lot_number" in detail["missing_fields"]


def test_whitespace_only_required_field_rejected(client: TestClient) -> None:
    payload = valid_commit_payload(customer_name="   ")
    response = client.post("/api/v1/complaints/commit", json=payload)
    assert response.status_code == 422
    assert "customer_name" in response.json()["detail"]["missing_fields"]


def test_get_complaint_by_id_and_404(client: TestClient) -> None:
    created = client.post("/api/v1/complaints/commit", json=valid_commit_payload()).json()
    fetched = client.get(f"/api/v1/complaints/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["complaint_number"] == created["complaint_number"]
    assert fetched.json()["fields"]["product_name"]["value"] == "Amoxicillin Capsules"

    missing = client.get(f"/api/v1/complaints/{uuid.uuid4()}")
    assert missing.status_code == 404


def test_history_newest_first_and_bounded(client: TestClient) -> None:
    first = client.post(
        "/api/v1/complaints/commit",
        json=valid_commit_payload(batch_lot_number="AAA111"),
    ).json()
    second = client.post(
        "/api/v1/complaints/commit",
        json=valid_commit_payload(batch_lot_number="BBB222"),
    ).json()

    history = client.get("/api/v1/complaints", params={"limit": 100})
    assert history.status_code == 200
    items = history.json()
    assert len(items) == 2
    assert items[0]["id"] == second["id"]
    assert items[1]["id"] == first["id"]

    bounded = client.get("/api/v1/complaints", params={"limit": 1})
    assert len(bounded.json()) == 1


def test_two_commits_receive_different_complaint_numbers(client: TestClient) -> None:
    a = client.post("/api/v1/complaints/commit", json=valid_commit_payload()).json()
    b = client.post(
        "/api/v1/complaints/commit",
        json=valid_commit_payload(batch_lot_number="OTHER99"),
    ).json()
    assert a["complaint_number"] != b["complaint_number"]


def test_no_update_or_delete_routes_exposed(client: TestClient) -> None:
    created = client.post("/api/v1/complaints/commit", json=valid_commit_payload()).json()
    complaint_id = created["id"]
    assert client.put(f"/api/v1/complaints/{complaint_id}", json={}).status_code == 405
    assert client.patch(f"/api/v1/complaints/{complaint_id}", json={}).status_code == 405
    assert client.delete(f"/api/v1/complaints/{complaint_id}").status_code == 405


def test_repository_persists_value_and_user_provenance(db_session: Session) -> None:
    from app.domain.complaint import ComplaintCommitRequest

    service = ComplaintService(db_session)
    response = service.commit(
        ComplaintCommitRequest.model_validate(valid_commit_payload())
    )
    repo = ComplaintRepository(db_session)
    stored = repo.get_by_id(response.id)
    assert stored is not None
    assert stored.batch_lot_number == "BMX240602"
    assert stored.field_metadata["batch_lot_number"]["provenance"] == "user"
    assert "value" not in stored.field_metadata["batch_lot_number"]

    reloaded = service.get(response.id)
    assert reloaded is not None
    assert reloaded.fields.batch_lot_number.value == "BMX240602"
    assert reloaded.fields.batch_lot_number.provenance.value == "user"


def test_persistence_failure_does_not_leak_connection_info(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise __import__("sqlalchemy.exc", fromlist=["SQLAlchemyError"]).SQLAlchemyError(
            "postgresql+psycopg://postgres:postgres@localhost:5432/veyraq secret"
        )

    monkeypatch.setattr(
        "app.repositories.complaint_repository.ComplaintRepository.add",
        boom,
    )
    response = client.post("/api/v1/complaints/commit", json=valid_commit_payload())
    assert response.status_code == 503
    text = response.text.lower()
    assert "postgres:postgres" not in text
    assert "postgresql+psycopg://" not in text
    assert "traceback" not in text
