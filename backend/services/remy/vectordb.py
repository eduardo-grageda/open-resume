from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from datetime import datetime
from typing import Optional

from backend.config import DATA_DIR, load_config
from backend.models import BaseCV, RemyListing

logger = logging.getLogger(__name__)

VECTORS_DIR = DATA_DIR / "remy" / "vectors"
VECTORS_PATH = VECTORS_DIR / "vectors.json"
LOCAL_EMBED_DIM = 512
CV_VECTOR_ID = "cv:latest"

_TOKEN_RE = re.compile(r"[a-z0-9#+.]+")


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _tokens(text: str) -> list[str]:
    words = _TOKEN_RE.findall(text.lower())
    tokens = [w for w in words if len(w) >= 2]
    tokens += [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
    return tokens


def _l2_norm(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def local_embed(text: str) -> list[float]:
    """Deterministic, dependency-free feature-hashing embedder.

    Used when no embedding provider is configured (REMY_EMBEDDING_MODEL
    empty). Unigram+bigram tokens are hashed into a fixed-size vector with
    sign tricks; cosine similarity still correlates with keyword overlap.
    """
    counts: dict[str, int] = {}
    for token in _tokens(text):
        counts[token] = counts.get(token, 0) + 1

    vector = [0.0] * LOCAL_EMBED_DIM
    for token, count in counts.items():
        digest = hashlib.md5(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:8], "little") % LOCAL_EMBED_DIM
        sign = 1.0 if digest[8] % 2 == 0 else -1.0
        vector[bucket] += sign * (1.0 + math.log(count))
    return _l2_norm(vector)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class Embedder:
    """Embeds text via the configured LLM provider or the local embedder."""

    def __init__(self) -> None:
        self._config = load_config()

    @property
    def uses_provider(self) -> bool:
        return bool(self._config.remy_embedding_model and self._config.openrouter_api_key)

    async def embed(self, text: str) -> list[float]:
        if self.uses_provider:
            try:
                from backend.services.llm import LLMClient

                llm = LLMClient(self._config)
                vectors = await llm.embed([text], model=self._config.remy_embedding_model)
                if vectors and vectors[0]:
                    return _l2_norm(vectors[0])
                logger.warning("Embedding provider returned empty vector; falling back to local embedder")
            except Exception as e:
                logger.warning("Provider embedding failed (%s); falling back to local embedder", e)
        return local_embed(text)


class VectorStore:
    """JSON-file-backed vector store (swap-in point for ChromaDB later).

    Entries: {id, kind (listing|cv), ref_id, vector, meta, updated_at}.
    """

    def __init__(self) -> None:
        VECTORS_DIR.mkdir(parents=True, exist_ok=True)

    def _read(self) -> dict[str, dict]:
        if not VECTORS_PATH.exists():
            return {}
        with open(VECTORS_PATH) as f:
            return json.load(f)

    def _write(self, entries: dict[str, dict]) -> None:
        with open(VECTORS_PATH, "w") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)

    async def get(self, vector_id: str) -> Optional[dict]:
        return self._read().get(vector_id)

    async def upsert(
        self,
        vector_id: str,
        kind: str,
        ref_id: str,
        vector: list[float],
        meta: Optional[dict] = None,
    ) -> None:
        entries = self._read()
        entries[vector_id] = {
            "id": vector_id,
            "kind": kind,
            "ref_id": ref_id,
            "vector": vector,
            "meta": meta or {},
            "updated_at": _now(),
        }
        self._write(entries)

    async def delete(self, vector_id: str) -> bool:
        entries = self._read()
        if vector_id not in entries:
            return False
        del entries[vector_id]
        self._write(entries)
        return True

    async def search(
        self,
        vector: list[float],
        top_k: int = 10,
        kind: Optional[str] = None,
    ) -> list[tuple[str, float]]:
        scored: list[tuple[str, float]] = []
        for vector_id, entry in self._read().items():
            if kind and entry.get("kind") != kind:
                continue
            scored.append((vector_id, cosine_similarity(vector, entry.get("vector", []))))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


def listing_text(listing: RemyListing) -> str:
    parts = [listing.title, listing.company, listing.location]
    if listing.description_md:
        parts.append(listing.description_md[:4000])
    return " ".join(p for p in parts if p)


def cv_text(cv: BaseCV) -> str:
    from backend.services.adapter import AdapterService

    return AdapterService._format_cv(cv)


def listing_vector_id(listing: RemyListing) -> str:
    return f"listing:{listing.id}"


async def ensure_listing_embedded(listing: RemyListing, embedder: Optional[Embedder] = None) -> str:
    """Embed a listing if not already in the vector store; returns vector id."""
    store = VectorStore()
    if listing.embedding_id and await store.get(listing.embedding_id) is not None:
        return listing.embedding_id
    embedder = embedder or Embedder()
    vector = await embedder.embed(listing_text(listing))
    vector_id = listing_vector_id(listing)
    await store.upsert(
        vector_id,
        "listing",
        listing.id,
        vector,
        {"title": listing.title, "company": listing.company},
    )
    return vector_id


async def get_cv_vector(cv: BaseCV, embedder: Optional[Embedder] = None) -> list[float]:
    """Embed the CV once per `updated_at`; re-embeds when the CV changes."""
    store = VectorStore()
    entry = await store.get(CV_VECTOR_ID)
    if entry is not None and entry.get("ref_id") == cv.updated_at:
        return entry["vector"]
    embedder = embedder or Embedder()
    vector = await embedder.embed(cv_text(cv))
    await store.upsert(CV_VECTOR_ID, "cv", cv.updated_at, vector)
    return vector
