import re
from typing import List, Tuple
import pymupdf as fitz
from backend.models.document import BoundingBox, PageData, ParsingStatus, TextBlock, TextSpan


def _is_header_footer_candidate(bbox: Tuple[float, float, float, float], page_height: float, text: str) -> bool:
    """Heuristic check for running header/footer based on page margin geometry."""
    y0, y1 = bbox[1], bbox[3]
    clean_text = text.strip()

    # Page number patterns: e.g., "Page 1 of 5", "- 2 -", "1 / 3"
    page_num_pattern = r"^[-–—\s]*(page\s+)?\d+(\s*(of|/)\s*\d+)?[-–—\s]*$"
    if re.match(page_num_pattern, clean_text, re.IGNORECASE):
        if y0 < page_height * 0.12 or y1 > page_height * 0.88:
            return True

    # Top running header (top 7% of page) or bottom running footer (bottom 7% of page)
    if y1 <= page_height * 0.07 or y0 >= page_height * 0.93:
        if len(clean_text) < 120:  # Running headers are generally concise
            return True

    return False


def _is_table_hint(text: str, lines_count: int) -> bool:
    """Detect if block exhibits tabular characteristics (tabs, aligned numeric columns)."""
    if "\t" in text:
        return True
    
    # Check for multiple numbers or currency figures in tight columns
    currency_or_num_count = len(re.findall(r"(?:₹|Rs\.?|INR|\b\d{2,}\b)", text))
    if lines_count >= 2 and currency_or_num_count >= 3:
        return True

    return False


def parse_pdf_geometry(pdf_bytes: bytes) -> Tuple[List[PageData], ParsingStatus, List[str]]:
    """Deterministically parse a PDF byte stream into structured PageData objects.

    Returns:
        Tuple of (pages_data, overall_status, warnings)
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: List[PageData] = []
    warnings: List[str] = []
    total_chars = 0

    try:
        for page_idx in range(len(doc)):
            page_num = page_idx + 1
            page = doc[page_idx]
            page_rect = page.rect
            width = float(page_rect.width)
            height = float(page_rect.height)

            # Extract layout dictionary with block, line, and span hierarchy
            page_dict = page.get_text("dict")
            extracted_blocks: List[TextBlock] = []
            page_char_count = 0

            raw_blocks = page_dict.get("blocks", [])
            text_block_idx = 0

            for raw_b in raw_blocks:
                # Type 0 is text block, Type 1 is image block
                if raw_b.get("type", 0) != 0:
                    continue

                b_bbox = raw_b.get("bbox", (0.0, 0.0, 0.0, 0.0))
                block_bbox = BoundingBox(
                    page=page_num,
                    x0=round(float(b_bbox[0]), 2),
                    y0=round(float(b_bbox[1]), 2),
                    x1=round(float(b_bbox[2]), 2),
                    y1=round(float(b_bbox[3]), 2),
                )

                block_id = f"p{page_num}_b{text_block_idx}"
                block_spans: List[TextSpan] = []
                lines = raw_b.get("lines", [])
                span_counter = 0

                raw_block_text = ""
                for line_idx, line in enumerate(lines):
                    line_spans = line.get("spans", [])
                    if not line_spans:
                        continue
                    if raw_block_text and not raw_block_text.endswith(" "):
                        raw_block_text += " "

                    for s_idx, span in enumerate(line_spans):
                        span_text = span.get("text", "")
                        if not span_text:
                            continue

                        char_start = len(raw_block_text)
                        raw_block_text += span_text
                        char_end = len(raw_block_text)

                        s_bbox = span.get("bbox", (0.0, 0.0, 0.0, 0.0))
                        span_obj = TextSpan(
                            span_id=f"p{page_num}_b{text_block_idx}_s{span_counter}",
                            block_id=block_id,
                            span_index=span_counter,
                            text=span_text,
                            bbox=BoundingBox(
                                page=page_num,
                                x0=round(float(s_bbox[0]), 2),
                                y0=round(float(s_bbox[1]), 2),
                                x1=round(float(s_bbox[2]), 2),
                                y1=round(float(s_bbox[3]), 2),
                            ),
                            font_name=span.get("font"),
                            font_size=round(float(span.get("size", 10.0)), 1),
                            flags=span.get("flags"),
                            char_start=char_start,
                            char_end=char_end,
                        )
                        block_spans.append(span_obj)
                        span_counter += 1

                combined_text = raw_block_text.strip()
                if not combined_text:
                    continue

                lstrip_diff = len(raw_block_text) - len(raw_block_text.lstrip())
                if lstrip_diff > 0:
                    for s in block_spans:
                        s.char_start = max(0, s.char_start - lstrip_diff)
                        s.char_end = max(0, s.char_end - lstrip_diff)

                block_char_start = page_char_count
                block_char_end = page_char_count + len(combined_text)
                page_char_count += len(combined_text)

                is_hdr_ftr = _is_header_footer_candidate(
                    (block_bbox.x0, block_bbox.y0, block_bbox.x1, block_bbox.y1),
                    height,
                    combined_text,
                )
                is_table = _is_table_hint(combined_text, len(lines))

                text_block = TextBlock(
                    block_id=block_id,
                    block_number=text_block_idx,
                    page=page_num,
                    bbox=block_bbox,
                    text=combined_text,
                    spans=block_spans,
                    char_start=block_char_start,
                    char_end=block_char_end,
                    is_header_footer=is_hdr_ftr,
                    is_table_hint=is_table,
                )
                extracted_blocks.append(text_block)
                text_block_idx += 1

            total_chars += page_char_count

            # Assess per-page status
            if page_char_count == 0:
                page_status = ParsingStatus.OCR_REQUIRED
                warnings.append(f"Page {page_num} contains no extractable text layer (may be scanned).")
            elif page_char_count < 40:
                page_status = ParsingStatus.TEXT_SPARSE
                warnings.append(f"Page {page_num} has sparse text ({page_char_count} characters).")
            else:
                page_status = ParsingStatus.TEXT_AVAILABLE

            page_data = PageData(
                page_number=page_num,
                width=round(width, 2),
                height=round(height, 2),
                blocks=extracted_blocks,
                char_count=page_char_count,
                status=page_status,
            )
            pages.append(page_data)

    finally:
        doc.close()

    # Determine overall document status
    if total_chars == 0:
        overall_status = ParsingStatus.OCR_REQUIRED
        warnings.append("Document appears to be fully scanned or image-based. OCR would be required.")
    elif total_chars < (len(pages) * 40):
        overall_status = ParsingStatus.TEXT_SPARSE
        warnings.append("Document has sparse overall text density.")
    else:
        overall_status = ParsingStatus.TEXT_AVAILABLE

    return pages, overall_status, warnings
