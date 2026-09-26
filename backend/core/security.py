import hashlib
from typing import Tuple
from fastapi import HTTPException, UploadFile, status
import pymupdf as fitz
from backend.core.config import settings


class IngestionError(HTTPException):
    """Clean structured exception for document ingestion failures."""

    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


async def validate_and_read_pdf(file: UploadFile) -> Tuple[bytes, str, str]:
    """Validate uploaded file for PDF magic-bytes, size caps, and readability.

    Returns:
        Tuple of (file_bytes, sha256_hash, sanitized_filename)
    Raises:
        IngestionError: When file fails any validation check.
    """
    if not file.filename:
        raise IngestionError("Uploaded file has no filename.")

    # Check filename extension
    if not file.filename.lower().endswith(".pdf"):
        raise IngestionError(
            f"Invalid file type for '{file.filename}'. Only text-native PDF files (.pdf) are supported."
        )

    # Read bytes into memory
    content = await file.read()
    if not content or len(content) == 0:
        raise IngestionError("Uploaded PDF file is empty (0 bytes).")

    # Enforce file size limit
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise IngestionError(
            f"File size exceeds maximum allowed limit of {settings.MAX_FILE_SIZE_MB} MB."
        )

    # Validate PDF magic bytes (%PDF-)
    if not content.startswith(b"%PDF-"):
        raise IngestionError(
            "Invalid file format: File does not start with valid PDF header (%PDF-)."
        )

    # Compute cryptographic SHA-256 hash
    sha256 = hashlib.sha256(content).hexdigest()

    # Verify structural readability using PyMuPDF in-memory
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception:
        raise IngestionError("Malformed or corrupted PDF file could not be opened.")

    # Check password protection
    if doc.is_encrypted:
        doc.close()
        raise IngestionError("Password-protected or encrypted PDF files are not supported.")

    page_count = len(doc)
    doc.close()

    if page_count == 0:
        raise IngestionError("PDF contains zero pages.")

    if page_count > settings.MAX_PAGE_COUNT:
        raise IngestionError(
            f"Document page count ({page_count}) exceeds maximum allowed limit of {settings.MAX_PAGE_COUNT} pages."
        )

    sanitized_filename = file.filename.replace("\x00", "").strip()

    return content, sha256, sanitized_filename
