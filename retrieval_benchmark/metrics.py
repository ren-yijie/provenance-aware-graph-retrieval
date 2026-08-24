"""Source retrieval and abstention metrics."""

from __future__ import annotations

from dataclasses import dataclass


NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class QueryMetrics:
    tp: int
    fp: int
    fn: int
    precision: float | str
    recall: float | str
    f1: float | str
    abstention_correct: bool


def evaluate_query(retrieved: list[str], gold: set[str], *, abstained: bool, answerable: bool) -> QueryMetrics:
    if len(retrieved) > 3:
        raise ValueError("Top-3 contract violated")
    if len(retrieved) != len(set(retrieved)):
        raise ValueError("duplicate retrieved Source IDs")
    if abstained != (len(retrieved) == 0):
        raise ValueError("abstention and retrieved IDs disagree")
    if not answerable:
        if gold:
            raise ValueError("unanswerable question cannot have gold Source IDs")
        fp = len(retrieved)
        return QueryMetrics(
            0, fp, 0,
            0.0 if fp else NOT_APPLICABLE,
            NOT_APPLICABLE,
            NOT_APPLICABLE,
            abstained,
        )
    if not gold:
        raise ValueError("answerable question requires gold Source IDs")
    predicted = set(retrieved)
    tp = len(predicted & gold)
    fp = len(predicted - gold)
    fn = len(gold - predicted)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return QueryMetrics(tp, fp, fn, precision, recall, f1, not abstained)
