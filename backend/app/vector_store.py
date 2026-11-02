"""Accès à Qdrant : une collection par niveau d'accès, ce qui garantit l'isolation des données.

Un élève n'interroge physiquement jamais la collection du niveau 2 : la séparation ne
repose pas sur un simple filtre qu'un bug pourrait contourner.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.http import models

from .chunking import Chunk
from .security import Level

logger = logging.getLogger(__name__)

_NAMESPACE = uuid.UUID("3f1c6a8e-2b7d-4c1a-9e55-6a2f0d1b7c42")


@dataclass(frozen=True)
class SearchHit:
    level: Level
    score: float
    payload: dict


class VectorStore:
    def __init__(self, client: QdrantClient, collections: dict[Level, str]):
        self.client = client
        self.collections = collections

    # ------------------------------------------------------------------ setup
    def ensure_collections(self, dimension: int) -> None:
        for level, name in self.collections.items():
            if self.client.collection_exists(name):
                info = self.client.get_collection(name)
                existing = info.config.params.vectors.size  # type: ignore[union-attr]
                if existing != dimension:
                    raise RuntimeError(
                        f"La collection '{name}' a des vecteurs de dimension {existing}, "
                        f"mais le modèle d'embedding produit {dimension}. "
                        "Supprimez la collection ou changez de modèle."
                    )
                continue
            self.client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE),
            )
            for field in ("document_id", "file_hash"):
                self.client.create_payload_index(name, field, models.PayloadSchemaType.KEYWORD)
            logger.info("Collection %s (%s) créée.", name, level.value)

    def ping(self) -> bool:
        try:
            self.client.get_collections()
            return True
        except Exception:  # noqa: BLE001
            return False

    # -------------------------------------------------------------- documents
    @staticmethod
    def _document_filter(document_id: str) -> models.Filter:
        return models.Filter(
            must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
        )

    def get_document_hash(self, level: Level, document_id: str) -> str | None:
        points, _ = self.client.scroll(
            collection_name=self.collections[level],
            scroll_filter=self._document_filter(document_id),
            limit=1,
            with_payload=["file_hash"],
            with_vectors=False,
        )
        return points[0].payload.get("file_hash") if points else None

    def count_document_chunks(self, level: Level, document_id: str) -> int:
        result = self.client.count(
            collection_name=self.collections[level],
            count_filter=self._document_filter(document_id),
            exact=True,
        )
        return result.count

    def replace_document(
        self,
        *,
        level: Level,
        document_id: str,
        filename: str,
        file_hash: str,
        file_type: str,
        chunks: list[Chunk],
        vectors: list[list[float]],
        ingested_at: datetime,
        batch_size: int = 128,
    ) -> None:
        """Supprime l'ancienne version du document puis insère les nouveaux chunks."""
        collection = self.collections[level]
        self.delete_document(level, document_id)
        points = [
            models.PointStruct(
                id=str(uuid.uuid5(_NAMESPACE, f"{level.value}:{document_id}:{chunk.index}")),
                vector=vector,
                payload={
                    "document_id": document_id,
                    "source": filename,
                    "file_hash": file_hash,
                    "file_type": file_type,
                    "level": level.value,
                    "page": chunk.page,
                    "chunk_index": chunk.index,
                    "text": chunk.text,
                    "ingested_at": ingested_at.isoformat(),
                },
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        for start in range(0, len(points), batch_size):
            self.client.upsert(collection_name=collection, points=points[start : start + batch_size], wait=True)

    def delete_document(self, level: Level, document_id: str) -> bool:
        if self.count_document_chunks(level, document_id) == 0:
            return False
        self.client.delete(
            collection_name=self.collections[level],
            points_selector=models.FilterSelector(filter=self._document_filter(document_id)),
            wait=True,
        )
        return True

    def list_documents(self, level: Level) -> list[dict]:
        documents: dict[str, dict] = {}
        offset = None
        while True:
            points, offset = self.client.scroll(
                collection_name=self.collections[level],
                limit=256,
                offset=offset,
                with_payload=["document_id", "source", "file_hash", "file_type", "ingested_at"],
                with_vectors=False,
            )
            for point in points:
                payload = point.payload or {}
                doc_id = payload.get("document_id", "inconnu")
                entry = documents.setdefault(
                    doc_id,
                    {
                        "document_id": doc_id,
                        "document": payload.get("source", "Inconnu"),
                        "level": level,
                        "chunks": 0,
                        "file_hash": payload.get("file_hash", ""),
                        "file_type": payload.get("file_type", ""),
                        "ingested_at": payload.get("ingested_at"),
                    },
                )
                entry["chunks"] += 1
            if offset is None:
                break
        return sorted(documents.values(), key=lambda d: d["document"].lower())

    # ----------------------------------------------------------------- search
    def search(self, levels: list[Level], vector: list[float], top_k: int, min_score: float) -> list[SearchHit]:
        hits: list[SearchHit] = []
        for level in levels:
            response = self.client.query_points(
                collection_name=self.collections[level],
                query=vector,
                limit=top_k,
                score_threshold=min_score,
                with_payload=True,
            )
            hits.extend(SearchHit(level=level, score=p.score, payload=p.payload or {}) for p in response.points)
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]
