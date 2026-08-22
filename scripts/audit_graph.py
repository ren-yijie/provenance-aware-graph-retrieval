#!/usr/bin/env python3
"""Audit the frozen graph slice without third-party dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict, deque
from pathlib import Path


EXPECTED_SHA256 = "bd6c8802a864b4599c064d34c01a5d8b460cb4f040bd8339f745bef8dcf61ad5"


def weak_components(node_ids: set[str], edges: list[dict[str, object]]) -> list[int]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        source = str(edge["source"])
        target = str(edge["target"])
        adjacency[source].add(target)
        adjacency[target].add(source)

    remaining = set(node_ids)
    sizes: list[int] = []
    while remaining:
        start = remaining.pop()
        queue: deque[str] = deque([start])
        size = 0
        while queue:
            current = queue.popleft()
            size += 1
            for neighbor in adjacency[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def audit(path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    graph = json.loads(payload)
    nodes = graph["nodes"]
    edges = graph["edges"]

    node_ids = [str(node["id"]) for node in nodes]
    edge_ids = [str(edge["id"]) for edge in edges]
    node_id_set = set(node_ids)
    endpoint_ids = {
        str(endpoint)
        for edge in edges
        for endpoint in (edge["source"], edge["target"])
    }
    triples = [(str(e["source"]), str(e["target"]), str(e["type"])) for e in edges]

    concept_edges = [edge for edge in edges if edge["type"] == "IS_CONCEPT"]
    concept_targets = Counter(str(edge["target"]) for edge in concept_edges)
    node_names = {str(node["id"]): str(node.get("name", node["id"])) for node in nodes}
    dominant_target, dominant_count = concept_targets.most_common(1)[0]

    embedding_dimensions = Counter(
        len(node.get("attributes", {}).get("embedding", []))
        for node in nodes
        if "embedding" in node.get("attributes", {})
    )
    components = weak_components(node_id_set, edges)

    return {
        "file": path.name,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "sha256_matches_frozen_record": hashlib.sha256(payload).hexdigest() == EXPECTED_SHA256,
        "directed": graph.get("directed"),
        "multigraph": graph.get("multigraph"),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_types": dict(sorted(Counter(str(n["type"]) for n in nodes).items())),
        "edge_types": dict(sorted(Counter(str(e["type"]) for e in edges).items())),
        "duplicate_node_ids": len(node_ids) - len(node_id_set),
        "duplicate_edge_ids": len(edge_ids) - len(set(edge_ids)),
        "dangling_endpoint_ids": sorted(endpoint_ids - node_id_set),
        "self_loops": sum(e["source"] == e["target"] for e in edges),
        "duplicate_edge_triples": len(triples) - len(set(triples)),
        "isolated_nodes": len(node_id_set - endpoint_ids),
        "weak_component_count": len(components),
        "largest_weak_component": components[0] if components else 0,
        "concept_embedding_dimensions": dict(sorted(embedding_dimensions.items())),
        "dominant_concept": {
            "id": dominant_target,
            "name": node_names[dominant_target],
            "is_concept_edges": dominant_count,
            "share": dominant_count / len(concept_edges),
        },
        "edges_with_confidence": sum("confidence" in e.get("attributes", {}) for e in edges),
    }


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "graph",
        nargs="?",
        type=Path,
        default=repo_root / "data/test_graph_slice.json",
    )
    args = parser.parse_args()
    print(json.dumps(audit(args.graph), indent=2))


if __name__ == "__main__":
    main()
