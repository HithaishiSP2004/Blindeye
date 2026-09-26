"""Structured Evidence Extraction and Deterministic Provenance Resolution."""

from backend.extraction.provenance_resolver import resolve_provenance
from backend.extraction.structured_extractor import extract_candidate_facts

__all__ = ["extract_candidate_facts", "resolve_provenance"]
