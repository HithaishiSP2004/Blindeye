import re
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field
from backend.models.contradiction import (
    ContradictionActor,
    ContradictionEvidence,
    ContradictionSubject,
)
from backend.models.document import Clause, DocumentTree
from backend.models.extraction import StructuredAgreement


class CandidateStatement(BaseModel):
    """A factual claim candidate extracted directly from DocumentTree."""

    statement_id: str
    subject: ContradictionSubject
    actor: ContradictionActor
    raw_value: str
    normalized_value: str
    unit: Optional[str] = None
    context_scope: Optional[str] = None
    claim_summary: str
    evidence: ContradictionEvidence


# Regex helpers for actor detection
RE_TENANT = re.compile(r"\b(tenant|licensee|lessee|second\s*party)\b", re.IGNORECASE)
RE_LANDLORD = re.compile(r"\b(landlord|licensor|lessor|first\s*party|owner)\b", re.IGNORECASE)
RE_BOTH = re.compile(r"\b(both\s*parties|either\s*party|mutually|by\s*mutual)\b", re.IGNORECASE)

# Regex helpers for temporal and conditional scopes
RE_INITIAL_TERM = re.compile(r"\b(initial\s*(?:term|period)|during\s*the\s*(?:initial\s*)?term|first\s*year)\b", re.IGNORECASE)
RE_RENEWAL = re.compile(r"\b(after\s*renewal|upon\s*renewal|extended\s*period|renewal\s*term|renewal)\b", re.IGNORECASE)
RE_BREACH = re.compile(r"\b(default|breach|failure\s*to\s*pay|non-payment)\b", re.IGNORECASE)
RE_CONVENIENCE = re.compile(r"\b(without\s*cause|for\s*convenience|at\s*will)\b", re.IGNORECASE)


def detect_actor(text: str) -> ContradictionActor:
    """Detect actor associated with obligation in text.

    Correction 2 & 4: Explicitly identifies TENANT, LANDLORD, BOTH, MUTUAL, or UNKNOWN.
    """
    has_both = bool(RE_BOTH.search(text))
    has_tenant = bool(RE_TENANT.search(text))
    has_landlord = bool(RE_LANDLORD.search(text))

    if has_both:
        return ContradictionActor.BOTH
    if has_tenant and not has_landlord:
        return ContradictionActor.TENANT
    if has_landlord and not has_tenant:
        return ContradictionActor.LANDLORD
    if has_tenant and has_landlord:
        return ContradictionActor.MUTUAL

    return ContradictionActor.UNKNOWN


def detect_context_scope(text: str) -> Optional[str]:
    """Detect specific temporal or conditional boundary conditions."""
    if RE_INITIAL_TERM.search(text):
        return "initial_term"
    if RE_RENEWAL.search(text):
        return "renewal"
    if RE_BREACH.search(text):
        return "breach"
    if RE_CONVENIENCE.search(text):
        return "convenience"
    return None


class CandidateExtractor:
    """Extracts candidate factual statements directly from DocumentTree.

    Enforces Phase 6 Architecture:
    - DocumentTree is the authoritative source (Correction 1).
    - StructuredAgreement is an optional acceleration layer.
    - Slices verbatim quotes with physical coordinates.
    """

    def extract_candidates(
        self,
        document_tree: DocumentTree,
        structured_agreement: Optional[StructuredAgreement] = None,
    ) -> List[CandidateStatement]:
        candidates: List[CandidateStatement] = []
        stmt_idx = 1

        for clause in document_tree.clauses:
            text = clause.text.strip()
            if not text or len(text) < 5:
                continue

            # 1. Notice Period Statements
            # e.g., "Tenant shall provide 30 days notice", "serving thirty (30) days written notice"
            notice_matches = re.finditer(
                r"\b(?:give|provide|serve|with)?\s*(?:thirty|sixty|ninety|fifteen|one|two|three)?\s*\(?([0-9]+)\)?\s*(days?|months?)\s*(?:prior\s*)?(?:written\s*)?notice\b|"
                r"\bnotice\s*(?:period\s*)?(?:of\s*|shall\s*be\s*|is\s*)?(?:thirty|sixty|ninety|fifteen|one|two|three)?\s*\(?([0-9]+)\)?\s*(days?|months?)\b|"
                r"\b(?:give|provide|serve|with)?\s*(thirty|sixty|ninety|fifteen|one|two|three)\s*(days?|months?)\s*(?:prior\s*)?(?:written\s*)?notice\b",
                text,
                re.IGNORECASE,
            )
            for m in notice_matches:
                num_raw = m.group(1) or m.group(3) or m.group(5)
                unit = (m.group(2) or m.group(4) or m.group(6) or "days").lower()
                if not num_raw:
                    continue

                word_map = {
                    "one": "1", "two": "2", "three": "3", "fifteen": "15",
                    "thirty": "30", "sixty": "60", "ninety": "90",
                }
                norm_str = word_map.get(num_raw.lower(), num_raw)
                try:
                    num = str(int(norm_str))
                except ValueError:
                    continue

                actor = detect_actor(text)
                scope = detect_context_scope(text)

                ev = ContradictionEvidence(
                    clause_id=clause.clause_id,
                    clause_number=clause.clause_number,
                    page_number=clause.page_number,
                    exact_quote=text,
                    bounding_boxes=clause.bounding_boxes,
                    spans=clause.spans,
                )
                candidates.append(
                    CandidateStatement(
                        statement_id=f"stmt_{stmt_idx}",
                        subject=ContradictionSubject.NOTICE_PERIOD,
                        actor=actor,
                        raw_value=f"{num} {unit}",
                        normalized_value=num,
                        unit=unit,
                        context_scope=scope,
                        claim_summary=f"{actor.value.capitalize()} notice period: {num} {unit}",
                        evidence=ev,
                    )
                )
                stmt_idx += 1

            # 2. Monthly Rent Statements
            # e.g., "monthly rent of Rs. 35,000", "monthly rent shall be Rs. 35,000", "paying rent of 40,000"
            rent_matches = re.finditer(
                r"\b(?:monthly\s*rent|rent\s*amount|rent)\s*(?:is|shall\s*be|payable\s*at|of|amount\s*of)?\s*(?:of\s*)?(?:rs\.?|inr|₹)?\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]+)?|[0-9]+)(?:\s*/-)?",
                text,
                re.IGNORECASE,
            )
            for m in rent_matches:
                val_str = m.group(1).replace(",", "")
                try:
                    val_num = float(val_str)
                except ValueError:
                    continue

                raw_match = m.group(0).lower()
                if val_num < 500 and not any(curr in raw_match for curr in ["rs", "inr", "₹"]):
                    continue

                actor = ContradictionActor.TENANT
                scope = detect_context_scope(text)

                ev = ContradictionEvidence(
                    clause_id=clause.clause_id,
                    clause_number=clause.clause_number,
                    page_number=clause.page_number,
                    exact_quote=text,
                    bounding_boxes=clause.bounding_boxes,
                    spans=clause.spans,
                )
                candidates.append(
                    CandidateStatement(
                        statement_id=f"stmt_{stmt_idx}",
                        subject=ContradictionSubject.MONTHLY_RENT,
                        actor=actor,
                        raw_value=f"Rs. {int(val_num):,}/-",
                        normalized_value=str(int(val_num)),
                        unit="INR",
                        context_scope=scope,
                        claim_summary=f"Monthly rent: Rs. {int(val_num):,}",
                        evidence=ev,
                    )
                )
                stmt_idx += 1

            # 3. Security Deposit Statements
            # e.g., "security deposit of Rs. 1,00,000"
            deposit_matches = re.finditer(
                r"\b(?:security\s*deposit|refundable\s*deposit|deposit)\s*(?:is|shall\s*be|of|amount\s*of|sum\s*of)?\s*(?:of\s*)?(?:rs\.?|inr|₹)?\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]+)?|[0-9]+)(?:\s*/-)?",
                text,
                re.IGNORECASE,
            )
            for m in deposit_matches:
                val_str = m.group(1).replace(",", "")
                try:
                    val_num = float(val_str)
                except ValueError:
                    continue

                raw_match = m.group(0).lower()
                if val_num < 500 and not any(curr in raw_match for curr in ["rs", "inr", "₹"]):
                    continue

                actor = detect_actor(text)
                if actor == ContradictionActor.UNKNOWN:
                    actor = ContradictionActor.TENANT

                scope = detect_context_scope(text)

                ev = ContradictionEvidence(
                    clause_id=clause.clause_id,
                    clause_number=clause.clause_number,
                    page_number=clause.page_number,
                    exact_quote=text,
                    bounding_boxes=clause.bounding_boxes,
                    spans=clause.spans,
                )
                candidates.append(
                    CandidateStatement(
                        statement_id=f"stmt_{stmt_idx}",
                        subject=ContradictionSubject.SECURITY_DEPOSIT,
                        actor=actor,
                        raw_value=f"Rs. {int(val_num):,}/-",
                        normalized_value=str(int(val_num)),
                        unit="INR",
                        context_scope=scope,
                        claim_summary=f"Security deposit: Rs. {int(val_num):,}",
                        evidence=ev,
                    )
                )
                stmt_idx += 1

            # 4. Tenure Statements
            # e.g., "term of 11 months", "tenure shall be 24 months"
            tenure_matches = re.finditer(
                r"\b(?:term|tenure|period)\s*(?:of\s*|shall\s*be\s*|is\s*)?([0-9]+)\s*(months?|years?)\b",
                text,
                re.IGNORECASE,
            )
            for m in tenure_matches:
                num = m.group(1)
                unit = m.group(2).lower()
                actor = ContradictionActor.MUTUAL
                scope = detect_context_scope(text)

                ev = ContradictionEvidence(
                    clause_id=clause.clause_id,
                    clause_number=clause.clause_number,
                    page_number=clause.page_number,
                    exact_quote=text,
                    bounding_boxes=clause.bounding_boxes,
                    spans=clause.spans,
                )
                candidates.append(
                    CandidateStatement(
                        statement_id=f"stmt_{stmt_idx}",
                        subject=ContradictionSubject.TENURE,
                        actor=actor,
                        raw_value=f"{num} {unit}",
                        normalized_value=str(int(num)),
                        unit=unit,
                        context_scope=scope,
                        claim_summary=f"Agreement tenure: {num} {unit}",
                        evidence=ev,
                    )
                )
                stmt_idx += 1

            # 5. Maintenance & Repair Responsibility
            repairs_matches = re.finditer(
                r"\b(minor\s*repairs|day\s*to\s*day\s*repairs|major\s*repairs|structural\s*repairs|all\s*repairs)\b",
                text,
                re.IGNORECASE,
            )
            for m in repairs_matches:
                repair_type = m.group(1).lower()
                actor = detect_actor(text)

                scope = "minor_repairs" if "minor" in repair_type or "day to day" in repair_type else (
                    "structural_repairs" if "structural" in repair_type or "major" in repair_type else "all_repairs"
                )

                ev = ContradictionEvidence(
                    clause_id=clause.clause_id,
                    clause_number=clause.clause_number,
                    page_number=clause.page_number,
                    exact_quote=text,
                    bounding_boxes=clause.bounding_boxes,
                    spans=clause.spans,
                )
                candidates.append(
                    CandidateStatement(
                        statement_id=f"stmt_{stmt_idx}",
                        subject=ContradictionSubject.MAINTENANCE_RESPONSIBILITY,
                        actor=actor,
                        raw_value=repair_type,
                        normalized_value=repair_type,
                        unit=None,
                        context_scope=scope,
                        claim_summary=f"{actor.value.capitalize()} handles {repair_type}",
                        evidence=ev,
                    )
                )
                stmt_idx += 1

        return candidates
