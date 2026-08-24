"""Frozen text construction and normalization rules."""

from __future__ import annotations

import re
import unicodedata


STOP_WORDS = frozenset(
    "a about above after again against all am an and any are as at be because been before "
    "being below between both but by can did do does doing down during each few for from further "
    "had has have having he her here hers herself him himself his how i if in into is it its itself "
    "just me more most my myself no nor not now of off on once only or other our ours ourselves out "
    "over own same she should so some such than that the their theirs them themselves then there "
    "these they this those through to too under until up very was we were what when where which while "
    "who whom why will with you your yours yourself yourselves".split()
)
TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", unicodedata.normalize("NFKC", value).lower()).strip()


def all_tokens(value: str) -> list[str]:
    return TOKEN_RE.findall(normalize_text(value))


def lexical_tokens(value: str) -> list[str]:
    return [token for token in all_tokens(value) if token not in STOP_WORDS]


def phrase_in_text(phrase: str, text: str) -> tuple[int, int] | None:
    """Return normalized character offsets for a token-bounded phrase."""
    needle = normalize_text(phrase)
    haystack = normalize_text(text)
    if not needle:
        return None
    pattern = re.compile(r"(?<![^\W_])" + re.escape(needle) + r"(?![^\W_])", re.UNICODE)
    match = pattern.search(haystack)
    return match.span() if match else None


def build_retrieval_text(source_node: dict[str, object]) -> str:
    """Use only the pre-evaluation evidence-bearing Source content field."""
    if source_node.get("type") != "Source":
        raise ValueError("retrieval text can only be built from Source nodes")
    attributes = source_node.get("attributes")
    if not isinstance(attributes, dict):
        raise ValueError("Source attributes must be an object")
    content = attributes.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError(f"Source {source_node.get('id')} has no profile content")
    return content
