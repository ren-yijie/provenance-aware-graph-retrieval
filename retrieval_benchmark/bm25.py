"""Deterministic Okapi BM25 retrieval."""

from __future__ import annotations

import math
import time
from collections import Counter

from .schema import Query, RankedSource, RetrievalResult
from .text import lexical_tokens


class BM25Retriever:
    method = "BM25 Keyword Search"
    implementation_id = "bm25_v1"

    def __init__(self, retrieval_texts: dict[str, str], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.source_ids = tuple(sorted(retrieval_texts))
        self.documents = {source_id: lexical_tokens(retrieval_texts[source_id]) for source_id in self.source_ids}
        self.term_frequencies = {source_id: Counter(tokens) for source_id, tokens in self.documents.items()}
        self.lengths = {source_id: len(tokens) for source_id, tokens in self.documents.items()}
        self.average_length = sum(self.lengths.values()) / len(self.lengths)
        self.document_frequency = Counter()
        for tokens in self.documents.values():
            self.document_frequency.update(set(tokens))

    def score(self, query_text: str, source_id: str) -> float:
        query_terms = Counter(lexical_tokens(query_text))
        score = 0.0
        length = self.lengths[source_id]
        frequencies = self.term_frequencies[source_id]
        total = len(self.source_ids)
        for term, query_frequency in query_terms.items():
            frequency = frequencies[term]
            if not frequency:
                continue
            df = self.document_frequency[term]
            idf = math.log(1.0 + (total - df + 0.5) / (df + 0.5))
            denominator = frequency + self.k1 * (1.0 - self.b + self.b * length / self.average_length)
            score += query_frequency * idf * (frequency * (self.k1 + 1.0) / denominator)
        return score

    def retrieve(self, query: Query) -> RetrievalResult:
        started = time.perf_counter_ns()
        scores = [(source_id, self.score(query.text, source_id)) for source_id in self.source_ids]
        ranked = sorted(scores, key=lambda item: (-item[1], item[0]))
        abstained = not ranked or ranked[0][1] == 0.0
        selected = () if abstained else tuple(
            RankedSource(source_id, score, rank, {"bm25_score": score})
            for rank, (source_id, score) in enumerate(ranked[:3], 1)
        )
        elapsed = (time.perf_counter_ns() - started) / 1_000_000
        return RetrievalResult(
            query.query_id, self.method, self.implementation_id, selected, abstained,
            elapsed, 0.0, "COMPLETE",
            {"k1": self.k1, "b": self.b, "top_k": 3, "tokenization": "preregistered_v1"},
            trace={"query_tokens": lexical_tokens(query.text)},
        )
