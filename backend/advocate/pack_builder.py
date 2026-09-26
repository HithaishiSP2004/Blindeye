"""Deterministic Advocate Preparation Pack Builder.

Compiles verified workspace state into an Evidentiary Agreement Review Dossier.
Strictly non-evaluative:
- Zero generative hallucination; deterministic value propagation only.
- Strict 4-tier evidence taxonomy.
- Dual physical provenance anchored directly to DocumentTree.
- Zero legal opinions, enforceability claims, or statutory judgments.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Union

from backend.models.document import BoundingBox, DocumentTree
from backend.models.verification import (
    AtomicClaim,
    DocumentVerificationResult,
    VerificationResult,
    VerificationStatus,
)
from backend.models.contradiction import (
    ContradictionResponse,
    ContradictionStatus,
)
from backend.models.advocate_pack import (
    AdvocatePack,
    AdvocatePackItem,
    CoverageGapItem,
    DiscrepancyItem,
    EvidenceClassification,
    ExecutiveSummary,
    FinancialCovenantRow,
    ProvenanceFootnote,
)


class PackFootnoteManager:
    """Manages sequential, deduplicated physical provenance footnotes."""

    def __init__(self):
        self.footnotes: List[ProvenanceFootnote] = []
        self._key_map: Dict[Tuple[str, int, str], int] = {}

    def add_footnote(
        self,
        clause_id: Optional[str],
        clause_number: Optional[str],
        page_number: int,
        exact_quote: str,
        bounding_boxes: Optional[List[BoundingBox]] = None,
    ) -> int:
        """Add or retrieve a 1-based footnote index for a physical citation."""
        clean_quote = (exact_quote or "").strip()
        key = (clause_id or "", page_number, clean_quote[:80])
        if key in self._key_map:
            return self._key_map[key]

        index = len(self.footnotes) + 1
        fn = ProvenanceFootnote(
            index=index,
            clause_id=clause_id,
            clause_number=clause_number,
            page_number=page_number,
            exact_quote=clean_quote,
            bounding_boxes=bounding_boxes or [],
        )
        self.footnotes.append(fn)
        self._key_map[key] = index
        return index


def _extract_claim_provenance(
    claim: AtomicClaim,
    footnote_mgr: PackFootnoteManager,
) -> Tuple[List[int], List[str], List[str]]:
    """Extract footnote indices, source clauses, and exact quotes from a claim."""
    indices: List[int] = []
    source_clauses: List[str] = []
    exact_quotes: List[str] = []

    # 1. Primary claim source if present
    if claim.source and claim.source.quote:
        p_idx = footnote_mgr.add_footnote(
            clause_id=claim.source.clause_id,
            clause_number=claim.source.clause_number,
            page_number=claim.source.page or 1,
            exact_quote=claim.source.quote,
            bounding_boxes=claim.source.bounding_boxes or ([claim.source.bbox] if claim.source.bbox else []),
        )
        indices.append(p_idx)
        if claim.source.clause_number:
            source_clauses.append(claim.source.clause_number)
        elif claim.source.clause_id:
            source_clauses.append(claim.source.clause_id)
        exact_quotes.append(claim.source.quote)

    # 2. Additional supporting quotes
    for q in claim.exact_quotes:
        if q not in exact_quotes:
            exact_quotes.append(q)

    # 3. Supporting clause IDs
    for c_id in claim.supporting_clause_ids:
        if c_id not in source_clauses:
            source_clauses.append(c_id)

    return indices, source_clauses, exact_quotes


def _build_summary_item(
    field_title: str,
    claim: Optional[AtomicClaim],
    footnote_mgr: PackFootnoteManager,
) -> AdvocatePackItem:
    """Build an ExecutiveSummary item strictly from a verified AtomicClaim.

    Rules:
    - each value originates from a verified AtomicClaim
    - absent/ambiguous values remain absent/ambiguous
    - no inferred party/property/date information
    """
    if claim and claim.status == VerificationStatus.VERIFIED and claim.value:
        indices, clauses, quotes = _extract_claim_provenance(claim, footnote_mgr)
        return AdvocatePackItem(
            field_name=field_title,
            value=claim.value,
            classification=EvidenceClassification.EXPLICIT_IN_DOCUMENT,
            provenance_indices=indices,
            source_clauses=clauses,
            exact_quotes=quotes,
            notes=None,
        )

    # If claim is absent or unverified
    return AdvocatePackItem(
        field_name=field_title,
        value=None,
        classification=EvidenceClassification.NO_SUPPORTING_PASSAGE,
        provenance_indices=[],
        source_clauses=[],
        exact_quotes=[],
        notes="No supporting provision found for this field.",
    )


def build_advocate_pack(
    document_tree: DocumentTree,
    verification_result: Union[VerificationResult, DocumentVerificationResult],
    contradiction_response: Optional[ContradictionResponse] = None,
    document_name: str = "Residential Agreement",
) -> AdvocatePack:
    """Deterministically compile verified workspace evidence into an AdvocatePack.

    Does NOT re-parse or re-evaluate the document. Reuses existing verified state.
    """
    footnote_mgr = PackFootnoteManager()

    # Index verified claims by canonical field name
    claims_by_field: Dict[str, AtomicClaim] = {}
    for c in verification_result.claims:
        claims_by_field[c.field_name.lower().strip()] = c

    # -------------------------------------------------------------------------
    # I. Executive Summary
    # -------------------------------------------------------------------------
    executive_summary = ExecutiveSummary(
        parties_licensor=_build_summary_item(
            "Licensor / Landlord",
            claims_by_field.get("landlord_name") or claims_by_field.get("licensor"),
            footnote_mgr,
        ),
        parties_licensee=_build_summary_item(
            "Licensee / Tenant",
            claims_by_field.get("tenant_name") or claims_by_field.get("licensee"),
            footnote_mgr,
        ),
        property_address=_build_summary_item(
            "Premises Address",
            claims_by_field.get("property_address"),
            footnote_mgr,
        ),
        monthly_rent=_build_summary_item(
            "Monthly Rent",
            claims_by_field.get("monthly_rent"),
            footnote_mgr,
        ),
        security_deposit=_build_summary_item(
            "Security Deposit",
            claims_by_field.get("security_deposit"),
            footnote_mgr,
        ),
        tenure_months=_build_summary_item(
            "Agreement Tenure",
            claims_by_field.get("tenure_months"),
            footnote_mgr,
        ),
        execution_date=_build_summary_item(
            "Execution / Commencement Date",
            claims_by_field.get("commencement_date") or claims_by_field.get("execution_date"),
            footnote_mgr,
        ),
    )

    # -------------------------------------------------------------------------
    # II. Financial Covenants Matrix
    # -------------------------------------------------------------------------
    financial_covenants: List[FinancialCovenantRow] = []

    # 1. Monthly Rent
    rent_claim = claims_by_field.get("monthly_rent")
    if rent_claim and rent_claim.status == VerificationStatus.VERIFIED and rent_claim.value:
        indices, clauses, quotes = _extract_claim_provenance(rent_claim, footnote_mgr)
        financial_covenants.append(
            FinancialCovenantRow(
                term="Monthly License Fee / Rent",
                amount_or_terms=rent_claim.value,
                actor_responsible="Tenant / Licensee",
                classification=EvidenceClassification.EXPLICIT_IN_DOCUMENT,
                provenance_indices=indices,
                source_clauses=clauses,
                exact_quotes=quotes,
            )
        )

    # 2. Security Deposit
    dep_claim = claims_by_field.get("security_deposit")
    if dep_claim and dep_claim.status == VerificationStatus.VERIFIED and dep_claim.value:
        indices, clauses, quotes = _extract_claim_provenance(dep_claim, footnote_mgr)
        financial_covenants.append(
            FinancialCovenantRow(
                term="Interest-Free Refundable Security Deposit",
                amount_or_terms=dep_claim.value,
                actor_responsible="Tenant / Licensee",
                classification=EvidenceClassification.EXPLICIT_IN_DOCUMENT,
                provenance_indices=indices,
                source_clauses=clauses,
                exact_quotes=quotes,
            )
        )

    # 3. Derived Total Initial Commitment (Rule 6: DERIVED_FROM_CLAUSES may only combine
    # explicitly verified claims and must list all supporting source clauses)
    if (
        rent_claim
        and rent_claim.status == VerificationStatus.VERIFIED
        and rent_claim.value
        and dep_claim
        and dep_claim.status == VerificationStatus.VERIFIED
        and dep_claim.value
    ):
        comb_indices = sorted(list(set(
            (financial_covenants[0].provenance_indices if len(financial_covenants) > 0 else [])
            + (financial_covenants[1].provenance_indices if len(financial_covenants) > 1 else [])
        )))
        comb_clauses = sorted(list(set(
            (financial_covenants[0].source_clauses if len(financial_covenants) > 0 else [])
            + (financial_covenants[1].source_clauses if len(financial_covenants) > 1 else [])
        )))
        comb_quotes = (
            (financial_covenants[0].exact_quotes if len(financial_covenants) > 0 else [])
            + (financial_covenants[1].exact_quotes if len(financial_covenants) > 1 else [])
        )
        financial_covenants.append(
            FinancialCovenantRow(
                term="Total Initial Financial Commitment (Deposit + First Month Fee)",
                amount_or_terms=f"Security Deposit ({dep_claim.value}) + First Month Rent ({rent_claim.value})",
                actor_responsible="Tenant / Licensee",
                classification=EvidenceClassification.DERIVED_FROM_CLAUSES,
                provenance_indices=comb_indices,
                source_clauses=comb_clauses,
                exact_quotes=comb_quotes,
            )
        )

    # 4. Maintenance Responsibility
    maint_claim = claims_by_field.get("maintenance_responsibility")
    if maint_claim and maint_claim.status == VerificationStatus.VERIFIED and maint_claim.value:
        indices, clauses, quotes = _extract_claim_provenance(maint_claim, footnote_mgr)
        financial_covenants.append(
            FinancialCovenantRow(
                term="Society Maintenance Charges",
                amount_or_terms=maint_claim.value,
                actor_responsible=maint_claim.actor or "Mutual / Specified",
                classification=EvidenceClassification.EXPLICIT_IN_DOCUMENT,
                provenance_indices=indices,
                source_clauses=clauses,
                exact_quotes=quotes,
            )
        )

    # 5. Late Payment Penalty
    late_claim = claims_by_field.get("late_payment_penalty")
    if late_claim and late_claim.status == VerificationStatus.VERIFIED and late_claim.value:
        indices, clauses, quotes = _extract_claim_provenance(late_claim, footnote_mgr)
        financial_covenants.append(
            FinancialCovenantRow(
                term="Late Payment Penalty / Interest",
                amount_or_terms=late_claim.value,
                actor_responsible="Tenant / Licensee",
                classification=EvidenceClassification.EXPLICIT_IN_DOCUMENT,
                provenance_indices=indices,
                source_clauses=clauses,
                exact_quotes=quotes,
            )
        )

    # -------------------------------------------------------------------------
    # III. Textual Divergence Schedule (Phase 6 Contradictions)
    # -------------------------------------------------------------------------
    textual_divergence_schedule: List[DiscrepancyItem] = []

    if contradiction_response and contradiction_response.findings:
        for finding in contradiction_response.findings:
            if finding.status == ContradictionStatus.CONFIRMED_CONFLICT:
                # Add footnotes for Source A and Source B
                fn_a = footnote_mgr.add_footnote(
                    clause_id=finding.source_a.clause_id,
                    clause_number=finding.source_a.clause_number,
                    page_number=finding.source_a.page_number,
                    exact_quote=finding.source_a.exact_quote,
                    bounding_boxes=finding.source_a.bounding_boxes,
                )
                fn_b = footnote_mgr.add_footnote(
                    clause_id=finding.source_b.clause_id,
                    clause_number=finding.source_b.clause_number,
                    page_number=finding.source_b.page_number,
                    exact_quote=finding.source_b.exact_quote,
                    bounding_boxes=finding.source_b.bounding_boxes,
                )

                subj_str = str(finding.subject.value if hasattr(finding.subject, "value") else finding.subject)
                actor_str = str(finding.actor.value if hasattr(finding.actor, "value") else finding.actor)

                textual_divergence_schedule.append(
                    DiscrepancyItem(
                        subject=subj_str,
                        actor=actor_str,
                        divergence_summary=(
                            f"{subj_str.replace('_', ' ').title()} divergence: "
                            f"'{finding.value_a}' vs '{finding.value_b}'"
                        ),
                        classification=EvidenceClassification.CONFLICTING_EVIDENCE,
                        source_a_clause=finding.source_a.clause_number or finding.source_a.clause_id,
                        source_a_page=finding.source_a.page_number,
                        source_a_quote=finding.source_a.exact_quote,
                        source_a_provenance_index=fn_a,
                        source_b_clause=finding.source_b.clause_number or finding.source_b.clause_id,
                        source_b_page=finding.source_b.page_number,
                        source_b_quote=finding.source_b.exact_quote,
                        source_b_provenance_index=fn_b,
                        neutral_comparison_statement=finding.explanation,
                    )
                )

    # -------------------------------------------------------------------------
    # IV. Document Coverage & Clarification Gaps
    # -------------------------------------------------------------------------
    coverage_gaps: List[CoverageGapItem] = []

    checked_fields_schema = [
        ("deposit_refund_days", "Security Deposit Refund Timeline", "Searched for explicit timeframe or conditions governing deposit return"),
        ("lock_in_months", "Lock-in Period Commitment", "Searched for minimum lock-in commitment restricting unilateral termination"),
        ("late_payment_penalty", "Late Payment Interest / Penalty", "Searched for default interest rate or daily penalty provisions"),
        ("maintenance_responsibility", "Society Maintenance Charge Apportionment", "Searched for explicit assignment of regular society maintenance fees"),
        ("renewal_terms", "Agreement Renewal Terms & Rent Escalation", "Searched for lease renewal mechanism or standard escalation percentage"),
    ]

    for field_key, field_label, search_scope in checked_fields_schema:
        claim = claims_by_field.get(field_key)
        # If the claim was not found or is unverified / None
        if not claim or claim.status != VerificationStatus.VERIFIED or not claim.value:
            coverage_gaps.append(
                CoverageGapItem(
                    field_name=field_label,
                    classification=EvidenceClassification.NO_SUPPORTING_PASSAGE,
                    status_display="UNADDRESSED",
                    coverage_note="No supporting provision found for this field.",
                    checked_scope=search_scope,
                )
            )

    # Assemble complete pack
    return AdvocatePack(
        document_name=document_name,
        total_pages=max(1, getattr(document_tree, "page_count", getattr(document_tree, "total_pages", 1))),
        compilation_timestamp=datetime.now(timezone.utc).isoformat(),
        executive_summary=executive_summary,
        financial_covenants=financial_covenants,
        textual_divergence_schedule=textual_divergence_schedule,
        coverage_gaps=coverage_gaps,
        footnotes=footnote_mgr.footnotes,
        legal_disclaimer=(
            "Evidentiary Agreement Review Dossier compiled strictly from physical document text. "
            "This document does not constitute legal advice, statutory validation, or advocate representation."
        ),
        builder_version="1.0.0",
    )
