import pytest
from backend.models.verification import AtomicClaim
from backend.verification.semantic_evaluator import DeterministicMockSemanticEvaluator


@pytest.mark.asyncio
async def test_mock_semantic_evaluator_support():
    """Verify semantic support on paraphrased maintenance clause."""
    evaluator = DeterministicMockSemanticEvaluator()
    claim = AtomicClaim(
        claim_id="c_maint",
        field_name="maintenance_responsibility",
        subject="premises_maintenance",
        value="Licensee is responsible for minor repairs up to Rs. 2000",
    )
    source = "All minor repairs such as tap washers, bulb replacements, and minor leakages up to Rs. 2,000 shall be borne by the Licensee."

    res = await evaluator.evaluate(claim, source)
    assert res.decision == "SUPPORTED"
    assert res.reason_code == "SEMANTIC_SUPPORT"


@pytest.mark.asyncio
async def test_mock_semantic_evaluator_non_support():
    """Verify semantic non-support on irrelevant passage."""
    evaluator = DeterministicMockSemanticEvaluator()
    claim = AtomicClaim(
        claim_id="c_maint",
        field_name="maintenance_responsibility",
        subject="premises_maintenance",
        value="Tenant is responsible for structural wall repairs",
    )
    source = "The tenant shall pay monthly rent of Rs. 35,000 on or before the 5th day."

    res = await evaluator.evaluate(claim, source)
    assert res.decision == "NOT_SUPPORTED"
    assert res.reason_code == "SEMANTIC_NON_SUPPORT"
