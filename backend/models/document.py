from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ParsingStatus(str, Enum):
    """Machine-readable document text extraction and readability status."""

    TEXT_AVAILABLE = "TEXT_AVAILABLE"
    TEXT_SPARSE = "TEXT_SPARSE"
    OCR_REQUIRED = "OCR_REQUIRED"
    PARSING_FAILED = "PARSING_FAILED"


class BoundingBox(BaseModel):
    """Geometric coordinate boundary on a specific document page in PDF points."""

    page: int = Field(..., ge=1, description="1-indexed document page number")
    x0: float = Field(..., description="Left coordinate in PDF points")
    y0: float = Field(..., description="Top coordinate in PDF points")
    x1: float = Field(..., description="Right coordinate in PDF points")
    y1: float = Field(..., description="Bottom coordinate in PDF points")


class TextSpan(BaseModel):
    """A granular typographical span inside a text block."""

    span_id: str = Field(..., description="Unique span ID e.g., 'p1_b2_s0'")
    block_id: Optional[str] = Field(default=None, description="Parent TextBlock ID")
    span_index: Optional[int] = Field(default=None, description="Index of span within block")
    text: str = Field(..., description="Verbatim text of the span")
    bbox: BoundingBox = Field(..., description="Spatial bounding box")
    font_name: Optional[str] = Field(default=None, description="Font identifier if available")
    font_size: Optional[float] = Field(default=None, description="Font size in points")
    flags: Optional[int] = Field(default=None, description="Font flags (bold, italic, etc.)")
    char_start: int = Field(default=0, ge=0, description="Start character offset in parent block")
    char_end: int = Field(default=0, ge=0, description="End character offset in parent block")
    clause_char_start: Optional[int] = Field(default=None, ge=0, description="Start character offset in parent clause")
    clause_char_end: Optional[int] = Field(default=None, ge=0, description="End character offset in parent clause")


class TextBlock(BaseModel):
    """A block of text extracted from a page layout."""

    block_id: str = Field(..., description="Unique block ID e.g., 'p1_b2'")
    block_number: int = Field(..., ge=0, description="Sequential block index on page")
    page: int = Field(..., ge=1, description="Page number where the block resides")
    bbox: BoundingBox = Field(..., description="Overall bounding box of the block")
    text: str = Field(..., description="Combined text content of the block")
    spans: List[TextSpan] = Field(default_factory=list, description="Contained typographical spans")
    char_start: int = Field(default=0, ge=0, description="Start character offset in page text")
    char_end: int = Field(default=0, ge=0, description="End character offset in page text")
    is_header_footer: bool = Field(default=False, description="Detected as repeated running header/footer")
    is_table_hint: bool = Field(default=False, description="Detected structural table-like layout hint")


class PageData(BaseModel):
    """Per-page layout geometry and text content."""

    page_number: int = Field(..., ge=1, description="1-indexed page number")
    width: float = Field(..., description="Page width in points")
    height: float = Field(..., description="Page height in points")
    blocks: List[TextBlock] = Field(default_factory=list, description="Extracted layout text blocks")
    char_count: int = Field(default=0, description="Total characters extracted from this page")
    status: ParsingStatus = Field(default=ParsingStatus.TEXT_AVAILABLE, description="Per-page text status")


class Clause(BaseModel):
    """A bounded contractual clause carrying physical coordinates and provenance."""

    clause_id: str = Field(..., description="Deterministic unique ID e.g., 'clause_p2_c4'")
    clause_number: str = Field(..., description="Human-readable clause identifier e.g., '4', '4.1', '(a)'")
    title: Optional[str] = Field(default=None, description="Optional detected clause heading")
    text: str = Field(..., description="Verbatim text content of the clause")
    page_number: int = Field(..., ge=1, description="Primary / starting page number of the clause")
    pages: List[int] = Field(default_factory=list, description="All pages this clause spans")
    bounding_boxes: List[BoundingBox] = Field(
        default_factory=list,
        description="Physical bounding boxes covering this clause across lines/pages",
    )
    spans: List[TextSpan] = Field(
        default_factory=list,
        description="Granular constituent spans carrying line-level bounding boxes and character offsets",
    )
    source_block_ids: List[str] = Field(
        default_factory=list,
        description="Traceability pointers back to raw layout TextBlock IDs",
    )
    parent_clause_id: Optional[str] = Field(
        default=None,
        description="Parent clause ID if hierarchical e.g., 'clause_p1_c1' for '1.1'",
    )
    hierarchy_level: int = Field(default=1, description="Nesting level: 1=top clause, 2=subclause, etc.")
    is_heading: bool = Field(default=False, description="Whether this block represents an agreement section header")
    is_header_footer: bool = Field(default=False, description="Whether classified as repeated running header/footer")
    is_uncertain: bool = Field(
        default=False,
        description="True if clause segmentation boundary was ambiguous or fallback-merged",
    )


class DocumentTree(BaseModel):
    """Hierarchical, coordinate-rich representation of an ingested document."""

    document_id: str = Field(..., description="Unique document session UUID")
    filename: str = Field(..., description="Original uploaded filename")
    sha256_hash: str = Field(..., description="Cryptographic SHA-256 hash of file content")
    file_size_bytes: int = Field(default=0, description="Size of original uploaded file in bytes")
    page_count: int = Field(..., ge=1, description="Total number of pages")
    parsing_status: ParsingStatus = Field(
        default=ParsingStatus.TEXT_AVAILABLE,
        description="Overall document text extraction status",
    )
    pages: List[PageData] = Field(default_factory=list, description="Per-page layout structures")
    clauses: List[Clause] = Field(default_factory=list, description="Ordered list of segmented clauses")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings recorded during parsing")
