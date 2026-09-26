import re
from typing import Optional, Tuple
from backend.models.verification import AtomicClaim

# Word-to-number mapping for Indian residential agreements
WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "forty-five": 45,
    "fifty": 50, "sixty": 60, "ninety": 90, "hundred": 100, "thousand": 1000,
    "lakh": 100000, "crore": 10000000,
}


def _extract_numeric_tokens(text: str) -> list[int]:
    """Extract all numeric quantities from text, including standard digits and word numbers."""
    if not text:
        return []
    # Find all standard digits
    cleaned = text.replace(",", "").replace("/-", "")
    digits = [int(n) for n in re.findall(r"\b\d+\b", cleaned)]

    # Check common written numbers in parenthetical or word form e.g., 'thirty (30)', 'eleven (11)'
    words = re.findall(r"\b[a-zA-Z\-]+\b", text.lower())
    for w in words:
        if w in WORD_NUMBERS and WORD_NUMBERS[w] not in digits:
            digits.append(WORD_NUMBERS[w])

    return digits


def _normalize_string_for_comparison(text: str) -> str:
    """Normalize string by collapsing spaces, removing punctuation, and lowercasing."""
    if not text:
        return ""
    t = text.lower().replace("/-", "").replace("₹", "rs ").replace("rs.", "rs ")
    t = re.sub(r"[,\.\(\)\-\–]", " ", t)
    return " ".join(t.split())


class DeterministicChecker:
    """Rigorous deterministic support checker for contractual facts against physical source text."""

    def check_claim_support(
        self,
        claim: AtomicClaim,
        source_text: str,
    ) -> Tuple[Optional[bool], str, str]:
        """Evaluate deterministic support between atomic claim and source text.

        Returns:
            Tuple of (is_supported: Optional[bool], reason_code: str, method: str)
            - True: Deterministic support conclusively established (no semantic call needed).
            - False: Deterministic contradiction / role mismatch / wrong value detected.
            - None: Source exists, but deterministic matching is insufficient (requires semantic evaluator).
        """
        if not source_text or not source_text.strip():
            return False, "NO_SOURCE_TEXT", "DETERMINISTIC_EMPTY"

        if not claim.value or not claim.value.strip():
            return False, "EMPTY_CLAIM_VALUE", "DETERMINISTIC_EMPTY"

        claim_val = claim.value.strip()
        field = claim.field_name

        # 1. Check for Actor / Role Inversion (e.g. Licensor as Tenant or Licensee as Landlord)
        if field in ("tenant_name", "landlord_name"):
            name_tokens = [t for t in re.findall(r"[A-Za-z]+", claim_val) if len(t) > 2 and t.lower() not in ("mr", "mrs", "ms", "dr")]
            if name_tokens:
                primary_name = " ".join(name_tokens)
                if field == "tenant_name":
                    # If this name is explicitly qualified as Licensor/Landlord in the source text
                    licensor_pattern = rf"\b{re.escape(name_tokens[-1])}\b.*?\((?:Licensor|Landlord|Lessor)\)"
                    if re.search(licensor_pattern, source_text, re.IGNORECASE):
                        return False, "ACTOR_MISMATCH_LICENSOR_ATTRIBUTED_AS_TENANT", "DETERMINISTIC_ACTOR_CHECK"
                elif field == "landlord_name":
                    # If this name is explicitly qualified as Licensee/Tenant in the source text
                    licensee_pattern = rf"\b{re.escape(name_tokens[-1])}\b.*?\((?:Licensee|Tenant|Lessee)\)"
                    if re.search(licensee_pattern, source_text, re.IGNORECASE):
                        return False, "ACTOR_MISMATCH_LICENSEE_ATTRIBUTED_AS_LANDLORD", "DETERMINISTIC_ACTOR_CHECK"

        # 2. Exact substring match in source text
        if claim_val in source_text:
            return True, "EXACT_SUBSTRING_SUPPORTED", "DETERMINISTIC_EXACT"

        # 3. Normalized string match
        norm_claim = _normalize_string_for_comparison(claim_val)
        norm_source = _normalize_string_for_comparison(source_text)
        if norm_claim in norm_source:
            return True, "NORMALIZED_STRING_SUPPORTED", "DETERMINISTIC_NORMALIZED"

        # 4. Numeric / Currency / Duration support check
        if claim.unit in ("INR", "MONTHS", "DAYS"):
            claim_nums = _extract_numeric_tokens(claim_val)
            source_nums = _extract_numeric_tokens(source_text)

            if claim_nums:
                target_num = claim_nums[0]
                # If target number is present in source quantities
                if target_num in source_nums:
                    return True, "NUMERIC_QUANTITY_MATCH", "DETERMINISTIC_NUMERIC"
                else:
                    # Target number is completely absent from source text numbers
                    # E.g. claim says 50,000 but source text has 35,000
                    if source_nums:
                        return False, "NUMERIC_VALUE_CONFLICT", "DETERMINISTIC_NUMERIC_CONFLICT"

        # 5. Paraphrased / obligation fields require semantic evaluation
        if field in ("maintenance_responsibility", "permitted_use", "renewal_terms"):
            # Defer to semantic evaluation
            return None, "SEMANTIC_EVALUATION_REQUIRED", "DEFER_TO_SEMANTIC"

        # Default fallback if no deterministic match could be established
        return None, "INSUFFICIENT_DETERMINISTIC_MATCH", "DEFER_TO_SEMANTIC"
