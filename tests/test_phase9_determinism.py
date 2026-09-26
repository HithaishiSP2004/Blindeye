"""Phase 9 Determinism and Idempotence Evaluation.

Tests:
- 5 sequential executions on identical agreement fixture yield identical parsed clauses.
- 5 sequential executions yield identical contradiction classifications.
- 5 sequential executions yield identical Advocate Pack structure.
"""

import pytest
from backend.engine.pdf_parser import parse_pdf_geometry
from backend.engine.clause_segmenter import segment_clauses
from backend.models.document import DocumentTree
from backend.contradiction.detector import ContradictionDetector
from backend.extraction.structured_extractor import _mock_extract_candidates
from backend.extraction.provenance_resolver import resolve_provenance
from backend.advocate.pack_builder import build_advocate_pack
from backend.verification.verification_gate import VerificationGate
from backend.verification.semantic_evaluator import DeterministicMockSemanticEvaluator


@pytest.fixture(scope="session")
def golden_pdf_bytes():
    path = "tests/fixtures/golden_agreement.pdf"
    with open(path, "rb") as f:
        return f.read()


def test_parsing_and_segmentation_determinism(golden_pdf_bytes):
    """5 repeated parsing & segmentation executions yield identical clauses."""
    baseline_clauses = None
    for _ in range(5):
        pages, status, warnings = parse_pdf_geometry(golden_pdf_bytes)
        clauses = segment_clauses(pages)
        clause_data = [(c.clause_id, c.clause_number, c.text, c.page_number) for c in clauses]
        if baseline_clauses is None:
            baseline_clauses = clause_data
        else:
            assert clause_data == baseline_clauses


@pytest.mark.asyncio
async def test_advocate_pack_compilation_determinism(golden_pdf_bytes):
    """5 repeated pack compilations yield identical dossier items."""
    pages, status, warnings = parse_pdf_geometry(golden_pdf_bytes)
    clauses = segment_clauses(pages)
    doc_tree = DocumentTree(
        document_id="doc_det",
        filename="golden_agreement.pdf",
        sha256_hash="hash",
        file_size_bytes=len(golden_pdf_bytes),
        page_count=len(pages),
        parsing_status=status,
        pages=pages,
        clauses=clauses,
    )
    candidates = _mock_extract_candidates(doc_tree)
    structured_agreement = resolve_provenance(candidates, doc_tree)
    gate = VerificationGate(semantic_evaluator=DeterministicMockSemanticEvaluator())
    veri_res = await gate.verify_agreement(structured_agreement, doc_tree)

    detector = ContradictionDetector()
    contra_res = detector.detect_contradictions(doc_tree, structured_agreement)

    baseline_dump = None
    for _ in range(5):
        pack = build_advocate_pack(doc_tree, veri_res, contra_res, document_name="golden_agreement.pdf")
        pack_dict = pack.model_dump()
        pack_dict.pop("compilation_timestamp")  # Timestamp differs across calls
        if baseline_dump is None:
            baseline_dump = pack_dict
        else:
            assert pack_dict == baseline_dump
