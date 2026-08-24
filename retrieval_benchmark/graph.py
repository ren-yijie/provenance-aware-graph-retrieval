"""Deterministic unweighted and provenance-aware graph retrieval."""

from __future__ import annotations

import math
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from .bm25 import BM25Retriever
from .schema import Query, RankedSource, RetrievalResult
from .text import all_tokens, lexical_tokens, normalize_text, phrase_in_text


PROFESSIONAL_CUES = frozenset(
    "associate banker cardiologist consultant director entrepreneur founder investment lawyer "
    "managing officer partner physician professor retired works designer".split()
)


@dataclass(frozen=True)
class Seed:
    node_id: str
    node_type: str
    match_class: int
    match_label: str
    match_kind: str


def _match_alias(alias: str, query_text: str) -> tuple[int, str] | None:
    alias_tokens = lexical_tokens(alias)
    if not alias_tokens:
        return None
    query_tokens = lexical_tokens(query_text)
    query_set = set(query_tokens)
    if phrase_in_text(alias, query_text):
        return 3, "exact_phrase"
    if set(alias_tokens).issubset(query_set):
        return 2, "complete_token"
    overlap = len(set(alias_tokens) & query_set)
    if len(set(alias_tokens)) >= 2 and overlap >= 2 and overlap / len(set(alias_tokens)) >= 0.5:
        return 1, "partial_multi_token"
    return None


class GraphIndex:
    def __init__(self, graph: dict[str, object]) -> None:
        self.graph = graph
        self.nodes = {str(node["id"]): node for node in graph["nodes"]}
        self.edges = {str(edge["id"]): edge for edge in graph["edges"]}
        self.adjacency: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for edge_id, edge in self.edges.items():
            source, target = str(edge["source"]), str(edge["target"])
            if source not in self.nodes or target not in self.nodes:
                raise ValueError(f"broken graph edge {edge_id}")
            self.adjacency[source].append((target, edge_id))
            self.adjacency[target].append((source, edge_id))
        for node_id in self.adjacency:
            self.adjacency[node_id].sort()
        self.source_ids = frozenset(node_id for node_id, node in self.nodes.items() if node["type"] == "Source")
        self.generic_concepts = self._generic_concepts()
        self.collision_entities = self._collision_entities()

    def aliases(self, node: dict[str, object]) -> tuple[str, ...]:
        aliases = {str(node.get("name", "")).strip()}
        if node.get("type") == "Discovered_entity":
            attributes = node.get("attributes", {})
            if isinstance(attributes, dict):
                tags = attributes.get("tags", [])
                if isinstance(tags, list):
                    aliases.update(str(tag).strip() for tag in tags if isinstance(tag, str))
        return tuple(sorted(alias for alias in aliases if alias))

    def seeds(self, query_text: str) -> tuple[Seed, ...]:
        seeds: list[Seed] = []
        for node_id, node in self.nodes.items():
            if node.get("type") not in {"Discovered_entity", "Concept"}:
                continue
            matches = []
            for alias in self.aliases(node):
                matched = _match_alias(alias, query_text)
                if matched:
                    matches.append((matched[0], alias, matched[1]))
            if matches:
                match_class, label, kind = sorted(matches, key=lambda item: (-item[0], normalize_text(item[1]), item[1]))[0]
                seeds.append(Seed(node_id, str(node["type"]), match_class, label, kind))
        return tuple(sorted(seeds, key=lambda seed: (-seed.match_class, seed.node_id)))

    def paths_to_sources(self, seed: Seed, max_length: int = 2) -> list[dict[str, Any]]:
        paths: list[dict[str, Any]] = []
        queue = deque([(seed.node_id, (seed.node_id,), tuple())])
        while queue:
            current, node_path, edge_path = queue.popleft()
            depth = len(edge_path)
            if depth and current in self.source_ids:
                paths.append(self._serialize_path(seed, node_path, edge_path))
                continue
            if depth == max_length:
                continue
            for neighbor, edge_id in self.adjacency.get(current, []):
                if neighbor in node_path:
                    continue
                queue.append((neighbor, node_path + (neighbor,), edge_path + (edge_id,)))
        return paths

    def candidates(self, query_text: str) -> tuple[tuple[Seed, ...], dict[str, list[dict[str, Any]]]]:
        seeds = self.seeds(query_text)
        candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for seed in seeds:
            for path in self.paths_to_sources(seed):
                candidates[path["source_id"]].append(path)
        for source_id in candidates:
            candidates[source_id].sort(key=lambda path: (path["path_length"], path["seed_id"], tuple(path["edge_ids"])))
        return seeds, dict(candidates)

    def _serialize_path(self, seed: Seed, node_path: tuple[str, ...], edge_path: tuple[str, ...]) -> dict[str, Any]:
        edge_trace = []
        for index, edge_id in enumerate(edge_path):
            edge = self.edges[edge_id]
            traversed_from, traversed_to = node_path[index], node_path[index + 1]
            edge_trace.append({
                "edge_id": edge_id,
                "edge_type": edge["type"],
                "stored_source": edge["source"],
                "stored_target": edge["target"],
                "traversal_direction": "stored" if edge["source"] == traversed_from else "reverse",
                "attributes": edge.get("attributes", {}),
            })
        return {
            "seed_id": seed.node_id,
            "seed_type": seed.node_type,
            "seed_label": seed.match_label,
            "seed_match_class": seed.match_class,
            "seed_match_kind": seed.match_kind,
            "node_ids": list(node_path),
            "edge_ids": list(edge_path),
            "edge_types": [edge["edge_type"] for edge in edge_trace],
            "edges": edge_trace,
            "path_length": len(edge_path),
            "source_id": node_path[-1],
        }

    def _generic_concepts(self) -> dict[str, dict[str, object]]:
        threshold = math.ceil(0.20 * len(self.source_ids))
        generic: dict[str, dict[str, object]] = {}
        for node_id, node in self.nodes.items():
            if node.get("type") != "Concept":
                continue
            artificial_seed = Seed(node_id, "Concept", 3, str(node.get("name", node_id)), "exact_phrase")
            supported = sorted({path["source_id"] for path in self.paths_to_sources(artificial_seed, 2)})
            if len(supported) >= threshold:
                generic[node_id] = {"name": node.get("name", node_id), "source_count": len(supported), "source_ids": supported}
        return generic

    def _collision_entities(self) -> dict[str, dict[str, object]]:
        collisions: dict[str, dict[str, object]] = {}
        for node_id, node in self.nodes.items():
            if node.get("type") != "Discovered_entity":
                continue
            entity_name = normalize_text(str(node.get("name", "")))
            matching: list[tuple[str, str]] = []
            for neighbor, edge_id in self.adjacency.get(node_id, []):
                source = self.nodes[neighbor]
                if source.get("type") != "Source" or self.edges[edge_id].get("type") != "MENTIONS":
                    continue
                metadata = source.get("attributes", {}).get("metadata", {})
                if normalize_text(str(metadata.get("name", ""))) == entity_name:
                    matching.append((neighbor, str(metadata.get("donor_id", ""))))
            if len(matching) >= 2 and len({donor_id for _, donor_id in matching}) >= 2:
                collisions[node_id] = {"name": node.get("name", node_id), "sources": sorted(source for source, _ in matching)}
        return collisions


class UnweightedGraphRetriever:
    method = "Unweighted Graph Retrieval"
    implementation_id = "unweighted_graph_v1"

    def __init__(self, graph: dict[str, object]) -> None:
        self.index = GraphIndex(graph)

    def retrieve(self, query: Query) -> RetrievalResult:
        started = time.perf_counter_ns()
        seeds, candidates = self.index.candidates(query.text)
        ranked_candidates = []
        for source_id, paths in candidates.items():
            exact_seeds = len({path["seed_id"] for path in paths if path["seed_match_class"] == 3})
            shortest = min(path["path_length"] for path in paths)
            path_count = len({(path["seed_id"], tuple(path["edge_ids"])) for path in paths})
            rank_key = (-exact_seeds, shortest, -path_count, source_id)
            ranked_candidates.append((rank_key, source_id, exact_seeds, shortest, path_count, paths))
        ranked_candidates.sort(key=lambda item: item[0])
        selected = tuple(
            RankedSource(
                source_id, float(exact_seeds), rank,
                {"rank_tuple": [exact_seeds, shortest, path_count, source_id], "paths": paths},
            )
            for rank, (_, source_id, exact_seeds, shortest, path_count, paths) in enumerate(ranked_candidates[:3], 1)
        )
        elapsed = (time.perf_counter_ns() - started) / 1_000_000
        return RetrievalResult(
            query.query_id, self.method, self.implementation_id, selected, not selected,
            elapsed, 0.0, "COMPLETE",
            {"top_k": 3, "max_path_length": 2, "edge_weight": "uniform", "edge_discovery": "undirected"},
            trace={"seeds": [seed.__dict__ for seed in seeds], "candidate_count": len(candidates)},
        )


class ProvenanceGraphRetriever:
    method = "Provenance-Aware Graph Retrieval"
    implementation_id = "provenance_graph_v1"

    def __init__(self, graph: dict[str, object], retrieval_texts: dict[str, str]) -> None:
        self.index = GraphIndex(graph)
        self.retrieval_texts = retrieval_texts
        self.bm25 = BM25Retriever(retrieval_texts)

    def _path_evidence(self, query_text: str, source_id: str, path: dict[str, Any]) -> list[dict[str, Any]]:
        content = self.retrieval_texts[source_id]
        evidence: list[dict[str, Any]] = []

        def add(kind: str, text: str, node_id: str | None = None) -> None:
            span = phrase_in_text(text, content)
            if span is not None:
                evidence.append({"kind": kind, "text": normalize_text(text), "span": list(span), "node_id": node_id})

        add("seed_alias", path["seed_label"], path["seed_id"])
        for node_id in path["node_ids"]:
            node = self.index.nodes[node_id]
            if node.get("type") == "Discovered_entity" and _match_alias(str(node.get("name", "")), query_text):
                add("named_entity", str(node["name"]), node_id)
        for edge in path["edges"]:
            trigger = edge.get("attributes", {}).get("original_trigger")
            if isinstance(trigger, str) and _match_alias(trigger, query_text):
                add("original_trigger", trigger)
        unique = {(item["kind"], item["text"]): item for item in evidence}
        return [unique[key] for key in sorted(unique)]

    def _collision_supported(self, query_text: str, source_id: str, path: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        collision_ids = [node_id for node_id in path["node_ids"] if node_id in self.index.collision_entities]
        if not collision_ids:
            return True, {"collision": False, "decision": "not_applicable"}
        content = self.retrieval_texts[source_id]
        content_tokens = set(lexical_tokens(content))
        query_tokens = set(lexical_tokens(query_text))
        for collision_id in collision_ids:
            entity = self.index.collision_entities[collision_id]
            name = str(entity["name"])
            if phrase_in_text(name, content) is None:
                return False, {"collision": True, "entity_id": collision_id, "decision": "excluded", "reason": "identity_name_not_in_source"}
            identity_tokens = set(lexical_tokens(name))
            literal_constraints = sorted((query_tokens - identity_tokens) & content_tokens)
            role_requested = bool({"employer", "role", "profession", "occupation"} & query_tokens)
            first_sentence = re.split(r"(?<=[.!?])\s+", normalize_text(content), maxsplit=1)[0]
            role_cues = sorted(PROFESSIONAL_CUES & set(all_tokens(first_sentence))) if role_requested else []
            if literal_constraints or (role_requested and role_cues and phrase_in_text(name, first_sentence)):
                return True, {
                    "collision": True, "entity_id": collision_id, "decision": "included",
                    "literal_constraint_tokens": literal_constraints,
                    "professional_cues": role_cues,
                }
            return False, {"collision": True, "entity_id": collision_id, "decision": "excluded", "reason": "unsupported_identity_collision"}
        return True, {"collision": False, "decision": "not_applicable"}

    def retrieve(self, query: Query) -> RetrievalResult:
        started = time.perf_counter_ns()
        seeds, candidates = self.index.candidates(query.text)
        eligible = []
        exclusions = []
        for source_id, paths in candidates.items():
            valid_paths = []
            all_evidence: dict[tuple[str, str], dict[str, Any]] = {}
            collision_decisions = []
            for path in paths:
                evidence = self._path_evidence(query.text, source_id, path)
                collision_ok, collision = self._collision_supported(query.text, source_id, path)
                collision_decisions.append(collision)
                if not collision_ok:
                    continue
                if evidence:
                    enriched = dict(path)
                    enriched["evidence"] = evidence
                    valid_paths.append(enriched)
                    for item in evidence:
                        all_evidence[(item["kind"], item["text"])] = item
            if not valid_paths:
                exclusions.append({"source_id": source_id, "reason": "no_valid_evidence_path", "collision_decisions": collision_decisions})
                continue
            direct_named = any(item["kind"] == "named_entity" for item in all_evidence.values())
            directly_supported_seed_ids = {
                path["seed_id"] for path in valid_paths
                if any(item["kind"] == "seed_alias" for item in path["evidence"])
            }
            generic_seed_ids = directly_supported_seed_ids & set(self.index.generic_concepts)
            non_generic_seed_ids = directly_supported_seed_ids - set(self.index.generic_concepts)
            if generic_seed_ids and not direct_named and not non_generic_seed_ids:
                exclusions.append({
                    "source_id": source_id, "reason": "generic_concept_only",
                    "generic_seed_ids": sorted(generic_seed_ids), "collision_decisions": collision_decisions,
                })
                continue
            shortest = min(path["path_length"] for path in valid_paths)
            bm25_score = self.bm25.score(query.text, source_id)
            evidence_count = len(all_evidence)
            rank_key = (not direct_named, -evidence_count, -len(non_generic_seed_ids), shortest, -bm25_score, source_id)
            eligible.append((
                rank_key, source_id, direct_named, evidence_count, non_generic_seed_ids,
                shortest, bm25_score, valid_paths, collision_decisions, generic_seed_ids,
            ))
        eligible.sort(key=lambda item: item[0])
        selected = tuple(
            RankedSource(
                source_id, float(evidence_count), rank,
                {
                    "rank_tuple": [direct_named, evidence_count, len(non_generic), shortest, bm25_score, source_id],
                    "paths": valid_paths,
                    "generic_concept_ids": sorted(generic_ids),
                    "generic_concept_decision": "accompanied" if generic_ids else "not_applicable",
                    "collision_decisions": collision_decisions,
                },
            )
            for rank, (_, source_id, direct_named, evidence_count, non_generic, shortest, bm25_score,
                       valid_paths, collision_decisions, generic_ids) in enumerate(eligible[:3], 1)
        )
        elapsed = (time.perf_counter_ns() - started) / 1_000_000
        return RetrievalResult(
            query.query_id, self.method, self.implementation_id, selected, not selected,
            elapsed, 0.0, "COMPLETE",
            {
                "top_k": 3, "max_path_length": 2, "generic_source_threshold": 10,
                "ranking": "preregistered_lexicographic_v1",
            },
            trace={
                "seeds": [seed.__dict__ for seed in seeds],
                "candidate_count": len(candidates),
                "eligible_count": len(eligible),
                "excluded_candidates": exclusions,
                "generic_concepts": self.index.generic_concepts,
                "collision_entities": self.index.collision_entities,
            },
        )
