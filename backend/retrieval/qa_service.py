import logging
import re
from typing import Dict, List, Optional
from backend.models.document import DocumentTree
from backend.models.extraction import StructuredAgreement
from backend.models.qa import (
    AnswerStatus,
    QAResponse,
    QuestionType,
    RetrievalMetadata,
    RetrievalMethod,
)
from backend.retrieval.clause_retriever import ClauseRetriever
from backend.retrieval.constrained_generator import (
    AnswerGenerator,
    GeminiGenerator,
)
from backend.retrieval.evidence_selector import EvidenceSelector
from backend.retrieval.field_lookup import FieldLookup
from backend.retrieval.lexical_retriever import LexicalRetriever
from backend.retrieval.qa_verifier import QAVerifier
from backend.retrieval.query_router import QueryRouter

logger = logging.getLogger(__name__)


def _resolve_coreference(question: str, history: Optional[List[Dict[str, str]]]) -> str:
    """Lightweight coreference resolution using conversation history (context only, never evidence).

    Enforces Correction 12:
    Conversation history is CONTEXT ONLY, NOT EVIDENCE.
    Never answer from previous assistant output alone.
    """
    if not history:
        return question

    clean_q = question.strip()
    lower_q = clean_q.lower()

    # Check for pronoun or referential queries e.g. "when is it due?", "how much is it?"
    has_pronoun = bool(re.search(r"\b(it|this|that|them)\b", lower_q))
    if not has_pronoun:
        return clean_q

    # Inspect last user question to identify subject
    last_user_turn = None
    for turn in reversed(history):
        if turn.get("role") in ("user", "human"):
            last_user_turn = turn.get("text", "")
            break

    if not last_user_turn:
        return clean_q

    last_lower = last_user_turn.lower()
    if "rent" in last_lower and "rent" not in lower_q:
        return f"{clean_q} (referring to rent)"
    if "deposit" in last_lower and "deposit" not in lower_q:
        return f"{clean_q} (referring to security deposit)"
    if "notice" in last_lower and "notice" not in lower_q:
        return f"{clean_q} (referring to notice period)"

    return clean_q


class QAService:
    """Master orchestrator for Evidence-First Residential Agreement Q&A.

    Preserves the strict flow:
    Question -> QueryRouter -> Retrieval Ladder -> Evidence Selection -> QAVerifier -> ConstrainedGenerator -> QAResponse

    Enforces all Phase 5 corrections:
    - Configurable Gemini model (gemini-3.8-flash default) (Correction 1)
    - QuestionType separated from AnswerStatus (Correction 2)
    - Formal Q&A verification contract (Correction 3)
    - Retrieval score != confidence (Correction 4)
    - Multiple candidate passages produce AMBIGUOUS, not contradiction (Correction 5)
    - Deterministic fast path for canonical fields (Correction 6)
    - Replaceable generator architecture (Correction 7)
    - Evidence-only LLM inputs (Correction 8)
    - Coordinate system and quotes locked to DocumentTree (Correction 9 & 10)
    - Stateless API design (Correction 11)
    """

    def __init__(
        self,
        query_router: Optional[QueryRouter] = None,
        field_lookup: Optional[FieldLookup] = None,
        clause_retriever: Optional[ClauseRetriever] = None,
        lexical_retriever: Optional[LexicalRetriever] = None,
        evidence_selector: Optional[EvidenceSelector] = None,
        qa_verifier: Optional[QAVerifier] = None,
        generator: Optional[AnswerGenerator] = None,
    ):
        self.router = query_router or QueryRouter()
        self.field_lookup = field_lookup or FieldLookup()
        self.clause_retriever = clause_retriever or ClauseRetriever()
        self.lexical_retriever = lexical_retriever or LexicalRetriever()
        self.evidence_selector = evidence_selector or EvidenceSelector()
        self.verifier = qa_verifier or QAVerifier()
        self.generator = generator or GeminiGenerator()

    async def answer_question(
        self,
        document_tree: DocumentTree,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        structured_agreement: Optional[StructuredAgreement] = None,
    ) -> QAResponse:
        """Process natural language question through retrieval, verification, and grounded generation."""
        # 1. Coreference resolution (Correction 12)
        resolved_question = _resolve_coreference(question, conversation_history)

        # 2. Query routing and safety/refusal classification (Correction 2, 13, 15, 16)
        route_res = self.router.route(resolved_question)

        # Handle policy refusal (Legal advice, external law, out of scope)
        if route_res.is_refused:
            answer_text = await self.generator.generate_answer(
                question=question,
                evidence=[],
                status=AnswerStatus.REFUSED,
                refusal_reason=route_res.refusal_reason,
            )
            return QAResponse(
                question=question,
                status=AnswerStatus.REFUSED,
                question_type=route_res.question_type,
                answer=answer_text,
                evidence=[],
                retrieval=RetrievalMetadata(
                    method=RetrievalMethod.FIELD_LOOKUP,
                    candidates_reviewed=0,
                ),
                refusal_reason=route_res.refusal_reason,
            )

        clean_query = route_res.cleaned_query

        # 3. Fast Path: Canonical Field Lookup (Correction 6 & 10)
        # Check canonical facts first (rent, deposit, duration, dates, parties, address, lock-in)
        field_match = self.field_lookup.lookup(clean_query, structured_agreement, document_tree)
        if field_match.is_matched:
            # If matched as NOT_FOUND (e.g. property address, lock-in period absent from agreement)
            if field_match.status == AnswerStatus.NOT_FOUND:
                return QAResponse(
                    question=question,
                    status=AnswerStatus.NOT_FOUND,
                    question_type=route_res.question_type,
                    answer=field_match.answer or "The agreement does not contain this information.",
                    evidence=[],
                    retrieval=RetrievalMetadata(
                        method=RetrievalMethod.FIELD_LOOKUP,
                        candidates_reviewed=0,
                    ),
                )

            # If matched as AMBIGUOUS
            if field_match.status == AnswerStatus.AMBIGUOUS:
                return QAResponse(
                    question=question,
                    status=AnswerStatus.AMBIGUOUS,
                    question_type=route_res.question_type,
                    answer=field_match.answer or "Multiple ambiguous provisions were found.",
                    evidence=[],
                    retrieval=RetrievalMetadata(
                        method=RetrievalMethod.FIELD_LOOKUP,
                        candidates_reviewed=2,
                    ),
                )

            # If matched and answered with verified provenance
            if field_match.status == AnswerStatus.ANSWERED and field_match.evidence:
                return QAResponse(
                    question=question,
                    status=AnswerStatus.ANSWERED,
                    question_type=route_res.question_type,
                    answer=field_match.answer or field_match.evidence[0].quote,
                    evidence=field_match.evidence,
                    retrieval=RetrievalMetadata(
                        method=RetrievalMethod.FIELD_LOOKUP,
                        candidates_reviewed=1,
                    ),
                )

        # 4. Exact Clause Lookup (Correction 17 & 19)
        # E.g. "What does Clause 3 say about repairs?" or "Section 4"
        if route_res.question_type == QuestionType.CLAUSE_LOOKUP or route_res.target_clause:
            clause_res = self.clause_retriever.retrieve_clause(
                clean_query,
                document_tree,
                target_number=route_res.target_clause,
            )
            if clause_res.status == AnswerStatus.ANSWERED and clause_res.clause:
                # If question asked specifically about a topic within the clause (e.g. "about repairs"),
                # select the most precise evidence sentence
                if "about" in clean_query.lower() or "for" in clean_query.lower():
                    refined_evidence = self.evidence_selector.select_evidence(
                        clause_res.clause, clean_query, document_tree
                    )
                    evidence_to_use = refined_evidence or clause_res.evidence
                else:
                    evidence_to_use = clause_res.evidence

                return QAResponse(
                    question=question,
                    status=AnswerStatus.ANSWERED,
                    question_type=QuestionType.CLAUSE_LOOKUP,
                    answer=clause_res.answer or evidence_to_use[0].quote,
                    evidence=evidence_to_use,
                    retrieval=RetrievalMetadata(
                        method=RetrievalMethod.CLAUSE_LOOKUP,
                        candidates_reviewed=1,
                    ),
                )
            elif clause_res.status == AnswerStatus.NOT_FOUND:
                return QAResponse(
                    question=question,
                    status=AnswerStatus.NOT_FOUND,
                    question_type=QuestionType.CLAUSE_LOOKUP,
                    answer=clause_res.answer or f"The agreement does not contain the requested clause.",
                    evidence=[],
                    retrieval=RetrievalMetadata(
                        method=RetrievalMethod.CLAUSE_LOOKUP,
                        candidates_reviewed=0,
                    ),
                )

        # 5. Lexical Retrieval (Pure-Python BM25) (Correction 4 & 30)
        bm25_candidates = self.lexical_retriever.retrieve(
            clean_query,
            document_tree,
            top_k=3,
            min_score=0.5,
        )

        # If no candidates meet threshold -> NOT_FOUND (Correction 4 & 26)
        if not bm25_candidates:
            ans_text = await self.generator.generate_answer(
                question=question,
                evidence=[],
                status=AnswerStatus.NOT_FOUND,
            )
            return QAResponse(
                question=question,
                status=AnswerStatus.NOT_FOUND,
                question_type=route_res.question_type,
                answer=ans_text,
                evidence=[],
                retrieval=RetrievalMetadata(
                    method=RetrievalMethod.BM25,
                    candidates_reviewed=0,
                    retrieval_score=None,
                ),
            )

        # Check for ambiguous candidates (Correction 5)
        # If top 2 candidates have very close scores and both have high term overlap
        is_ambiguous = False
        if len(bm25_candidates) >= 2:
            score1 = bm25_candidates[0].retrieval_score
            score2 = bm25_candidates[1].retrieval_score
            if score1 > 0 and (score2 / score1) >= 0.95 and score1 < 2.0:
                is_ambiguous = True

        top_candidate = bm25_candidates[0]

        # 6. Evidence Selection (Sentence-level quote + bboxes) (Correction 10 & 18)
        citations = self.evidence_selector.select_evidence(
            top_candidate.clause,
            clean_query,
            document_tree,
        )

        # 7. Formal Verification Contract (Correction 3)
        verif_res = await self.verifier.verify(
            question=clean_query,
            candidate_evidence=citations,
            is_ambiguous_retrieval=is_ambiguous,
        )

        # 8. Constrained Answer Generation (Correction 7 & 8)
        answer_text = await self.generator.generate_answer(
            question=clean_query,
            evidence=citations if verif_res.is_verified else [],
            status=verif_res.status,
        )

        return QAResponse(
            question=question,
            status=verif_res.status,
            question_type=route_res.question_type,
            answer=answer_text,
            evidence=citations if verif_res.is_verified else [],
            retrieval=RetrievalMetadata(
                method=RetrievalMethod.BM25,
                candidates_reviewed=len(bm25_candidates),
                retrieval_score=top_candidate.retrieval_score,
            ),
        )
