"""Deterministic document text extraction for complaint intake.

Documents are processed in memory only. Nothing is written to disk or
PostgreSQL. Scanned-image OCR is intentionally not implemented.
"""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from email import policy
from email.message import Message
from email.parser import BytesParser
from html.parser import HTMLParser
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal

import pymupdf

from app.services.document_limits import (
    EMPTY_TEXT_MESSAGE,
    ENCRYPTED_PDF_MESSAGE,
    FILE_TOO_LARGE_MESSAGE,
    MAX_EXTRACTED_CHARACTERS,
    MAX_PDF_PAGES,
    MAX_UPLOAD_BYTES,
    SCANNED_PDF_MESSAGE,
    SUPPORTED_EXTENSIONS,
    TEXT_TOO_LONG_MESSAGE,
    TOO_MANY_PAGES_MESSAGE,
    UNREADABLE_DOCUMENT_MESSAGE,
    UNSUPPORTED_TYPE_MESSAGE,
)

logger = logging.getLogger(__name__)

DocumentType = Literal["pdf", "txt", "eml"]


class DocumentValidationError(Exception):
    """Safe, user-facing document validation failure."""

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class DocumentExtractionResult:
    filename: str
    document_type: DocumentType
    text: str
    page_count: int | None
    byte_size: int


def safe_presentation_filename(filename: str | None) -> str:
    """Return an untrusted filename for display only — never a filesystem path."""
    if not filename or not filename.strip():
        return "upload"
    name = PureWindowsPath(filename.strip()).name
    name = PurePosixPath(name).name
    return name or "upload"


def _extension_of(filename: str) -> str:
    return PurePosixPath(filename).suffix.lower()


def _detect_document_type(filename: str, content_type: str | None) -> DocumentType:
    extension = _extension_of(filename)
    if extension not in SUPPORTED_EXTENSIONS:
        raise DocumentValidationError(UNSUPPORTED_TYPE_MESSAGE, status_code=415)

    normalized_type = (content_type or "").split(";")[0].strip().lower()
    if extension == ".pdf":
        if normalized_type and normalized_type not in {
            "application/pdf",
            "application/octet-stream",
            "",
        }:
            # Browsers may send incomplete MIME; extension remains authoritative
            # when the suffix is .pdf and bytes will be verified as PDF.
            pass
        return "pdf"
    if extension == ".txt":
        return "txt"
    return "eml"


def normalize_extracted_text(text: str) -> str:
    """Conservative normalization — evidence must remain intact."""
    cleaned = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    if cleaned.startswith("\ufeff"):
        cleaned = cleaned.lstrip("\ufeff")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _assert_meaningful_text(text: str, *, scanned_pdf: bool = False) -> str:
    normalized = normalize_extracted_text(text)
    if not normalized or not any(ch.isalnum() for ch in normalized):
        message = SCANNED_PDF_MESSAGE if scanned_pdf else EMPTY_TEXT_MESSAGE
        raise DocumentValidationError(message, status_code=422)
    if len(normalized) > MAX_EXTRACTED_CHARACTERS:
        raise DocumentValidationError(TEXT_TOO_LONG_MESSAGE, status_code=422)
    return normalized


def extract_pdf_text(file_bytes: bytes) -> tuple[str, int]:
    try:
        document = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:  # noqa: BLE001 — convert parser failures to 422
        raise DocumentValidationError(UNREADABLE_DOCUMENT_MESSAGE, status_code=422) from exc

    try:
        if document.is_encrypted or document.needs_pass:
            raise DocumentValidationError(ENCRYPTED_PDF_MESSAGE, status_code=422)

        page_count = document.page_count
        if page_count > MAX_PDF_PAGES:
            raise DocumentValidationError(TOO_MANY_PAGES_MESSAGE, status_code=422)

        parts: list[str] = []
        for page in document:
            parts.append(page.get_text("text"))
        combined = "\n".join(parts)
        text = _assert_meaningful_text(combined, scanned_pdf=True)
        return text, page_count
    finally:
        document.close()


def extract_txt_text(file_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            decoded = file_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise DocumentValidationError(UNREADABLE_DOCUMENT_MESSAGE, status_code=422)

    return _assert_meaningful_text(decoded)


class _HTMLToText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if tag in {"br", "p", "div", "tr", "li", "h1", "h2", "h3", "h4"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag in {"p", "div", "tr", "li", "h1", "h2", "h3", "h4"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        self._chunks.append(data)

    def text(self) -> str:
        return "".join(self._chunks)


def _html_to_text(raw_html: str) -> str:
    parser = _HTMLToText()
    parser.feed(raw_html)
    parser.close()
    return html.unescape(parser.text())


def _message_body_text(message: Message) -> str:
    if message.is_multipart():
        plain_parts: list[str] = []
        html_parts: list[str] = []
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            disposition = (part.get_content_disposition() or "").lower()
            if disposition == "attachment":
                continue
            content_type = part.get_content_type()
            try:
                payload = part.get_content()
            except Exception:  # noqa: BLE001
                continue
            if not isinstance(payload, str):
                continue
            if content_type == "text/plain":
                plain_parts.append(payload)
            elif content_type == "text/html":
                html_parts.append(_html_to_text(payload))
        if plain_parts:
            return "\n\n".join(plain_parts)
        if html_parts:
            return "\n\n".join(html_parts)
        return ""

    content_type = message.get_content_type()
    try:
        payload = message.get_content()
    except Exception:  # noqa: BLE001
        return ""
    if not isinstance(payload, str):
        return ""
    if content_type == "text/html":
        return _html_to_text(payload)
    return payload


def extract_eml_text(file_bytes: bytes) -> str:
    try:
        message = BytesParser(policy=policy.default).parsebytes(file_bytes)
    except Exception as exc:  # noqa: BLE001
        raise DocumentValidationError(UNREADABLE_DOCUMENT_MESSAGE, status_code=422) from exc

    headers: list[str] = []
    for label, key in (
        ("Subject", "subject"),
        ("From", "from"),
        ("To", "to"),
        ("Date", "date"),
    ):
        value = message.get(key)
        if value:
            headers.append(f"{label}: {value}")

    body = _message_body_text(message)
    combined = "\n".join(headers)
    if body.strip():
        combined = f"{combined}\n\n{body}" if combined else body

    return _assert_meaningful_text(combined)


def extract_document(
    *,
    filename: str | None,
    content_type: str | None,
    file_bytes: bytes,
) -> DocumentExtractionResult:
    presentation_name = safe_presentation_filename(filename)
    byte_size = len(file_bytes)

    if byte_size == 0:
        raise DocumentValidationError(UNREADABLE_DOCUMENT_MESSAGE, status_code=422)
    if byte_size > MAX_UPLOAD_BYTES:
        raise DocumentValidationError(FILE_TOO_LARGE_MESSAGE, status_code=413)

    document_type = _detect_document_type(presentation_name, content_type)
    page_count: int | None = None

    if document_type == "pdf":
        text, page_count = extract_pdf_text(file_bytes)
    elif document_type == "txt":
        text = extract_txt_text(file_bytes)
    else:
        text = extract_eml_text(file_bytes)

    logger.info(
        "document.extract success type=%s bytes=%s pages=%s chars=%s",
        document_type,
        byte_size,
        page_count,
        len(text),
    )
    return DocumentExtractionResult(
        filename=presentation_name,
        document_type=document_type,
        text=text,
        page_count=page_count,
        byte_size=byte_size,
    )
