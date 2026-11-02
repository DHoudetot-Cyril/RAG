"""Configuration centralisée, lue depuis les variables d'environnement (ou un fichier .env)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Qdrant ---
    qdrant_url: str = "http://localhost:6333"
    collection_level1: str = "level1_usagers"
    collection_level2: str = "level2_direction"

    # --- Embeddings ---
    embedding_model_name: str = "intfloat/multilingual-e5-large"
    embedding_device: str | None = None  # "cuda", "cpu" ou None (auto)
    preload_embedding_model: bool = True

    # --- LLM (n'importe quel serveur compatible OpenAI : vLLM, llama.cpp, Ollama...) ---
    llm_base_url: str = "http://localhost:8000/v1"
    llm_api_key: str = "not-needed"
    llm_model_name: str = "Qwen/Qwen2.5-7B-Instruct"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 768
    llm_timeout_seconds: float = 120.0

    # --- Retrieval ---
    top_k: int = 5
    min_score: float = 0.75  # score cosinus minimal (e5 produit des scores élevés) : à calibrer via eval/
    max_history_turns: int = 4

    # --- Découpage ---
    chunk_size: int = 1200  # caractères (~300 tokens, sous la limite de 512 de e5)
    chunk_overlap: int = 200

    # --- Ingestion ---
    max_upload_mb: int = 50

    # --- Authentification par clé d'API (une clé par rôle) ---
    student_api_key: str = "change-me-student"
    direction_api_key: str = "change-me-direction"
    admin_api_key: str = "change-me-admin"

    # --- Divers ---
    cors_origins: list[str] = ["*"]
    school_name: str = "l'établissement"


@lru_cache
def get_settings() -> Settings:
    return Settings()
