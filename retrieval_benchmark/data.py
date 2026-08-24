"""Frozen graph and evaluation data loading."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .schema import Query
from .text import build_retrieval_text


RAW_SHA256 = "bd6c8802a864b4599c064d34c01a5d8b460cb4f040bd8339f745bef8dcf61ad5"
CANONICAL_SHA256 = "cfa22f31d1d0186f6f54119c5be0597f88b94c6fa4a1db8c39cef4c975c7f498"


@dataclass(frozen=True)
class BenchmarkData:
    graph: dict[str, object]
    sources: dict[str, dict[str, object]]
    retrieval_texts: dict[str, str]
    queries: tuple[Query, ...]
    gold: dict[str, frozenset[str]]
    answerable: dict[str, bool]
    question_rows: dict[str, dict[str, str]]


def canonical_json_bytes(graph: dict[str, object]) -> bytes:
    return json.dumps(
        graph, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _tabular_rows(path: Path, first_header: str) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    header_index = next(index for index, row in enumerate(rows) if row and row[0] == first_header)
    header = rows[header_index]
    return [dict(zip(header, row)) for row in rows[header_index + 1 :] if row and row[0]]


def load_benchmark(root: Path, *, include_gold: bool = True) -> BenchmarkData:
    graph_path = root / "data" / "test_graph_slice.json"
    raw = graph_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256:
        raise ValueError("raw frozen graph fingerprint mismatch")
    graph = json.loads(raw)
    if hashlib.sha256(canonical_json_bytes(graph)).hexdigest() != CANONICAL_SHA256:
        raise ValueError("canonical frozen graph fingerprint mismatch")
    sources = {
        str(node["id"]): node
        for node in graph["nodes"]
        if node.get("type") == "Source"
    }
    retrieval_texts = {source_id: build_retrieval_text(node) for source_id, node in sources.items()}
    question_rows = {
        row["Question_ID"]: row
        for row in _tabular_rows(root / "data" / "csv" / "question_gold.csv", "Question_ID")
    }
    queries = tuple(Query(query_id, row["Question"]) for query_id, row in question_rows.items())
    if include_gold:
        gold = {
            query_id: frozenset(item for item in row["Expected_Source_IDs"].split("|") if item)
            for query_id, row in question_rows.items()
        }
        answerable = {query_id: row["Answerable"].strip().lower() == "true" for query_id, row in question_rows.items()}
    else:
        gold = {}
        answerable = {}
        question_rows = {}
    return BenchmarkData(graph, sources, retrieval_texts, queries, gold, answerable, question_rows)


def load_retrieval_inputs(root: Path) -> BenchmarkData:
    """Load retriever inputs without exposing gold or evaluation rows."""
    graph_path = root / "data" / "test_graph_slice.json"
    raw = graph_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256:
        raise ValueError("raw frozen graph fingerprint mismatch")
    graph = json.loads(raw)
    if hashlib.sha256(canonical_json_bytes(graph)).hexdigest() != CANONICAL_SHA256:
        raise ValueError("canonical frozen graph fingerprint mismatch")
    sources = {
        str(node["id"]): node
        for node in graph["nodes"]
        if node.get("type") == "Source"
    }
    retrieval_texts = {source_id: build_retrieval_text(node) for source_id, node in sources.items()}
    rows = _tabular_rows(root / "data" / "csv" / "question_gold.csv", "Question_ID")
    queries = tuple(Query(row["Question_ID"], row["Question"]) for row in rows)
    return BenchmarkData(graph, sources, retrieval_texts, queries, {}, {}, {})
