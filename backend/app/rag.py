"""Orchestration RAG : recherche des passages pertinents puis génération d'une réponse sourcée."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

from starlette.concurrency import run_in_threadpool

from .config import Settings
from .embeddings import Embedder
from .llm import ChatModel
from .schemas import ChatResponse, ChatTurn, Source
from .security import Level
from .vector_store import SearchHit, VectorStore

NO_ANSWER = (
    "Je ne trouve pas cette information dans les documents officiels. Je vous invite à contacter le secrétariat."
)

SYSTEM_PROMPT = """Tu es l'assistant administratif de {school}. Tu réponds en français, \
de façon courtoise, claire et concise.

Règles impératives :
1. Réponds UNIQUEMENT à partir des extraits de documents fournis ci-dessous.
2. Si les extraits ne permettent pas de répondre, dis exactement : "{no_answer}"
3. N'invente jamais de règle, de date, de montant ni de contact.
4. Cite tes sources avec leur numéro entre crochets, par exemple [1] ou [2][3].
5. Ne parle pas des « extraits » ou du « contexte » : réponds naturellement.

Extraits de documents :
{context}"""


def format_context(hits: list[SearchHit]) -> str:
    blocks = []
    for number, hit in enumerate(hits, start=1):
        page = hit.payload.get("page")
        location = f", page {page}" if page else ""
        blocks.append(f"[{number}] {hit.payload.get('source', 'Document')}{location}\n{hit.payload.get('text', '')}")
    return "\n\n".join(blocks)


def to_sources(hits: list[SearchHit], excerpt_chars: int = 300) -> list[Source]:
    sources = []
    for hit in hits:
        text = hit.payload.get("text", "")
        excerpt = text if len(text) <= excerpt_chars else text[:excerpt_chars].rsplit(" ", 1)[0] + "…"
        sources.append(
            Source(
                document=hit.payload.get("source", "Inconnu"),
                document_id=hit.payload.get("document_id", ""),
                level=hit.level,
                page=hit.payload.get("page"),
                score=round(hit.score, 4),
                excerpt=excerpt,
            )
        )
    return sources


class RAGService:
    def __init__(self, store: VectorStore, embedder: Embedder, llm: ChatModel, settings: Settings):
        self.store = store
        self.embedder = embedder
        self.llm = llm
        self.settings = settings

    def retrieve(self, question: str, levels: list[Level]) -> list[SearchHit]:
        vector = self.embedder.embed_query(question)
        return self.store.search(levels, vector, self.settings.top_k, self.settings.min_score)

    def build_messages(self, question: str, history: list[ChatTurn], hits: list[SearchHit]) -> list[dict]:
        system = SYSTEM_PROMPT.format(
            school=self.settings.school_name, no_answer=NO_ANSWER, context=format_context(hits)
        )
        messages = [{"role": "system", "content": system}]
        max_messages = self.settings.max_history_turns * 2
        recent = history[-max_messages:] if max_messages > 0 else []
        messages.extend({"role": turn.role, "content": turn.content} for turn in recent)
        messages.append({"role": "user", "content": question})
        return messages

    async def answer(self, question: str, history: list[ChatTurn], levels: list[Level]) -> ChatResponse:
        started = time.perf_counter()
        hits = await run_in_threadpool(self.retrieve, question, levels)
        if not hits:
            answer = NO_ANSWER  # inutile d'appeler le LLM : on évite toute hallucination.
        else:
            answer = await self.llm.complete(self.build_messages(question, history, hits))
        return ChatResponse(
            answer=answer,
            sources=to_sources(hits),
            levels_searched=levels,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    async def stream(self, question: str, history: list[ChatTurn], levels: list[Level]) -> AsyncIterator[dict]:
        """Événements : `sources`, puis une série de `token`, puis `done` (ou `error`)."""
        started = time.perf_counter()
        hits = await run_in_threadpool(self.retrieve, question, levels)
        yield {"type": "sources", "sources": [s.model_dump(mode="json") for s in to_sources(hits)]}
        if not hits:
            yield {"type": "token", "content": NO_ANSWER}
        else:
            async for token in self.llm.stream(self.build_messages(question, history, hits)):
                yield {"type": "token", "content": token}
        yield {"type": "done", "latency_ms": int((time.perf_counter() - started) * 1000)}
