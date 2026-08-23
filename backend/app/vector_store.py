from __future__ import annotations

from collections import Counter
from hashlib import sha256
from math import sqrt
from typing import Any
import re

from backend.app.config import settings


TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]+")


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text or "")]


def vectorize(text: str) -> Counter[str]:
    return Counter(tokenize(text))


def cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    overlap = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in overlap)
    left_norm = sqrt(sum(value * value for value in left.values()))
    right_norm = sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


class LocalVectorStore:
    """Small dependency-free vector index for the assessment.

    This is not Pinecone. It is a local lexical vector store using bag-of-words
    vectors and cosine similarity, combined with source authority in the tool
    layer. Production can swap this interface for pgvector, Pinecone, Qdrant,
    Weaviate, or OpenSearch without changing the agent contract.
    """

    provider_name = "local"

    def search(self, documents: list[dict[str, Any]], query: str, limit: int = 5) -> list[tuple[dict[str, Any], float]]:
        query_vector = vectorize(query)
        scored: list[tuple[dict[str, Any], float]] = []
        for document in documents:
            text = f"{document.get('name', '')} {document.get('text', '')}"
            score = cosine_similarity(query_vector, vectorize(text))
            if score > 0:
                scored.append((document, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:limit]


class PineconeVectorStore:
    """Production Pinecone adapter.

    Documents are still hydrated from the assessment data snapshot, but search
    is performed against Pinecone using OpenAI embeddings. In a larger
    deployment, move `ensure_indexed` into an async ingestion worker.
    """

    provider_name = "pinecone"
    chunk_size = 3000
    chunk_overlap = 300

    def __init__(self) -> None:
        if not settings.pinecone_api_key or not settings.pinecone_index:
            raise RuntimeError("PINECONE_API_KEY and PINECONE_INDEX are required for Pinecone retrieval.")
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required to embed Pinecone queries and documents.")
        try:
            from pinecone import Pinecone  # type: ignore
        except Exception as exc:
            raise RuntimeError("Install the pinecone package to use RETRIEVAL_PROVIDER=pinecone.") from exc
        try:
            from openai import OpenAI  # type: ignore
        except Exception as exc:
            raise RuntimeError("Install the openai package to use Pinecone retrieval.") from exc
        self.client = Pinecone(api_key=settings.pinecone_api_key)
        self.index = self.client.Index(settings.pinecone_index)
        self.openai = OpenAI(api_key=settings.openai_api_key)
        self._indexed_fingerprints: set[str] = set()

    def search(self, documents: list[dict[str, Any]], query: str, limit: int = 5) -> list[tuple[dict[str, Any], float]]:
        self.ensure_indexed(documents)
        query_vector = self._embed(query)
        response = self.index.query(
            vector=query_vector,
            top_k=limit,
            namespace=settings.pinecone_namespace,
            include_metadata=True,
        )
        matches = response.get("matches", []) if isinstance(response, dict) else getattr(response, "matches", [])
        results: list[tuple[dict[str, Any], float]] = []
        for match in matches:
            metadata = match.get("metadata", {}) if isinstance(match, dict) else getattr(match, "metadata", {}) or {}
            score = float(match.get("score", 0.0) if isinstance(match, dict) else getattr(match, "score", 0.0))
            results.append((self._doc_from_metadata(metadata), score))
        return results

    def ensure_indexed(self, documents: list[dict[str, Any]]) -> None:
        vectors = []
        for doc in documents:
            for chunk_index, text in enumerate(self._chunks(str(doc.get("text") or ""))):
                fingerprint = self._fingerprint(doc, chunk_index, text)
                if fingerprint in self._indexed_fingerprints:
                    continue
                vectors.append(
                    {
                        "id": fingerprint,
                        "values": self._embed(f"{doc.get('name', '')}\n{text}"),
                        "metadata": self._metadata(doc, chunk_index, text),
                    }
                )
                self._indexed_fingerprints.add(fingerprint)
        if vectors:
            self.index.upsert(vectors=vectors, namespace=settings.pinecone_namespace)

    def _embed(self, text: str) -> list[float]:
        kwargs: dict[str, Any] = {"model": settings.openai_embedding_model, "input": text[:8000]}
        if settings.openai_embedding_dimensions:
            kwargs["dimensions"] = settings.openai_embedding_dimensions
        response = self.openai.embeddings.create(**kwargs)
        return list(response.data[0].embedding)

    def _chunks(self, text: str) -> list[str]:
        normalized = " ".join(text.split())
        if not normalized:
            return [""]
        chunks = []
        start = 0
        while start < len(normalized):
            chunks.append(normalized[start : start + self.chunk_size])
            start += self.chunk_size - self.chunk_overlap
        return chunks

    def _fingerprint(self, doc: dict[str, Any], chunk_index: int, text: str) -> str:
        raw = f"{doc.get('id') or doc.get('name')}:{chunk_index}:{text}"
        return sha256(raw.encode("utf-8")).hexdigest()

    def _metadata(self, doc: dict[str, Any], chunk_index: int, text: str) -> dict[str, Any]:
        return {
            "id": str(doc.get("id") or ""),
            "name": str(doc.get("name") or ""),
            "source_type": str(doc.get("source_type") or ""),
            "authority": str(doc.get("authority") or ""),
            "status": str(doc.get("status") or ""),
            "account_id": str(doc.get("account_id") or ""),
            "page": int(doc.get("page") or 1),
            "chunk_index": chunk_index,
            "text": text,
        }

    def _doc_from_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        account_id = metadata.get("account_id") or None
        return {
            "id": metadata.get("id"),
            "name": metadata.get("name"),
            "source_type": metadata.get("source_type"),
            "authority": metadata.get("authority"),
            "status": metadata.get("status"),
            "account_id": account_id,
            "page": metadata.get("page"),
            "text": metadata.get("text") or "",
        }


def create_vector_store():
    if settings.retrieval_provider == "pinecone":
        return PineconeVectorStore()
    if settings.is_production:
        raise RuntimeError("Production must use RETRIEVAL_PROVIDER=pinecone.")
    return LocalVectorStore()
