"""Pipeline d'ingestion : extraction → découpage → embeddings → Qdrant.

L'ingestion est idempotente : chaque document est identifié par son nom (et son niveau),
et son contenu par une empreinte SHA-256. Ré-envoyer le même fichier ne crée aucun doublon ;
envoyer une nouvelle version remplace proprement l'ancienne.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import PurePath

from .chunking import chunk_sections
from .config import Settings
from .embeddings import Embedder
from .parsers import extract_sections
from .schemas import IngestResult
from .security import Level
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class EmptyDocumentError(ValueError):
    pass


def safe_filename(filename: str) -> str:
    # PurePath ne gère pas les "\" sous Linux : on normalise d'abord.
    name = PurePath(filename.replace("\\", "/")).name.strip()
    return name or "document"


def make_document_id(filename: str) -> str:
    return hashlib.sha1(safe_filename(filename).lower().encode("utf-8")).hexdigest()[:16]


class IngestionService:
    def __init__(self, store: VectorStore, embedder: Embedder, settings: Settings):
        self.store = store
        self.embedder = embedder
        self.settings = settings

    def ingest(self, filename: str, data: bytes, level: Level) -> IngestResult:
        filename = safe_filename(filename)
        document_id = make_document_id(filename)
        file_hash = hashlib.sha256(data).hexdigest()

        previous_hash = self.store.get_document_hash(level, document_id)
        if previous_hash == file_hash:
            chunks = self.store.count_document_chunks(level, document_id)
            logger.info("%s inchangé, ingestion ignorée.", filename)
            return IngestResult(
                document_id=document_id, document=filename, level=level, status="unchanged", chunks=chunks
            )

        sections = extract_sections(filename, data)
        chunks = chunk_sections(sections, self.settings.chunk_size, self.settings.chunk_overlap)
        if not chunks:
            raise EmptyDocumentError(
                f"Aucun texte exploitable dans '{filename}'. S'il s'agit d'un scan, "
                "il faut d'abord le passer dans un OCR."
            )

        vectors = self.embedder.embed_passages([c.text for c in chunks])
        self.store.replace_document(
            level=level,
            document_id=document_id,
            filename=filename,
            file_hash=file_hash,
            file_type=PurePath(filename).suffix.lower().lstrip("."),
            chunks=chunks,
            vectors=vectors,
            ingested_at=datetime.now(UTC),
        )
        status = "updated" if previous_hash else "ingested"
        logger.info("%s : %d chunks (%s) dans %s.", filename, len(chunks), status, level.value)
        return IngestResult(document_id=document_id, document=filename, level=level, status=status, chunks=len(chunks))
