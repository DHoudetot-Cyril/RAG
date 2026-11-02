from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .security import Level, Role


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list)
    levels: list[Level] | None = Field(
        default=None,
        description="Restreint la recherche à certains niveaux (par défaut : tous ceux autorisés pour le rôle).",
    )


class Source(BaseModel):
    document: str
    document_id: str
    level: Level
    page: int | None = None
    score: float
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    levels_searched: list[Level]
    latency_ms: int


class DocumentInfo(BaseModel):
    document_id: str
    document: str
    level: Level
    chunks: int
    file_hash: str
    file_type: str
    ingested_at: datetime | None = None


class IngestResult(BaseModel):
    document_id: str
    document: str
    level: Level
    status: Literal["ingested", "updated", "unchanged"]
    chunks: int


class DeleteResult(BaseModel):
    document_id: str
    level: Level
    deleted: bool


class WhoAmI(BaseModel):
    role: Role
    levels: list[Level]


class HealthStatus(BaseModel):
    status: Literal["ok", "degraded"]
    qdrant: bool
    llm: bool
    embedding_model: str
    llm_model: str
