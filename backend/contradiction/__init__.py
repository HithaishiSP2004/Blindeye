"""Contradiction detection and evidence relationship subsystem."""

from backend.contradiction.context_matcher import ContextMatcher
from backend.contradiction.detector import ContradictionDetector
from backend.contradiction.extractor import CandidateExtractor, CandidateStatement
from backend.models.contradiction import (
    ContradictionActor,
    ContradictionEvidence,
    ContradictionFinding,
    ContradictionResponse,
    ContradictionStatus,
    ContradictionSubject,
)

__all__ = [
    "ContradictionStatus",
    "ContradictionActor",
    "ContradictionSubject",
    "ContradictionEvidence",
    "ContradictionFinding",
    "ContradictionResponse",
    "CandidateExtractor",
    "CandidateStatement",
    "ContextMatcher",
    "ContradictionDetector",
]
