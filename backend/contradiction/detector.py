import logging
from typing import Dict, List, Optional
from backend.contradiction.context_matcher import ContextMatcher
from backend.contradiction.extractor import CandidateExtractor, CandidateStatement
from backend.models.contradiction import (
    ContradictionFinding,
    ContradictionResponse,
    ContradictionStatus,
    ContradictionSubject,
)
from backend.models.document import DocumentTree
from backend.models.extraction import StructuredAgreement

logger = logging.getLogger(__name__)


class ContradictionDetector:
    """Core engine for detecting textual contradictions and evidence relationships in agreements.

    Enforces Phase 6 Architecture:
    - DocumentTree is authoritative source; StructuredAgreement is acceleration only (Correction 1).
    - Unknown actor / context yields INSUFFICIENT_CONTEXT, never automatic NO_CONFLICT (Correction 2 & 6).
    - Candidates grouped by subject before comparison to avoid O(n^2) unstructured pairwise evaluation (Correction 3).
    - Explicit BOTH / MUTUAL actor semantics with conservative ambiguity (Correction 4).
    - Non-adjudicating: identifies factual incompatibilities without judging clause priority or validity (Section 20).
    - Dual physical provenance required for CONFIRMED_CONFLICT (Correction 1 & Section 8).
    """

    def __init__(
        self,
        extractor: Optional[CandidateExtractor] = None,
        matcher: Optional[ContextMatcher] = None,
    ):
        self.extractor = extractor or CandidateExtractor()
        self.matcher = matcher or ContextMatcher()

    def detect_contradictions(
        self,
        document_tree: DocumentTree,
        structured_agreement: Optional[StructuredAgreement] = None,
    ) -> ContradictionResponse:
        # Step 1: Extract candidate statements directly from DocumentTree
        candidates = self.extractor.extract_candidates(document_tree, structured_agreement)

        if not candidates:
            return ContradictionResponse(
                findings=[],
                total_conflicts=0,
                evaluation_summary="No factual statements could be extracted from the document for contradiction analysis.",
            )

        # Step 2: Subject grouping before comparison (Correction 3)
        subject_groups: Dict[ContradictionSubject, List[CandidateStatement]] = {}
        for stmt in candidates:
            subject_groups.setdefault(stmt.subject, []).append(stmt)

        all_findings: List[ContradictionFinding] = []
        seen_pairs = set()

        # Step 3: Compare candidate statements within each subject group
        for subject, stmts in subject_groups.items():
            n = len(stmts)
            for i in range(n):
                for j in range(i + 1, n):
                    stmt_a = stmts[i]
                    stmt_b = stmts[j]

                    # Deduplicate: if quotes and clauses are identical, skip
                    if (
                        stmt_a.evidence.clause_id == stmt_b.evidence.clause_id
                        and stmt_a.evidence.exact_quote == stmt_b.evidence.exact_quote
                    ):
                        continue

                    # Avoid redundant duplicate pairings
                    pair_key = tuple(sorted([stmt_a.statement_id, stmt_b.statement_id]))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    finding = self.matcher.evaluate_pair(stmt_a, stmt_b)
                    all_findings.append(finding)

        # Prioritize confirmed conflicts first, then insufficient context, then no conflict
        status_priority = {
            ContradictionStatus.CONFIRMED_CONFLICT: 0,
            ContradictionStatus.INSUFFICIENT_CONTEXT: 1,
            ContradictionStatus.UNRESOLVED: 2,
            ContradictionStatus.NO_CONFLICT: 3,
        }
        all_findings.sort(key=lambda f: status_priority.get(f.status, 99))

        confirmed_count = sum(1 for f in all_findings if f.status == ContradictionStatus.CONFIRMED_CONFLICT)

        if confirmed_count > 0:
            summary = (
                f"Identified {confirmed_count} confirmed textual contradiction(s) requiring review "
                f"across {len(candidates)} analyzed statements in {len(document_tree.clauses)} clauses."
            )
        else:
            summary = (
                f"Analyzed {len(candidates)} factual statements across {len(document_tree.clauses)} clauses. "
                f"No conflicting statements detected among analyzed covenants."
            )

        return ContradictionResponse(
            findings=all_findings,
            total_conflicts=confirmed_count,
            evaluation_summary=summary,
        )
