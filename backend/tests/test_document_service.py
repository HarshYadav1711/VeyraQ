"""Document service extraction and validation tests."""

from __future__ import annotations

from email.message import EmailMessage

import pymupdf
import pytest

from app.services.document_limits import (
    MAX_EXTRACTED_CHARACTERS,
    MAX_PDF_PAGES,
    MAX_UPLOAD_BYTES,
    SCANNED_PDF_MESSAGE,
)
from app.services.document_service import (
    DocumentValidationError,
    extract_document,
    extract_eml_text,
    extract_pdf_text,
    extract_txt_text,
)


def _pdf_with_text(text: str, *, pages: int = 1) -> bytes:
    document = pymupdf.open()
    try:
        for index in range(pages):
            page = document.new_page()
            if index == 0:
                page.insert_text((72, 72), text)
            else:
                page.insert_text((72, 72), f"Page {index + 1}")
        return document.tobytes()
    finally:
        document.close()


def _blank_pdf(*, pages: int = 1) -> bytes:
    document = pymupdf.open()
    try:
        for _ in range(pages):
            document.new_page()
        return document.tobytes()
    finally:
        document.close()


def test_pdf_with_embedded_text_extracts_successfully() -> None:
    payload = _pdf_with_text(
        "Cefixime Capsules 200 mg\nCFX260481\nMarch 2026"
    )
    result = extract_document(
        filename="complaint.pdf",
        content_type="application/pdf",
        file_bytes=payload,
    )
    assert result.document_type == "pdf"
    assert result.page_count == 1
    assert "Cefixime Capsules 200 mg" in result.text
    assert "CFX260481" in result.text
    assert "March 2026" in result.text


def test_blank_pdf_returns_scanned_message() -> None:
    with pytest.raises(DocumentValidationError) as exc_info:
        extract_pdf_text(_blank_pdf())
    assert exc_info.value.status_code == 422
    assert exc_info.value.message == SCANNED_PDF_MESSAGE


def test_pdf_beyond_page_limit_is_rejected() -> None:
    payload = _pdf_with_text("Complaint text", pages=MAX_PDF_PAGES + 1)
    with pytest.raises(DocumentValidationError) as exc_info:
        extract_document(
            filename="long.pdf",
            content_type="application/pdf",
            file_bytes=payload,
        )
    assert exc_info.value.status_code == 422
    assert "pages" in exc_info.value.message.lower()


def test_oversized_upload_is_rejected() -> None:
    payload = b"x" * (MAX_UPLOAD_BYTES + 1)
    with pytest.raises(DocumentValidationError) as exc_info:
        extract_document(
            filename="huge.txt",
            content_type="text/plain",
            file_bytes=payload,
        )
    assert exc_info.value.status_code == 413


def test_unsupported_extension_is_rejected() -> None:
    with pytest.raises(DocumentValidationError) as exc_info:
        extract_document(
            filename="notes.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_bytes=b"not a real document",
        )
    assert exc_info.value.status_code == 415


def test_invalid_pdf_bytes_are_rejected() -> None:
    with pytest.raises(DocumentValidationError) as exc_info:
        extract_document(
            filename="fake.pdf",
            content_type="application/pdf",
            file_bytes=b"this is not a pdf",
        )
    assert exc_info.value.status_code == 422


def test_txt_extracts_correctly() -> None:
    text = extract_txt_text(b"Customer: Northstar\nBatch: CFX260481\n")
    assert "Northstar" in text
    assert "CFX260481" in text


def test_utf8_sig_txt_extracts_correctly() -> None:
    payload = "Cefixime Capsules 200 mg".encode("utf-8-sig")
    text = extract_txt_text(payload)
    assert text.startswith("Cefixime Capsules 200 mg")
    assert "\ufeff" not in text


def test_eml_text_plain_body_extracts() -> None:
    message = EmailMessage()
    message["Subject"] = "Capsule discoloration"
    message["From"] = "qa@northstar.example"
    message["To"] = "complaints@veyraq.example"
    message["Date"] = "Tue, 15 Sep 2026 10:00:00 +0000"
    message.set_content(
        "Product: Cefixime Capsules 200 mg\nBatch: CFX260481\n"
        "Brown discoloration observed during inspection."
    )
    text = extract_eml_text(message.as_bytes())
    assert "Subject: Capsule discoloration" in text
    assert "From: qa@northstar.example" in text
    assert "CFX260481" in text
    assert "Brown discoloration" in text


def test_eml_attachment_content_is_not_appended() -> None:
    message = EmailMessage()
    message["Subject"] = "Complaint"
    message["From"] = "sender@example.com"
    message["To"] = "qa@example.com"
    message.set_content("Visible complaint body with batch CFX260481.")
    message.add_attachment(
        b"SECRET_ATTACHMENT_SHOULD_NOT_APPEAR",
        maintype="application",
        subtype="octet-stream",
        filename="secret.bin",
    )
    text = extract_eml_text(message.as_bytes())
    assert "Visible complaint body" in text
    assert "SECRET_ATTACHMENT_SHOULD_NOT_APPEAR" not in text


def test_extracted_text_over_character_limit_is_rejected() -> None:
    oversized = ("Complaint line\n" * (MAX_EXTRACTED_CHARACTERS // 10 + 50)).encode("utf-8")
    with pytest.raises(DocumentValidationError) as exc_info:
        extract_document(
            filename="long.txt",
            content_type="text/plain",
            file_bytes=oversized,
        )
    assert exc_info.value.status_code == 422
    assert "characters" in exc_info.value.message.lower()
