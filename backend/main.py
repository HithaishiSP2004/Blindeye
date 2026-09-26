import json
import uuid
from typing import Optional
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.core.security import validate_and_read_pdf
from backend.engine.clause_segmenter import segment_clauses
from backend.engine.pdf_parser import parse_pdf_geometry
from backend.extraction.provenance_resolver import resolve_provenance
from backend.extraction.structured_extractor import extract_candidate_facts
from backend.models.advocate_pack import AdvocatePack
from backend.models.contradiction import ContradictionResponse
from backend.models.document import DocumentTree
from backend.models.extraction import StructuredAgreementResult
from backend.models.qa import QAResponse
from backend.models.verification import DocumentVerificationResult
from backend.advocate.pack_builder import build_advocate_pack
from backend.contradiction.detector import ContradictionDetector
from backend.retrieval.qa_service import QAService
from backend.verification.verification_gate import VerificationGate

app = FastAPI(
    title="Evidence-First Residential Agreement Intelligence",
    description="Verification-first document intelligence engine for Indian residential agreements.",
    version="0.8.0",
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify backend operational readiness."""
    return {
        "status": "ok",
        "app": "Evidence-First Legal AI",
        "environment": settings.APP_ENV,
        "phase": "8 - Advocate Preparation Pack",


        "gemini_model": settings.GEMINI_MODEL,
        "limits": {
            "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
            "max_page_count": settings.MAX_PAGE_COUNT,
        },
    }


@app.get("/", tags=["Root"])
async def root():
    """Root metadata endpoint."""
    return {
        "message": "Evidence-First Residential Agreement Intelligence API",
        "version": "0.4.0",
        "status": "online",
        "docs_url": "/docs",
    }


@app.post("/documents/parse", response_model=DocumentTree, tags=["Documents"])
async def parse_document(file: UploadFile = File(...)):
    """Securely ingest and parse an uploaded PDF into a coordinate-preserving DocumentTree."""
    # 1. Ingestion security & integrity validation
    content, sha256_hash, filename = await validate_and_read_pdf(file)
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"

    # 2. Geometric parsing via PyMuPDF
    pages, parsing_status, warnings = parse_pdf_geometry(content)

    # 3. Deterministic clause boundary segmentation
    clauses = segment_clauses(pages)

    # 4. Assemble hierarchical DocumentTree
    doc_tree = DocumentTree(
        document_id=doc_id,
        filename=filename,
        sha256_hash=sha256_hash,
        file_size_bytes=len(content),
        page_count=len(pages),
        parsing_status=parsing_status,
        pages=pages,
        clauses=clauses,
        warnings=warnings,
    )

    return doc_tree


@app.post("/documents/extract", response_model=StructuredAgreementResult, tags=["Extraction"])
async def extract_document(file: UploadFile = File(...)):
    """Securely ingest PDF, parse DocumentTree, extract candidate facts via Gemini,
    and resolve deterministic physical provenance.
    """
    # 1. Ingestion security & integrity validation
    content, sha256_hash, filename = await validate_and_read_pdf(file)
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"

    # 2. Geometric parsing via PyMuPDF
    pages, parsing_status, warnings = parse_pdf_geometry(content)

    # 3. Deterministic clause boundary segmentation
    clauses = segment_clauses(pages)

    # 4. Assemble hierarchical DocumentTree
    doc_tree = DocumentTree(
        document_id=doc_id,
        filename=filename,
        sha256_hash=sha256_hash,
        file_size_bytes=len(content),
        page_count=len(pages),
        parsing_status=parsing_status,
        pages=pages,
        clauses=clauses,
        warnings=warnings,
    )

    # 5. Extract candidate facts via Gemini official SDK (or deterministic fallback)
    candidates = await extract_candidate_facts(doc_tree)

    # 6. Resolve deterministic provenance against DocumentTree
    structured_agreement = resolve_provenance(candidates, doc_tree)

    return StructuredAgreementResult(
        document_tree=doc_tree,
        structured_agreement=structured_agreement,
    )


@app.post("/documents/verify", response_model=DocumentVerificationResult, tags=["Verification"])
async def verify_document(file: UploadFile = File(...)):
    """Securely ingest PDF, parse DocumentTree, extract candidate facts,
    resolve provenance, and execute the Verification Gate.
    """
    # 1. Ingestion security & integrity validation
    content, sha256_hash, filename = await validate_and_read_pdf(file)
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"

    # 2. Geometric parsing via PyMuPDF
    pages, parsing_status, warnings = parse_pdf_geometry(content)

    # 3. Deterministic clause boundary segmentation
    clauses = segment_clauses(pages)

    # 4. Assemble hierarchical DocumentTree
    doc_tree = DocumentTree(
        document_id=doc_id,
        filename=filename,
        sha256_hash=sha256_hash,
        file_size_bytes=len(content),
        page_count=len(pages),
        parsing_status=parsing_status,
        pages=pages,
        clauses=clauses,
        warnings=warnings,
    )

    # 5. Extract candidate facts via Gemini official SDK (or deterministic fallback)
    candidates = await extract_candidate_facts(doc_tree)

    # 6. Resolve deterministic provenance against DocumentTree
    structured_agreement = resolve_provenance(candidates, doc_tree)

    # 7. Verification Gate (Correction 1, 2, 7, 13)
    gate = VerificationGate()
    verification_result = await gate.verify_agreement(structured_agreement, doc_tree)

    return verification_result


@app.post("/documents/ask", response_model=QAResponse, tags=["Q&A"])
async def ask_document(
    file: UploadFile = File(...),
    question: str = Form(...),
    conversation_history: Optional[str] = Form(None),
):
    """Evidence-First Q&A endpoint for Indian residential agreements.

    Adheres strictly to Phase 5 Corrections:
    - Stateless API accepting multipart/form-data (Correction 11).
    - Preserves Question -> Retrieval -> Verification -> Answer -> Source chain.
    - Deterministic fast path for canonical queries without requiring Gemini.
    - Conversation history is context-only, never evidence (Correction 12).
    """
    # 1. Ingestion security & integrity validation
    content, sha256_hash, filename = await validate_and_read_pdf(file)
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"

    # 2. Geometric parsing via PyMuPDF
    pages, parsing_status, warnings = parse_pdf_geometry(content)

    # 3. Deterministic clause boundary segmentation
    clauses = segment_clauses(pages)

    # 4. Assemble hierarchical DocumentTree
    doc_tree = DocumentTree(
        document_id=doc_id,
        filename=filename,
        sha256_hash=sha256_hash,
        file_size_bytes=len(content),
        page_count=len(pages),
        parsing_status=parsing_status,
        pages=pages,
        clauses=clauses,
        warnings=warnings,
    )

    # 5. Fast canonical extraction for field lookup
    candidates = await extract_candidate_facts(doc_tree)
    structured_agreement = resolve_provenance(candidates, doc_tree)

    # 6. Parse optional conversation history
    parsed_history = []
    if conversation_history:
        try:
            parsed_history = json.loads(conversation_history)
        except Exception:
            parsed_history = []

    # 7. Route, retrieve, verify, and generate answer
    qa_service = QAService()
    response = await qa_service.answer_question(
        document_tree=doc_tree,
        question=question,
        conversation_history=parsed_history,
        structured_agreement=structured_agreement,
    )

    return response


@app.post("/documents/contradictions", response_model=ContradictionResponse, tags=["Contradictions"])
async def detect_document_contradictions(
    file: UploadFile = File(...),
):
    """Stateless contradiction intelligence endpoint for Indian residential agreements.

    Enforces Phase 6 Architecture:
    - Stateless API accepting multipart/form-data.
    - Slices candidate statements directly from DocumentTree (Correction 1).
    - Detects contractual conflicts across notice period, rent, deposit, tenure, repairs.
    - Resolves dual physical provenance (source_a and source_b).
    - Identifies conflicts without legal adjudication or validity ratings.
    """
    # 1. Ingestion security & integrity validation
    content, sha256_hash, filename = await validate_and_read_pdf(file)
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"

    # 2. Geometric parsing via PyMuPDF
    pages, parsing_status, warnings = parse_pdf_geometry(content)

    # 3. Deterministic clause boundary segmentation
    clauses = segment_clauses(pages)

    # 4. Assemble hierarchical DocumentTree
    doc_tree = DocumentTree(
        document_id=doc_id,
        filename=filename,
        sha256_hash=sha256_hash,
        file_size_bytes=len(content),
        page_count=len(pages),
        parsing_status=parsing_status,
        pages=pages,
        clauses=clauses,
        warnings=warnings,
    )

    # 5. Extract candidate facts & provenance for acceleration
    candidates = await extract_candidate_facts(doc_tree)
    structured_agreement = resolve_provenance(candidates, doc_tree)

    # 6. Run contradiction detection
    detector = ContradictionDetector()
    return detector.detect_contradictions(doc_tree, structured_agreement)


@app.post("/documents/advocate-pack", response_model=AdvocatePack, tags=["Advocate Pack"])
async def generate_advocate_pack_endpoint(
    file: UploadFile = File(...),
):
    """Generate an Evidentiary Agreement Review Dossier (Advocate Preparation Pack).

    Strictly non-evaluative:
    - Reuses exact existing pipeline components (PDF parsing, clause segmentation, verification, contradiction detection).
    - Assembles deterministic evidentiary dossier with dual physical provenance.
    - Zero generative hallucination; zero legal advice or validity adjudication.
    """
    # 1. Ingestion security & integrity validation
    content, sha256_hash, filename = await validate_and_read_pdf(file)
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"

    # 2. Geometric parsing via PyMuPDF
    pages, parsing_status, warnings = parse_pdf_geometry(content)

    # 3. Deterministic clause boundary segmentation
    clauses = segment_clauses(pages)

    # 4. Assemble hierarchical DocumentTree
    doc_tree = DocumentTree(
        document_id=doc_id,
        filename=filename,
        sha256_hash=sha256_hash,
        file_size_bytes=len(content),
        page_count=len(pages),
        parsing_status=parsing_status,
        pages=pages,
        clauses=clauses,
        warnings=warnings,
    )

    # 5. Extract candidate facts & provenance
    candidates = await extract_candidate_facts(doc_tree)
    structured_agreement = resolve_provenance(candidates, doc_tree)

    # 6. Run verification gate
    gate = VerificationGate()
    verification_res = await gate.verify_agreement(structured_agreement, doc_tree)

    # 7. Run contradiction detector
    detector = ContradictionDetector()
    contradiction_res = detector.detect_contradictions(doc_tree, structured_agreement)

    # 8. Deterministically compile AdvocatePack
    return build_advocate_pack(
        document_tree=doc_tree,
        verification_result=verification_res,
        contradiction_response=contradiction_res,
        document_name=filename,
    )


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=(settings.APP_ENV == "development"),
    )
