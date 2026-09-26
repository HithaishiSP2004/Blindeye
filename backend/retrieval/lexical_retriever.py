import math
import re
from typing import Dict, List, Set
from pydantic import BaseModel
from backend.models.document import Clause, DocumentTree

# Common English stopwords to ignore in BM25 scoring
STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves", "tell", "agreement", "clause",
}


def _tokenize(text: str) -> List[str]:
    """Tokenize and normalize text into clean alphanumeric stems/words."""
    if not text:
        return []
    words = re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


class BM25Candidate(BaseModel):
    """Candidate clause returned by BM25 scoring."""

    clause: Clause
    retrieval_score: float
    matched_terms: List[str] = []


class LexicalRetriever:
    """Pure-Python BM25 ranking across segmented DocumentTree clauses.

    Adheres strictly to Phase 5 Corrections:
    - Pure Python BM25 without ChromaDB or external vector DB (Correction 30).
    - BM25 score is labeled retrieval_score, NEVER confidence or AI confidence (Correction 4).
    - Multiple candidate passages produce AMBIGUOUS, not contradiction (Correction 5).
    - Low-score candidates return empty results to prevent hallucinated answers (Correction 4 & 26).
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def retrieve(
        self,
        query: str,
        document_tree: DocumentTree,
        top_k: int = 3,
        min_score: float = 0.5,
    ) -> List[BM25Candidate]:
        """Rank clauses against query tokens using BM25 scoring."""
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        # Filter out header/footer clauses
        corpus_clauses: List[Clause] = [
            c for c in document_tree.clauses if not c.is_header_footer and c.text.strip()
        ]
        if not corpus_clauses:
            return []

        n_docs = len(corpus_clauses)
        doc_tokens_list = [_tokenize(c.text) for c in corpus_clauses]
        doc_lengths = [len(tokens) for tokens in doc_tokens_list]
        avg_doc_len = sum(doc_lengths) / max(n_docs, 1)

        # Inverted index: term -> set of doc indices
        df: Dict[str, int] = {}
        for tokens in doc_tokens_list:
            unique_terms = set(tokens)
            for term in unique_terms:
                df[term] = df.get(term, 0) + 1

        # Compute BM25 score for each document
        candidates: List[BM25Candidate] = []
        for idx, (clause, tokens, d_len) in enumerate(zip(corpus_clauses, doc_tokens_list, doc_lengths)):
            if not tokens:
                continue

            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1

            score = 0.0
            matched = []
            for q_term in query_tokens:
                if q_term in tf:
                    doc_freq = df.get(q_term, 0)
                    # Standard BM25 IDF formulation
                    idf = math.log((n_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
                    term_freq = tf[q_term]
                    numerator = term_freq * (self.k1 + 1)
                    denominator = term_freq + self.k1 * (1 - self.b + self.b * (d_len / max(avg_doc_len, 1.0)))
                    score += idf * (numerator / denominator)
                    matched.append(q_term)

            if score >= min_score and matched:
                candidates.append(
                    BM25Candidate(
                        clause=clause,
                        retrieval_score=round(score, 4),
                        matched_terms=list(set(matched)),
                    )
                )

        # Sort descending by retrieval_score
        candidates.sort(key=lambda c: c.retrieval_score, reverse=True)
        return candidates[:top_k]
