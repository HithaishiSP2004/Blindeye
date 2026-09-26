import pytest
from backend.models.verification import AtomicClaim
from backend.verification.deterministic_checker import DeterministicChecker


@pytest.fixture
def checker():
    return DeterministicChecker()


def test_exact_substring_supported(checker):
    """Verify exact substring in source returns is_supported=True."""
    claim = AtomicClaim(
        claim_id="c1",
        field_name="monthly_rent",
        subject="monthly_rent",
        value="Rs. 35,000/- per month",
        unit="INR",
    )
    source = "2.1 Monthly Rent: The Licensee shall pay a sum of Rs. 35,000/- per month."
    is_sup, reason, method = checker.check_claim_support(claim, source)

    assert is_sup is True
    assert reason == "EXACT_SUBSTRING_SUPPORTED"
    assert method == "DETERMINISTIC_EXACT"


def test_normalized_currency_and_numbers(checker):
    """Verify currency normalization (Rs. vs ₹, commas, /-)."""
    claim = AtomicClaim(
        claim_id="c2",
        field_name="security_deposit",
        subject="security_deposit",
        value="₹1,00,000",
        unit="INR",
    )
    source = "The Licensee has deposited an interest-free refundable deposit of Rs. 1,00,000/- with the Licensor."
    is_sup, reason, method = checker.check_claim_support(claim, source)

    assert is_sup is True
    assert "SUPPORTED" in reason or "MATCH" in reason


def test_numeric_conflict_rejected(checker):
    """Verify numeric mismatch (claim says Rs. 50,000 but source has Rs. 35,000) returns False."""
    claim = AtomicClaim(
        claim_id="c3",
        field_name="monthly_rent",
        subject="monthly_rent",
        value="Rs. 50,000",
        unit="INR",
    )
    source = "The Licensee shall pay a sum of Rs. 35,000/- per month."
    is_sup, reason, method = checker.check_claim_support(claim, source)

    assert is_sup is False
    assert reason == "NUMERIC_VALUE_CONFLICT"


def test_actor_mismatch_licensor_as_tenant(checker):
    """Verify tenant_name claim attributed to Licensor is rejected deterministically."""
    claim = AtomicClaim(
        claim_id="c4",
        field_name="tenant_name",
        subject="party_licensee",
        actor="licensee",
        value="Mr. Rajesh Kumar",
        unit="TEXT",
    )
    source = "by and between Mr. Rajesh Kumar (Licensor) and Ms. Priya Sharma (Licensee)."
    is_sup, reason, method = checker.check_claim_support(claim, source)

    assert is_sup is False
    assert "ACTOR_MISMATCH" in reason


def test_paraphrased_obligation_defers_to_semantic(checker):
    """Verify obligation fields defer to semantic evaluation when exact match is insufficient."""
    claim = AtomicClaim(
        claim_id="c5",
        field_name="maintenance_responsibility",
        subject="premises_maintenance",
        value="Tenant handles interior maintenance",
        unit="TEXT",
    )
    source = "The Licensee shall maintain the interior of the premises in clean condition."
    is_sup, reason, method = checker.check_claim_support(claim, source)

    assert is_sup is None
    assert reason == "SEMANTIC_EVALUATION_REQUIRED"
    assert method == "DEFER_TO_SEMANTIC"
