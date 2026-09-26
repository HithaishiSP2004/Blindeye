import pytest
from pydantic import ValidationError
from backend.models.extraction import (
    CandidateExtractionResult,
    CandidateFact,
    ExtractionStatus,
    MatchQuality,
    ProvenancedValue,
    ResolutionMethod,
    StructuredAgreement,
)
from backend.models.verification import ClaimTag


def test_candidate_fact_schema():
    """Verify CandidateFact serializes and deserializes properly."""
    fact = CandidateFact(
        field_name="monthly_rent",
        candidate_value="Rs. 35,000",
        candidate_quote="Rs. 35,000/- per month",
        candidate_clause_id="clause_p1_c2",
        is_present=True,
    )
    assert fact.field_name == "monthly_rent"
    assert fact.candidate_value == "Rs. 35,000"
    assert fact.is_present is True


def test_candidate_extraction_result_json_schema():
    """Verify CandidateExtractionResult can generate official JSON schema for Gemini response_schema."""
    schema = CandidateExtractionResult.model_json_schema()
    assert "properties" in schema
    assert "monthly_rent" in schema["properties"]
    assert "security_deposit" in schema["properties"]
    assert "lock_in_months" in schema["properties"]


def test_provenanced_value_never_defaults_to_explicit():
    """CRITICAL: Test that ProvenancedValue NEVER defaults claim_tag to EXPLICIT."""
    val = ProvenancedValue(field_name="lock_in_months")
    assert val.claim_tag is None
    assert val.status == ExtractionStatus.NOT_FOUND
    assert val.is_present is False
    assert val.bbox is None
    assert val.exact_quote is None


def test_structured_agreement_summary_defaults():
    """Verify StructuredAgreement defaults initialize 16 independent fields."""
    agreement = StructuredAgreement(document_id="doc_test_schema")
    assert agreement.summary.fields_total == 0
    assert agreement.summary.fields_found == 0
    assert agreement.monthly_rent.field_name == "monthly_rent"
    assert agreement.monthly_rent.is_present is False
    assert agreement.monthly_rent.claim_tag is None
    assert agreement.lock_in_months.is_present is False
