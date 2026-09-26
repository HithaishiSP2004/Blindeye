# Blindeye: Evidence-First Residential Agreement Intelligence

> **Verifier, not generator.** An India-focused residential rental agreement inspection and verification engine.  
> Every document-grounded claim is traceable to exact source text with physical coordinate provenance. When evidence is absent, ambiguous, or out-of-scope, the system deterministically refuses to fabricate an answer.

---

## Core Philosophy

- **Zero Unverified Assertions:** Answers and extractions are strictly grounded in physical document bounding boxes or deterministically refused.
- **Verification Gate:** Candidate claims pass through formal deterministic and NLI semantic verification prior to presentation.
- **Explicit Claim Classification:** Verification yields transparent states (`VERIFIED`, `UNSUPPORTED`, `CONTRADICTORY`, `NOT_FOUND`, `AMBIGUOUS`).
- **Prompt Injection Defense:** Neutralizes system override instructions without destructive prompt corruption.
- **Clear Legal Guardrails:** Rejects legal advice queries and general trivia out of boundary scope.

---

## Architecture Overview

```
                                ┌─────────────────────────────────────────┐
                                │          Uploaded Agreement PDF         │
                                └────────────────────┬────────────────────┘
                                                     │
                                       ┌─────────────▼─────────────┐
                                       │   Document Engine (PyMuPDF)│
                                       │  - PDF to DocumentTree     │
                                       │  - Spatial Bounding Boxes  │
                                       └─────────────┬─────────────┘
                                                     │
                   ┌─────────────────────────────────┴─────────────────────────────────┐
                   │                                                                   │
        ┌──────────▼──────────┐                                             ┌──────────▼──────────┐
        │ Extraction Pipeline │                                             │    Q&A Subsystem    │
        │ - Candidate Schema  │                                             │ - Query Router      │
        │ - Claim Decomposer  │                                             │ - Retrieval Ladder  │
        │ - Provenance Engine │                                             │ - Evidence Selector │
        └──────────┬──────────┘                                             └──────────┬──────────┘
                   │                                                                   │
                   └─────────────────────────────────┬─────────────────────────────────┘
                                                     │
                                       ┌─────────────▼─────────────┐
                                       │    Verification Gate      │
                                       │  - Deterministic Checks   │
                                       │  - NLI Semantic Evaluator │
                                       └─────────────┬─────────────┘
                                                     │
                                       ┌─────────────▼─────────────┐
                                       │   Editorial Split-Screen  │
                                       │  - Document Canvas & BBox │
                                       │  - Grounded Claim Panels  │
                                       │  - Research Q&A Desk      │
                                       └───────────────────────────┘
```

### Key Modules

1. **Document Engine (`backend/document/`):**
   - High-fidelity PDF parsing with text spans, font metadata, page dimensions, and coordinate bounding boxes `[x0, y0, x1, y1]`.
   - Structural clause segmentation identifying numbered headings, recitals, and covenants.

2. **Extraction & Provenance Resolver (`backend/extraction/`):**
   - Extracts canonical residential agreement fields (rent, security deposit, lock-in period, notice period, maintenance, escalation, permitted use).
   - Resolves exact page numbers and bounding box coordinates for each extracted claim.

3. **Verification Core (`backend/verification/`):**
   - Dual-layer verification: fast deterministic matching followed by DeBERTa-v3 natural language inference.
   - Refusal engine classifying missing or unsupported claims into explicit refusal payloads with explanatory rationales.

4. **Evidence-First Q&A (`backend/retrieval/`):**
   - **Query Router:** Classifies question intent (`CANONICAL_FIELD`, `CLAUSE_LOOKUP`, `OPEN_SEARCH`, `LEGAL_ADVICE_REFUSAL`, `GENERAL_OUT_OF_BOUNDS`) and neutralizes adversarial instructions.
   - **Retrieval Ladder:** Multi-tier fallback ladder from canonical field lookup to clause locator to BM25 lexical ranking.
   - **Evidence Selector:** Isolates verbatim supporting quotations and computes physical bounding boxes.
   - **Constrained Generator:** Synthesizes factual answers grounded strictly in retrieved context.

5. **Editorial UI (`frontend/`):**
   - Side-by-side interactive interface: PDF document surface on the left with dynamic bounding box highlight overlays and pan/zoom controls.
   - Evidence inspector on the right with categorized claim cards, verification chips, and an interactive Q&A research desk.

---

## Getting Started

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & **npm**

### 1. Backend Setup

```powershell
# Navigate to project root
cd "e:\Educational\College\MCA\hackethon\Google\legal ai"

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r backend/requirements.txt

# Configure environment variables
Copy-Item .env.example .env

# Run automated test suite (110 tests)
pytest tests -v

# Start FastAPI backend server
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend documentation and OpenAPI specs will be available at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

### 2. Frontend Setup

```powershell
# Navigate to frontend directory
cd frontend

# Install frontend dependencies
npm install

# Start Vite development server
npm run dev
```

Frontend application will be accessible at:
- Web App: `http://localhost:5173`

---

## API Reference

| Endpoint | Method | Input | Description |
| :--- | :--- | :--- | :--- |
| `/health` | `GET` | None | Service heartbeat and configuration status |
| `/documents/parse` | `POST` | `multipart/form-data` (PDF) | Extracts raw text spans, pages, and spatial bounding boxes |
| `/documents/extract` | `POST` | `multipart/form-data` (PDF) | Extracts structured candidate claims with provenance mapping |
| `/documents/verify` | `POST` | `multipart/form-data` (PDF) | End-to-end extraction and formal verification pipeline |
| `/documents/ask` | `POST` | `multipart/form-data` (PDF, `question`, `history`) | Evidence-first grounded Q&A with coordinate citations |

---

## Running Verification Tests

```powershell
# Run the complete test suite
pytest tests -v

# Run targeted subsystem tests
pytest tests/test_qa_security.py -v       # Prompt-injection & adversarial override tests
pytest tests/test_qa_golden.py -v         # Golden agreement question-answering tests
pytest tests/test_golden_verification.py -v# End-to-end verification gate tests
```

---

## License

MIT License. See project documentation for architectural details.
