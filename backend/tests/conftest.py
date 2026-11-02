"""Fixtures de test : Qdrant en mémoire, embedder et LLM factices.

Aucun GPU, aucun téléchargement de modèle ni serveur externe n'est nécessaire :
la suite complète tourne en quelques secondes, y compris dans la CI GitHub Actions.
"""

from __future__ import annotations

import hashlib
import math
import re

import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from app.config import Settings
from app.main import create_app

KEYS = {"student": "key-student", "direction": "key-direction", "admin": "key-admin"}
_WORD = re.compile(r"\w+", re.UNICODE)


class FakeEmbedder:
    """Sac de mots haché : deux textes partageant des mots ont un cosinus élevé."""

    dimension = 256

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for word in _WORD.findall(text.lower()):
            if len(word) < 3:
                continue
            index = int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dimension
            vector[index] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]


class FakeLLM:
    def __init__(self) -> None:
        self.calls: list[list[dict]] = []

    async def complete(self, messages: list[dict]) -> str:
        self.calls.append(messages)
        return "Réponse factice fondée sur les documents [1]."

    async def stream(self, messages: list[dict]):
        self.calls.append(messages)
        for token in ["Réponse ", "factice ", "[1]."]:
            yield token

    async def ping(self) -> bool:
        return True


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        student_api_key=KEYS["student"],
        direction_api_key=KEYS["direction"],
        admin_api_key=KEYS["admin"],
        min_score=0.2,
        top_k=3,
        chunk_size=300,
        chunk_overlap=50,
        max_upload_mb=1,
    )


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def client(settings: Settings, fake_llm: FakeLLM):
    app = create_app(
        settings,
        embedder=FakeEmbedder(),
        llm=fake_llm,
        qdrant_client=QdrantClient(location=":memory:"),
    )
    with TestClient(app) as test_client:
        yield test_client


def auth(role: str) -> dict[str, str]:
    return {"X-API-Key": KEYS[role]}
