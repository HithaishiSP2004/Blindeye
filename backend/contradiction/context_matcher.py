import uuid
from typing import Dict, List, Optional, Tuple
from backend.contradiction.extractor import CandidateStatement
from backend.models.contradiction import (
    ContradictionActor,
    ContradictionFinding,
    ContradictionStatus,
    ContradictionSubject,
)


class ContextMatcher:
    """Evaluates candidate statement pairs according to Phase 6 context rules.

    Enforces:
    - Subject grouping before comparison (Correction 3).
    - Unknown actor / context yields INSUFFICIENT_CONTEXT, never automatic NO_CONFLICT (Correction 2 & 6).
    - BOTH / MUTUAL vs specific actor yields INSUFFICIENT_CONTEXT (Correction 4).
    - Known different actors (Tenant vs Landlord) yields NO_CONFLICT (valid asymmetry).
    - Disjoint temporal / conditional scopes yield NO_CONFLICT.
    - Identical values yield NO_CONFLICT.
    - Incompatible values for same actor & matching context yield candidate CONFIRMED_CONFLICT.
    """

    def evaluate_pair(
        self,
        stmt_a: CandidateStatement,
        stmt_b: CandidateStatement,
    ) -> ContradictionFinding:
        subject = stmt_a.subject
        finding_id = f"cf_{subject.value.lower()}_{uuid.uuid4().hex[:8]}"

        val_a = stmt_a.raw_value
        val_b = stmt_b.raw_value
        norm_a = stmt_a.normalized_value
        norm_b = stmt_b.normalized_value

        actor_a = stmt_a.actor
        actor_b = stmt_b.actor

        scope_a = stmt_a.context_scope
        scope_b = stmt_b.context_scope

        # Rule 1: Unknown Actor (Correction 2 & 6)
        # If either actor is UNKNOWN and values conflict, do NOT declare NO_CONFLICT.
        # We cannot safely assume mismatch or conflict without explicit party attribution.
        if actor_a == ContradictionActor.UNKNOWN or actor_b == ContradictionActor.UNKNOWN:
            if norm_a != norm_b:
                return ContradictionFinding(
                    finding_id=finding_id,
                    status=ContradictionStatus.INSUFFICIENT_CONTEXT,
                    subject=subject,
                    actor=ContradictionActor.UNKNOWN,
                    value_a=val_a,
                    value_b=val_b,
                    unit=stmt_a.unit or stmt_b.unit,
                    context_scope=scope_a or scope_b,
                    claim_a=stmt_a.claim_summary,
                    claim_b=stmt_b.claim_summary,
                    source_a=stmt_a.evidence,
                    source_b=stmt_b.evidence,
                    explanation=(
                        f"The agreement contains statements with different values ({val_a} vs {val_b}) "
                        f"for {subject.value.replace('_', ' ').lower()}, but the obligated party is not "
                        f"explicitly determinable from the immediate text."
                    ),
                    comparison_method="actor_uncertainty_guard",
                )
            else:
                return ContradictionFinding(
                    finding_id=finding_id,
                    status=ContradictionStatus.NO_CONFLICT,
                    subject=subject,
                    actor=ContradictionActor.UNKNOWN,
                    value_a=val_a,
                    value_b=val_b,
                    unit=stmt_a.unit or stmt_b.unit,
                    context_scope=scope_a or scope_b,
                    claim_a=stmt_a.claim_summary,
                    claim_b=stmt_b.claim_summary,
                    source_a=stmt_a.evidence,
                    source_b=stmt_b.evidence,
                    explanation=f"Both statements specify the same value ({val_a}) regardless of party attribution.",
                    comparison_method="identical_value_affirmation",
                )

        # Rule 2: Explicitly Known Different Actors (Correction 2)
        # Tenant obligation vs Landlord obligation is valid contractual asymmetry, NOT a conflict.
        is_distinct_actors = (
            (actor_a == ContradictionActor.TENANT and actor_b == ContradictionActor.LANDLORD)
            or (actor_a == ContradictionActor.LANDLORD and actor_b == ContradictionActor.TENANT)
        )
        if is_distinct_actors:
            return ContradictionFinding(
                finding_id=finding_id,
                status=ContradictionStatus.NO_CONFLICT,
                subject=subject,
                actor=ContradictionActor.MUTUAL,
                value_a=val_a,
                value_b=val_b,
                unit=stmt_a.unit or stmt_b.unit,
                context_scope=scope_a or scope_b,
                claim_a=stmt_a.claim_summary,
                claim_b=stmt_b.claim_summary,
                source_a=stmt_a.evidence,
                source_b=stmt_b.evidence,
                explanation=(
                    f"These statements assign terms to different parties ({actor_a.value.lower()} vs "
                    f"{actor_b.value.lower()}), representing valid contractual asymmetry rather than a contradiction."
                ),
                comparison_method="actor_asymmetry_resolution",
            )

        # Rule 3: BOTH / MUTUAL vs Specific Actor (Correction 4)
        # e.g., "Both parties shall provide 30 days notice" vs "Tenant shall provide 60 days notice".
        # Conservative ambiguity: yield INSUFFICIENT_CONTEXT unless scope is explicitly proven disjoint.
        is_both_vs_specific = (
            (actor_a in (ContradictionActor.BOTH, ContradictionActor.MUTUAL) and actor_b in (ContradictionActor.TENANT, ContradictionActor.LANDLORD))
            or (actor_b in (ContradictionActor.BOTH, ContradictionActor.MUTUAL) and actor_a in (ContradictionActor.TENANT, ContradictionActor.LANDLORD))
        )
        if is_both_vs_specific:
            if norm_a != norm_b:
                specific_actor = actor_b if actor_a in (ContradictionActor.BOTH, ContradictionActor.MUTUAL) else actor_a
                return ContradictionFinding(
                    finding_id=finding_id,
                    status=ContradictionStatus.INSUFFICIENT_CONTEXT,
                    subject=subject,
                    actor=specific_actor,
                    value_a=val_a,
                    value_b=val_b,
                    unit=stmt_a.unit or stmt_b.unit,
                    context_scope=scope_a or scope_b,
                    claim_a=stmt_a.claim_summary,
                    claim_b=stmt_b.claim_summary,
                    source_a=stmt_a.evidence,
                    source_b=stmt_b.evidence,
                    explanation=(
                        f"One statement specifies terms for both parties while another specifies terms for the "
                        f"{specific_actor.value.lower()}; insufficient context to determine if provisions are "
                        f"mutually exclusive or represent a specific party covenant."
                    ),
                    comparison_method="mutual_specificity_guard",
                )

        # Rule 4: Context / Temporal Scope Differences (Section 4 & 10 Case D)
        # e.g. "initial term" vs "renewal", or "minor repairs" vs "structural repairs".
        if scope_a and scope_b and scope_a != scope_b:
            return ContradictionFinding(
                finding_id=finding_id,
                status=ContradictionStatus.NO_CONFLICT,
                subject=subject,
                actor=actor_a,
                value_a=val_a,
                value_b=val_b,
                unit=stmt_a.unit or stmt_b.unit,
                context_scope=f"{scope_a} vs {scope_b}",
                claim_a=stmt_a.claim_summary,
                claim_b=stmt_b.claim_summary,
                source_a=stmt_a.evidence,
                source_b=stmt_b.evidence,
                explanation=(
                    f"These statements apply to distinct contractual scopes or conditions "
                    f"({scope_a.replace('_', ' ')} vs {scope_b.replace('_', ' ')}); therefore they do not conflict."
                ),
                comparison_method="context_scope_differentiation",
            )

        # Rule 5: Value Comparison
        # If normalized values agree, no conflict.
        if norm_a == norm_b:
            return ContradictionFinding(
                finding_id=finding_id,
                status=ContradictionStatus.NO_CONFLICT,
                subject=subject,
                actor=actor_a,
                value_a=val_a,
                value_b=val_b,
                unit=stmt_a.unit or stmt_b.unit,
                context_scope=scope_a or scope_b,
                claim_a=stmt_a.claim_summary,
                claim_b=stmt_b.claim_summary,
                source_a=stmt_a.evidence,
                source_b=stmt_b.evidence,
                explanation=f"Both statements agree on the same value ({val_a}).",
                comparison_method="identical_value_affirmation",
            )

        # Rule 6: Same Known Actor, Matching Context, Incompatible Values
        # Verify physical provenance (Correction 1 & Phase 6 requirement)
        has_prov_a = bool(stmt_a.evidence.bounding_boxes) or bool(stmt_a.evidence.exact_quote)
        has_prov_b = bool(stmt_b.evidence.bounding_boxes) or bool(stmt_b.evidence.exact_quote)

        if not has_prov_a or not has_prov_b:
            return ContradictionFinding(
                finding_id=finding_id,
                status=ContradictionStatus.INSUFFICIENT_CONTEXT,
                subject=subject,
                actor=actor_a,
                value_a=val_a,
                value_b=val_b,
                unit=stmt_a.unit or stmt_b.unit,
                context_scope=scope_a or scope_b,
                claim_a=stmt_a.claim_summary,
                claim_b=stmt_b.claim_summary,
                source_a=stmt_a.evidence,
                source_b=stmt_b.evidence,
                explanation="Physical source provenance could not be fully grounded in DocumentTree for both statements.",
                comparison_method="provenance_gated_evaluation",
            )

        # Confirmed Conflict (Non-adjudicating explanation)
        cl_a_lbl = f"Clause {stmt_a.evidence.clause_number}" if stmt_a.evidence.clause_number else "Agreement text"
        cl_b_lbl = f"Clause {stmt_b.evidence.clause_number}" if stmt_b.evidence.clause_number else "Agreement text"

        return ContradictionFinding(
            finding_id=finding_id,
            status=ContradictionStatus.CONFIRMED_CONFLICT,
            subject=subject,
            actor=actor_a,
            value_a=val_a,
            value_b=val_b,
            unit=stmt_a.unit or stmt_b.unit,
            context_scope=scope_a or scope_b,
            claim_a=stmt_a.claim_summary,
            claim_b=stmt_b.claim_summary,
            source_a=stmt_a.evidence,
            source_b=stmt_b.evidence,
            explanation=(
                f"{cl_a_lbl} (Page {stmt_a.evidence.page_number}) states {val_a}, whereas "
                f"{cl_b_lbl} (Page {stmt_b.evidence.page_number}) states {val_b}. "
                f"These statements assign incompatible terms to the {actor_a.value.lower()} under the same subject."
            ),
            comparison_method="deterministic_context_match",
        )
