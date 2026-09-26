import logging
from typing import List
from backend.models.extraction import ProvenancedValue, StructuredAgreement
from backend.models.verification import (
    AtomicClaim,
    ClaimSource,
    ClaimVerificationMetadata,
    VerificationStatus,
)

logger = logging.getLogger(__name__)

# Canonical legal mapping: field -> (subject, default_actor, predicate, unit)
FIELD_DECOMPOSITION_RULES = {
    "monthly_rent": {
        "subject": "monthly_rent",
        "actor": "licensee",
        "predicate": "shall_pay",
        "unit": "INR",
        "qualifiers": ["per month"],
    },
    "security_deposit": {
        "subject": "security_deposit",
        "actor": "licensee",
        "predicate": "has_deposited",
        "unit": "INR",
        "qualifiers": ["refundable", "interest-free"],
    },
    "deposit_refund_days": {
        "subject": "security_deposit",
        "actor": "licensor",
        "predicate": "shall_refund",
        "unit": "DAYS",
        "qualifiers": ["handover of vacant possession"],
    },
    "tenure_months": {
        "subject": "agreement_term",
        "actor": "both",
        "predicate": "shall_remain_in_force",
        "unit": "MONTHS",
        "qualifiers": ["initial duration"],
    },
    "commencement_date": {
        "subject": "license_period",
        "actor": "both",
        "predicate": "commences_on",
        "unit": "DATE",
        "qualifiers": [],
    },
    "notice_period_days": {
        "subject": "agreement_termination",
        "actor": "both",
        "predicate": "shall_serve_prior_notice",
        "unit": "DAYS",
        "qualifiers": ["prior written notice"],
    },
    "landlord_name": {
        "subject": "party_licensor",
        "actor": "licensor",
        "predicate": "identifies_as",
        "unit": "TEXT",
        "qualifiers": ["owner", "first part"],
    },
    "tenant_name": {
        "subject": "party_licensee",
        "actor": "licensee",
        "predicate": "identifies_as",
        "unit": "TEXT",
        "qualifiers": ["occupant", "second part"],
    },
    "property_address": {
        "subject": "licensed_premises",
        "actor": "licensor",
        "predicate": "situated_at",
        "unit": "TEXT",
        "qualifiers": ["demised premises"],
    },
    "agreement_type": {
        "subject": "legal_nature",
        "actor": "both",
        "predicate": "constitutes",
        "unit": "TEXT",
        "qualifiers": ["formal indenture"],
    },
    "execution_date": {
        "subject": "execution",
        "actor": "both",
        "predicate": "executed_on",
        "unit": "DATE",
        "qualifiers": ["date of agreement"],
    },
    "maintenance_responsibility": {
        "subject": "premises_maintenance",
        "actor": "both",
        "predicate": "bears_repair_liability",
        "unit": "TEXT",
        "qualifiers": ["minor repairs vs structural"],
    },
    "lock_in_months": {
        "subject": "lock_in_period",
        "actor": "both",
        "predicate": "restricts_termination_for",
        "unit": "MONTHS",
        "qualifiers": ["non-terminable"],
    },
    "late_payment_penalty": {
        "subject": "rent_default",
        "actor": "licensee",
        "predicate": "incurs_penalty",
        "unit": "INR",
        "qualifiers": ["per day penalty"],
    },
    "permitted_use": {
        "subject": "permitted_use",
        "actor": "licensee",
        "predicate": "restricted_to",
        "unit": "TEXT",
        "qualifiers": ["residential purpose only"],
    },
    "renewal_terms": {
        "subject": "term_extension",
        "actor": "both",
        "predicate": "may_renew_upon",
        "unit": "TEXT",
        "qualifiers": ["mutual consent"],
    },
}


def decompose_field_to_atomic_claim(
    field_name: str,
    provenanced_value: ProvenancedValue,
    document_id: str,
) -> AtomicClaim:
    """Decompose a single extracted field into a structured AtomicClaim."""
    rule = FIELD_DECOMPOSITION_RULES.get(
        field_name,
        {
            "subject": field_name,
            "actor": "both",
            "predicate": "stipulates",
            "unit": "TEXT",
            "qualifiers": [],
        },
    )

    claim_id = f"claim_{document_id[:8]}_{field_name}"
    val = provenanced_value.value

    # Build claim_text description
    actor_str = f"{rule['actor'].capitalize()} " if rule.get("actor") else ""
    claim_text = f"{actor_str}{rule['predicate'].replace('_', ' ')} {rule['subject'].replace('_', ' ')}: {val or 'NOT FOUND'}"

    source = None
    if provenanced_value.is_present and provenanced_value.exact_quote:
        source = ClaimSource(
            clause_id=provenanced_value.source_clause_id,
            clause_number=provenanced_value.source_clause_number,
            page=provenanced_value.page,
            pages=provenanced_value.pages,
            quote=provenanced_value.exact_quote,
            bbox=provenanced_value.bbox,
            bounding_boxes=provenanced_value.bounding_boxes,
        )

    return AtomicClaim(
        claim_id=claim_id,
        claim_text=claim_text,
        field_name=field_name,
        subject=rule["subject"],
        actor=rule.get("actor"),
        predicate=rule["predicate"],
        value=val,
        unit=rule.get("unit"),
        qualifiers=list(rule.get("qualifiers", [])),
        source_document_id=document_id,
        status=VerificationStatus.UNRESOLVED,
        claim_tag=None,  # Must never default to EXPLICIT or NOT_FOUND
        source=source,
        supporting_clause_ids=[provenanced_value.source_clause_id] if provenanced_value.source_clause_id else [],
        exact_quotes=[provenanced_value.exact_quote] if provenanced_value.exact_quote else [],
        bounding_boxes=provenanced_value.bounding_boxes,
        verification=ClaimVerificationMetadata(
            resolution_method=provenanced_value.resolution_method.value if provenanced_value.resolution_method else None,
        ),
    )


def decompose_agreement(
    structured_agreement: StructuredAgreement,
    document_id: str,
) -> List[AtomicClaim]:
    """Decompose all canonical fields in StructuredAgreement into atomic claims."""
    claims: List[AtomicClaim] = []
    field_names = [
        "monthly_rent",
        "security_deposit",
        "deposit_refund_days",
        "tenure_months",
        "commencement_date",
        "notice_period_days",
        "landlord_name",
        "tenant_name",
        "property_address",
        "agreement_type",
        "execution_date",
        "maintenance_responsibility",
        "lock_in_months",
        "late_payment_penalty",
        "permitted_use",
        "renewal_terms",
    ]

    for name in field_names:
        val = getattr(structured_agreement, name, None)
        if isinstance(val, ProvenancedValue):
            claim = decompose_field_to_atomic_claim(name, val, document_id)
            claims.append(claim)

    return claims
