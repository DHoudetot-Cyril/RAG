"""API FastAPI de RAG École.

Documentation interactive : http://localhost:8080/docs
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from qdrant_client import QdrantClient
from starlette.concurrency import run_in_threadpool

from . import __version__
from .config import Settings, get_settings
from .embeddings import E5Embedder, Embedder
from .ingestion import EmptyDocumentError, IngestionService
from .llm import ChatModel, LLMError, OpenAICompatibleLLM
from .parsers import UnsupportedFormatError
from .rag import RAGService, to_sources
from .schemas import (
    ChatRequest,
    ChatResponse,
    DeleteResult,
    DocumentInfo,
    HealthStatus,
    IngestResult,
    Source,
    WhoAmI,
)
from .security import Level, Role, allowed_levels, get_current_role, require_admin
from .vector_store import VectorStore

logger = logging.getLogger("rag")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@dataclass
class Services:
    settings: Settings
    store: VectorStore
    embedder: Embedder
    llm: ChatModel
    rag: RAGService
    ingestion: IngestionService


def _connect_qdrant(url: str, attempts: int = 10, delay: float = 3.0) -> QdrantClient:
    """Qdrant peut démarrer après l'API dans docker compose : on patiente un peu."""
    for attempt in range(1, attempts + 1):
        client = QdrantClient(url=url)
        try:
            client.get_collections()
            return client
        except Exception as exc:  # noqa: BLE001
            logger.warning("Qdrant indisponible (%s), tentative %d/%d...", exc, attempt, attempts)
            time.sleep(delay)
    raise RuntimeError(f"Impossible de joindre Qdrant sur {url}")


def create_app(
    settings: Settings | None = None,
    *,
    embedder: Embedder | None = None,
    llm: ChatModel | None = None,
    qdrant_client: QdrantClient | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = qdrant_client or _connect_qdrant(settings.qdrant_url)
        emb = embedder or E5Embedder(settings.embedding_model_name, settings.embedding_device)
        model = llm or OpenAICompatibleLLM(
            base_url=settings.llm_base_url,
            model=settings.llm_model_name,
            api_key=settings.llm_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout_seconds,
        )
        store = VectorStore(
            client, {Level.LEVEL1: settings.collection_level1, Level.LEVEL2: settings.collection_level2}
        )
        # Récupérer la dimension charge le modèle : le premier appel utilisateur sera rapide.
        store.ensure_collections(emb.dimension)
        app.state.services = Services(
            settings=settings,
            store=store,
            embedder=emb,
            llm=model,
            rag=RAGService(store, emb, model, settings),
            ingestion=IngestionService(store, emb, settings),
        )
        logger.info("API prête.")
        yield
        if hasattr(model, "aclose"):
            await model.aclose()

    app = FastAPI(
        title="RAG École API",
        version=__version__,
        description="Assistant documentaire à niveaux d'accès (élèves / direction) basé sur le RAG.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def services(request: Request) -> Services:
        return request.app.state.services

    # ---------------------------------------------------------------- système
    @app.get("/health", response_model=HealthStatus, tags=["Système"])
    async def health(svc: Services = Depends(services)) -> HealthStatus:
        qdrant_ok = await run_in_threadpool(svc.store.ping)
        llm_ok = await svc.llm.ping()
        return HealthStatus(
            status="ok" if qdrant_ok and llm_ok else "degraded",
            qdrant=qdrant_ok,
            llm=llm_ok,
            embedding_model=svc.settings.embedding_model_name,
            llm_model=svc.settings.llm_model_name,
        )

    @app.get("/me", response_model=WhoAmI, tags=["Système"])
    async def whoami(role: Role = Depends(get_current_role)) -> WhoAmI:
        return WhoAmI(role=role, levels=allowed_levels(role))

    # ------------------------------------------------------------------- chat
    @app.post("/chat", response_model=ChatResponse, tags=["Chat"])
    async def chat(
        body: ChatRequest, role: Role = Depends(get_current_role), svc: Services = Depends(services)
    ) -> ChatResponse:
        levels = allowed_levels(role, body.levels)
        try:
            return await svc.rag.answer(body.question, body.history, levels)
        except LLMError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    @app.post("/search", response_model=list[Source], tags=["Chat"])
    async def search(
        body: ChatRequest, role: Role = Depends(get_current_role), svc: Services = Depends(services)
    ) -> list[Source]:
        """Recherche sémantique seule (sans génération) : utile pour le débogage et l'évaluation."""
        levels = allowed_levels(role, body.levels)
        hits = await run_in_threadpool(svc.rag.retrieve, body.question, levels)
        return to_sources(hits)

    @app.post(
        "/chat/stream",
        tags=["Chat"],
        response_class=StreamingResponse,
        responses={200: {"content": {"application/x-ndjson": {}}}},
    )
    async def chat_stream(
        body: ChatRequest, role: Role = Depends(get_current_role), svc: Services = Depends(services)
    ) -> StreamingResponse:
        """Réponse en streaming, au format NDJSON (un objet JSON par ligne)."""
        levels = allowed_levels(role, body.levels)

        async def events():
            try:
                async for event in svc.rag.stream(body.question, body.history, levels):
                    yield json.dumps(event, ensure_ascii=False) + "\n"
            except LLMError as exc:
                yield json.dumps({"type": "error", "detail": str(exc)}, ensure_ascii=False) + "\n"

        return StreamingResponse(events(), media_type="application/x-ndjson")

    # -------------------------------------------------------------- documents
    @app.get("/documents", response_model=list[DocumentInfo], tags=["Documents"])
    async def list_documents(
        level: Level | None = Query(default=None),
        role: Role = Depends(get_current_role),
        svc: Services = Depends(services),
    ) -> list[DocumentInfo]:
        levels = allowed_levels(role, [level] if level else None)
        documents: list[DocumentInfo] = []
        for lvl in levels:
            rows = await run_in_threadpool(svc.store.list_documents, lvl)
            documents.extend(DocumentInfo(**row) for row in rows)
        return documents

    @app.post(
        "/documents",
        response_model=IngestResult,
        status_code=status.HTTP_201_CREATED,
        tags=["Documents"],
        dependencies=[Depends(require_admin)],
    )
    async def ingest_document(
        file: UploadFile = File(...),
        level: Level = Form(...),
        svc: Services = Depends(services),
    ) -> IngestResult:
        max_bytes = svc.settings.max_upload_mb * 1024 * 1024
        data = await file.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Fichier trop volumineux (max {svc.settings.max_upload_mb} Mo).",
            )
        try:
            return await run_in_threadpool(svc.ingestion.ingest, file.filename or "document", data, level)
        except UnsupportedFormatError as exc:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc
        except EmptyDocumentError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    @app.delete(
        "/documents/{level}/{document_id}",
        response_model=DeleteResult,
        tags=["Documents"],
        dependencies=[Depends(require_admin)],
    )
    async def delete_document(level: Level, document_id: str, svc: Services = Depends(services)) -> DeleteResult:
        deleted = await run_in_threadpool(svc.store.delete_document, level, document_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")
        return DeleteResult(document_id=document_id, level=level, deleted=True)

    return app


app = create_app()
