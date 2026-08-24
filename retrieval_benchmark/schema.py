"""Shared query and result schemas."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Query:
    query_id: str
    text: str


@dataclass(frozen=True)
class RankedSource:
    source_id: str
    score: float
    rank: int
    trace: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    query_id: str
    method: str
    implementation_id: str
    ranked_sources: tuple[RankedSource, ...]
    abstained: bool
    latency_ms: float
    api_cost_usd: float
    run_status: str
    configuration: dict[str, Any]
    method_answer: str = "NOT_APPLICABLE"
    trace: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.ranked_sources) > 3:
            raise ValueError("Top-3 contract violated")
        if self.abstained and self.ranked_sources:
            raise ValueError("abstained results cannot contain ranked sources")
        if not self.abstained and not self.ranked_sources:
            raise ValueError("non-abstained results require ranked sources")
        if tuple(item.rank for item in self.ranked_sources) != tuple(range(1, len(self.ranked_sources) + 1)):
            raise ValueError("ranks must be consecutive from one")
        if len({item.source_id for item in self.ranked_sources}) != len(self.ranked_sources):
            raise ValueError("duplicate Source IDs are not allowed")
        if self.api_cost_usd != 0.0:
            raise ValueError("this local benchmark must have zero API cost")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
