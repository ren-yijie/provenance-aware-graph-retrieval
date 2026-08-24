"""Local MiniLM vector retrieval with versioned embedding cache."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import numpy as np

from .schema import Query, RankedSource, RetrievalResult


MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
THRESHOLD = 0.30


def l2_normalize(array: np.ndarray) -> np.ndarray:
    values = np.asarray(array, dtype=np.float32)
    if values.ndim == 1:
        values = values.reshape(1, -1)
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("zero vector cannot be normalized")
    return values / norms


def resolve_model_revision(model_id: str) -> str:
    try:
        from huggingface_hub import scan_cache_dir

        repos = [repo for repo in scan_cache_dir().repos if repo.repo_id == model_id and repo.repo_type == "model"]
        revisions = sorted(
            {revision.commit_hash for repo in repos for revision in repo.revisions if revision.commit_hash}
        )
        if revisions:
            return revisions[-1]
    except Exception:
        pass
    return "UNKNOWN"


def load_sentence_transformer(
    model_id: str = MODEL_ID, revision: str = MODEL_REVISION
) -> tuple[Any, str, str]:
    import sentence_transformers
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_id, revision=revision)
    resolved = resolve_model_revision(model_id)
    if resolved != "UNKNOWN" and resolved != revision:
        raise ValueError(f"resolved model revision {resolved} does not match pinned {revision}")
    return model, str(sentence_transformers.__version__), revision


class VectorRetriever:
    method = "Local Vector RAG"
    implementation_id = "minilm_vector_v1"

    def __init__(
        self,
        retrieval_texts: dict[str, str],
        model: Any,
        *,
        model_id: str = MODEL_ID,
        model_revision: str,
        sentence_transformers_version: str,
        dataset_fingerprint: str,
        cache_root: Path,
        threshold: float = THRESHOLD,
    ) -> None:
        self.model = model
        self.model_id = model_id
        self.model_revision = model_revision
        self.package_version = sentence_transformers_version
        self.dataset_fingerprint = dataset_fingerprint
        self.threshold = threshold
        self.source_ids = tuple(sorted(retrieval_texts))
        safe_model = re.sub(r"[^A-Za-z0-9._-]+", "_", model_id)
        safe_revision = re.sub(r"[^A-Za-z0-9._-]+", "_", model_revision)
        self.cache_identifier = Path(".cache/retrieval_embeddings/v1") / dataset_fingerprint / safe_model / safe_revision
        self.cache_dir = cache_root / "v1" / dataset_fingerprint / safe_model / safe_revision
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_hit = False
        expected = {
            "cache_version": 1,
            "dataset_fingerprint": dataset_fingerprint,
            "model_id": model_id,
            "model_revision": model_revision,
            "source_ids": list(self.source_ids),
            "l2_normalized": True,
            "dtype": "float32",
        }
        array_path = self.cache_dir / "source_embeddings.npy"
        metadata_path = self.cache_dir / "metadata.json"
        if array_path.exists() and metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            array = np.load(array_path, allow_pickle=False)
            if all(metadata.get(key) == value for key, value in expected.items()) and metadata.get("shape") == list(array.shape):
                self.source_embeddings = np.asarray(array, dtype=np.float32)
                if not np.allclose(np.linalg.norm(self.source_embeddings, axis=1), 1.0, atol=1e-5):
                    raise ValueError("cached embeddings are not L2-normalized")
                self.cache_hit = True
                return
        encoded = model.encode(
            [retrieval_texts[source_id] for source_id in self.source_ids],
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        self.source_embeddings = l2_normalize(np.asarray(encoded, dtype=np.float32))
        metadata = dict(expected)
        metadata["shape"] = list(self.source_embeddings.shape)
        np.save(array_path, self.source_embeddings, allow_pickle=False)
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    def retrieve(self, query: Query) -> RetrievalResult:
        started = time.perf_counter_ns()
        query_embedding = self.model.encode(
            [query.text], convert_to_numpy=True, show_progress_bar=False
        )
        normalized_query = l2_normalize(np.asarray(query_embedding, dtype=np.float32))[0]
        similarities = self.source_embeddings @ normalized_query
        ranked = sorted(
            zip(self.source_ids, similarities.tolist()),
            key=lambda item: (-item[1], item[0]),
        )
        abstained = not ranked or ranked[0][1] < self.threshold
        selected = () if abstained else tuple(
            RankedSource(source_id, float(score), rank, {"cosine_similarity": float(score)})
            for rank, (source_id, score) in enumerate(ranked[:3], 1)
        )
        elapsed = (time.perf_counter_ns() - started) / 1_000_000
        return RetrievalResult(
            query.query_id, self.method, self.implementation_id, selected, abstained,
            elapsed, 0.0, "COMPLETE",
            {
                "model_id": self.model_id,
                "model_revision": self.model_revision,
                "sentence_transformers_version": self.package_version,
                "threshold": self.threshold,
                "top_k": 3,
                "similarity": "cosine_on_explicitly_l2_normalized_float32",
                "source_embedding_cache": self.cache_identifier.as_posix(),
            },
            trace={"cache_hit": self.cache_hit},
        )
