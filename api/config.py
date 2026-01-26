"""Configuration settings for RAG API with vLLM."""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # Qdrant
    qdrant_host: str = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6333"))
    collection_name: str = os.getenv("COLLECTION_NAME", "rag_ig2i")
    
    # vLLM Server
    vllm_host: str = os.getenv("VLLM_HOST", "localhost")
    vllm_port: int = int(os.getenv("VLLM_PORT", "8000"))
    llm_model: str = os.getenv("LLM_MODEL", "cyankiwi/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit")
    
    # Embedding
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
    
    # API
    api_key: str = os.getenv("API_KEY", "")
    
    # RAG
    top_k: int = 5
    chunk_size: int = 512
    chunk_overlap: int = 50
    max_tokens: int = 1024
    temperature: float = 0.7
    
    @property
    def vllm_base_url(self) -> str:
        """Get vLLM OpenAI-compatible base URL."""
        return f"http://{self.vllm_host}:{self.vllm_port}/v1"


settings = Settings()
