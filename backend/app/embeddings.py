"""Modèles d'embedding.

Les modèles de la famille E5 doivent recevoir un préfixe différent selon qu'on encode
une question (`query: `) ou un passage de document (`passage: `). Oublier l'un des deux
dégrade nettement la qualité de recherche : c'est encapsulé ici pour ne jamais se tromper.
"""

from __future__ import annotations

import logging
import threading
from typing import Protocol

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    @property
    def dimension(self) -> int: ...

    def embed_query(self, text: str) -> list[float]: ...

    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...


class E5Embedder:
    """Wrapper SentenceTransformers chargé paresseusement (le modèle pèse ~2 Go)."""

    def __init__(self, model_name: str, device: str | None = None, batch_size: int = 32):
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self._model = None
        self._lock = threading.Lock()

    def _get_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import SentenceTransformer

                    logger.info("Chargement du modèle d'embedding %s...", self.model_name)
                    self._model = SentenceTransformer(self.model_name, device=self.device)
                    self._model.max_seq_length = 512
                    logger.info("Modèle chargé sur %s.", self._model.device)
        return self._model

    def warmup(self) -> None:
        self._get_model()

    @property
    def dimension(self) -> int:
        return int(self._get_model().get_sentence_embedding_dimension())

    def embed_query(self, text: str) -> list[float]:
        vector = self._get_model().encode([f"query: {text}"], normalize_embeddings=True)[0]
        return vector.tolist()

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._get_model().encode(
            [f"passage: {t}" for t in texts],
            normalize_embeddings=True,
            batch_size=self.batch_size,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vectors]
