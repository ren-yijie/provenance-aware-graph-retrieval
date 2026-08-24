from __future__ import annotations

import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from retrieval_benchmark.bm25 import BM25Retriever
from retrieval_benchmark.data import (
    CANONICAL_SHA256,
    RAW_SHA256,
    canonical_json_bytes,
    load_benchmark,
    load_retrieval_inputs,
)
from retrieval_benchmark.graph import GraphIndex, ProvenanceGraphRetriever, UnweightedGraphRetriever
from retrieval_benchmark.metrics import NOT_APPLICABLE, evaluate_query
from retrieval_benchmark.schema import Query, RankedSource, RetrievalResult
from retrieval_benchmark.text import build_retrieval_text, normalize_text
from retrieval_benchmark.vector import MODEL_REVISION, VectorRetriever, l2_normalize


ROOT = Path(__file__).resolve().parents[1]


class FakeEncoder:
    def __init__(self, mapping: dict[str, list[float]]) -> None:
        self.mapping = mapping
        self.calls = 0

    def encode(self, texts, **kwargs):
        self.calls += 1
        return np.asarray([self.mapping[text] for text in texts], dtype=np.float32)


class IntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_benchmark(ROOT)

    def test_frozen_fingerprints(self):
        import hashlib

        raw = (ROOT / "data/test_graph_slice.json").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), RAW_SHA256)
        self.assertEqual(hashlib.sha256(canonical_json_bytes(json.loads(raw))).hexdigest(), CANONICAL_SHA256)

    def test_all_gold_source_ids_exist(self):
        source_ids = set(self.data.sources)
        self.assertEqual(len(source_ids), 50)
        for gold in self.data.gold.values():
            self.assertLessEqual(gold, source_ids)

    def test_shared_retrieval_text_is_content_only(self):
        for source_id, node in self.data.sources.items():
            self.assertEqual(self.data.retrieval_texts[source_id], node["attributes"]["content"])
            self.assertNotIn(source_id, self.data.retrieval_texts[source_id])

    def test_no_evaluation_fields_leak_into_retrieval_text(self):
        forbidden = ["Expected_Source_IDs", "Gold_Evidence", "Gold_Answer_Summary", "NOT_RUN"]
        corpus = "\n".join(self.data.retrieval_texts.values())
        for value in forbidden:
            self.assertNotIn(value, corpus)

    def test_build_retrieval_text_rejects_non_source(self):
        with self.assertRaises(ValueError):
            build_retrieval_text({"id": "x", "type": "Concept", "attributes": {"content": "text"}})


class SchemaMetricTests(unittest.TestCase):
    def test_top_three_enforced(self):
        ranked = tuple(RankedSource(f"S{i}", 1.0, i, {}) for i in range(1, 5))
        with self.assertRaises(ValueError):
            RetrievalResult("Q", "M", "V", ranked, False, 1.0, 0.0, "COMPLETE", {})

    def test_answerable_metrics(self):
        metrics = evaluate_query(["A", "X"], {"A", "B"}, abstained=False, answerable=True)
        self.assertEqual((metrics.tp, metrics.fp, metrics.fn), (1, 1, 1))
        self.assertEqual((metrics.precision, metrics.recall, metrics.f1), (0.5, 0.5, 0.5))
        self.assertTrue(metrics.abstention_correct)

    def test_empty_gold_correct_abstention_is_not_applicable(self):
        metrics = evaluate_query([], set(), abstained=True, answerable=False)
        self.assertEqual((metrics.tp, metrics.fp, metrics.fn), (0, 0, 0))
        self.assertEqual(metrics.precision, NOT_APPLICABLE)
        self.assertEqual(metrics.recall, NOT_APPLICABLE)
        self.assertEqual(metrics.f1, NOT_APPLICABLE)
        self.assertTrue(metrics.abstention_correct)

    def test_empty_gold_incorrect_retrieval(self):
        metrics = evaluate_query(["A", "B"], set(), abstained=False, answerable=False)
        self.assertEqual((metrics.tp, metrics.fp, metrics.fn), (0, 2, 0))
        self.assertEqual(metrics.precision, 0.0)
        self.assertEqual(metrics.recall, NOT_APPLICABLE)
        self.assertFalse(metrics.abstention_correct)


class BM25Tests(unittest.TestCase):
    def test_deterministic_ranking_and_tie_break(self):
        texts = {"SRC_B": "alpha beta", "SRC_A": "alpha beta", "SRC_C": "gamma"}
        retriever = BM25Retriever(texts)
        first = retriever.retrieve(Query("Q", "alpha"))
        second = retriever.retrieve(Query("Q", "alpha"))
        self.assertEqual(
            [item.source_id for item in first.ranked_sources],
            [item.source_id for item in second.ranked_sources],
        )
        self.assertEqual([item.source_id for item in first.ranked_sources[:2]], ["SRC_A", "SRC_B"])

    def test_zero_score_abstains(self):
        result = BM25Retriever({"S": "alpha"}).retrieve(Query("Q", "omega"))
        self.assertTrue(result.abstained)


class VectorTests(unittest.TestCase):
    def test_model_revision_is_pinned_to_executed_snapshot(self):
        self.assertEqual(MODEL_REVISION, "1110a243fdf4706b3f48f1d95db1a4f5529b4d41")

    def test_normalization(self):
        values = l2_normalize(np.asarray([[3.0, 4.0], [5.0, 12.0]], dtype=np.float32))
        np.testing.assert_allclose(np.linalg.norm(values, axis=1), np.ones(2), atol=1e-6)

    def test_cache_and_threshold(self):
        mapping = {"doc a": [1, 0], "doc b": [0, 1], "query high": [1, 0], "query low": [-1, -1]}
        with tempfile.TemporaryDirectory() as directory:
            model = FakeEncoder(mapping)
            kwargs = dict(
                model_id="fake/model", model_revision="abc", sentence_transformers_version="test",
                dataset_fingerprint="fingerprint", cache_root=Path(directory), threshold=0.30,
            )
            first = VectorRetriever({"A": "doc a", "B": "doc b"}, model, **kwargs)
            self.assertFalse(first.cache_hit)
            self.assertEqual(
                first.cache_identifier.as_posix(),
                ".cache/retrieval_embeddings/v1/fingerprint/fake_model/abc",
            )
            self.assertFalse(first.retrieve(Query("Q1", "query high")).abstained)
            second_model = FakeEncoder(mapping)
            second = VectorRetriever({"A": "doc a", "B": "doc b"}, second_model, **kwargs)
            self.assertTrue(second.cache_hit)
            self.assertEqual(second_model.calls, 0)
            self.assertTrue(second.retrieve(Query("Q2", "query low")).abstained)


class GraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = load_retrieval_inputs(ROOT)
        cls.index = GraphIndex(cls.inputs.graph)

    def test_paths_never_exceed_two_edges_and_resolve_sources(self):
        for query in self.inputs.queries:
            seeds, candidates = self.index.candidates(query.text)
            for source_id, paths in candidates.items():
                self.assertIn(source_id, self.inputs.sources)
                for path in paths:
                    self.assertLessEqual(path["path_length"], 2)
                    self.assertEqual(path["node_ids"][-1], source_id)

    def test_deterministic_graph_ranking(self):
        retriever = UnweightedGraphRetriever(self.inputs.graph)
        query = self.inputs.queries[0]
        a = retriever.retrieve(query)
        b = retriever.retrieve(query)
        self.assertEqual([x.source_id for x in a.ranked_sources], [x.source_id for x in b.ranked_sources])

    def test_generic_concept_threshold(self):
        self.assertTrue(self.index.generic_concepts)
        for details in self.index.generic_concepts.values():
            self.assertGreaterEqual(details["source_count"], 10)

    def test_identity_collisions_derived(self):
        names = {normalize_text(str(item["name"])) for item in self.index.collision_entities.values()}
        self.assertTrue({"tariq al-rashid", "sophia andreou", "vikram nair", "andre beaumont"} <= names)

    def test_provenance_paths_and_filters(self):
        retriever = ProvenanceGraphRetriever(self.inputs.graph, self.inputs.retrieval_texts)
        for query in self.inputs.queries[:5]:
            result = retriever.retrieve(query)
            for ranked in result.ranked_sources:
                self.assertIn(ranked.source_id, self.inputs.sources)
                self.assertTrue(ranked.trace["paths"])
                for path in ranked.trace["paths"]:
                    self.assertTrue(path["evidence"])
                    self.assertLessEqual(path["path_length"], 2)

    def test_broken_graph_reference_rejected(self):
        graph = json.loads(json.dumps(self.inputs.graph))
        graph["edges"][0]["target"] = "MISSING"
        with self.assertRaises(ValueError):
            GraphIndex(graph)


class IsolationTests(unittest.TestCase):
    def test_direct_runner_launcher_imports_package(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_benchmark.py"), "--help"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_retrievers_have_no_gold_parameter_or_attribute(self):
        inputs = load_retrieval_inputs(ROOT)
        retrievers = [BM25Retriever(inputs.retrieval_texts), UnweightedGraphRetriever(inputs.graph), ProvenanceGraphRetriever(inputs.graph, inputs.retrieval_texts)]
        for retriever in retrievers:
            self.assertNotIn("gold", vars(retriever))
            self.assertNotIn("gold", inspect.signature(type(retriever).__init__).parameters)
        self.assertEqual(inputs.gold, {})
        self.assertEqual(inputs.question_rows, {})


if __name__ == "__main__":
    unittest.main()
