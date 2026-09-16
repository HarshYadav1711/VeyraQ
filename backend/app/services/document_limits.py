"""Centralized document intake limits for the assessment build."""

from app.core.config import settings

MAX_PDF_PAGES = 20
MAX_EXTRACTED_CHARACTERS = 20_000

SUPPORTED_EXTENSIONS = frozenset({".pdf", ".txt", ".eml"})
SUPPORTED_CONTENT_TYPES = frozenset(
    {
        "application/pdf",
        "text/plain",
        "message/rfc822",
    }
)

SCANNED_PDF_MESSAGE = (
    "This PDF does not contain readable embedded text. Scanned-image "
    "OCR is not enabled in this assessment build."
)

UNSUPPORTED_TYPE_MESSAGE = (
    "Unsupported document type. Upload a PDF, TXT, or EML complaint file."
)

TOO_MANY_PAGES_MESSAGE = (
    f"PDF exceeds the maximum of {MAX_PDF_PAGES} pages supported in this assessment build."
)

TEXT_TOO_LONG_MESSAGE = (
    f"Extracted document text exceeds the maximum of "
    f"{MAX_EXTRACTED_CHARACTERS:,} characters. Shorten the document or "
    "split the complaint before retrying."
)

UNREADABLE_DOCUMENT_MESSAGE = (
    "The document could not be read. Upload a valid PDF, TXT, or EML file."
)

ENCRYPTED_PDF_MESSAGE = (
    "This PDF is password-protected or encrypted and cannot be processed."
)

EMPTY_TEXT_MESSAGE = "No readable text could be extracted from the document."

POPULATED_DRAFT_MESSAGE = (
    "Start a New Complaint before analyzing another complaint document."
)


def max_upload_bytes() -> int:
    """Configured maximum upload size (default 4 MiB for Vercel-compatible deploys)."""
    return settings.MAX_UPLOAD_BYTES


def file_too_large_message() -> str:
    megabytes = max(1, max_upload_bytes() // (1024 * 1024))
    return f"Document exceeds the maximum upload size of {megabytes} MB."


# Back-compat aliases used by services/tests (resolved at import from settings).
MAX_UPLOAD_BYTES = max_upload_bytes()
FILE_TOO_LARGE_MESSAGE = file_too_large_message()
