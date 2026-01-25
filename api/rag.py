"""RAG Engine with Qdrant and vLLM via OpenAI compatible API."""
import json
from typing import AsyncGenerator, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny
from sentence_transformers import SentenceTransformer
from openai import AsyncOpenAI

from config import settings


class RAGEngine:
    """RAG Engine combining retrieval and generation via vLLM."""
    
    def __init__(self):
        """Initialize RAG components."""
        self._qdrant: Optional[QdrantClient] = None
        self._embedder: Optional[SentenceTransformer] = None
        self._llm: Optional[AsyncOpenAI] = None
    
    @property
    def qdrant(self) -> QdrantClient:
        """Lazy load Qdrant client."""
        if self._qdrant is None:
            self._qdrant = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port
            )
        return self._qdrant
    
    @property
    def embedder(self) -> SentenceTransformer:
        """Lazy load embedding model."""
        if self._embedder is None:
            self._embedder = SentenceTransformer(settings.embedding_model)
        return self._embedder
    
    @property
    def llm(self) -> AsyncOpenAI:
        """Lazy load vLLM client."""
        if self._llm is None:
            self._llm = AsyncOpenAI(
                api_key=settings.api_key or "EMPTY",
                base_url=settings.vllm_base_url
            )
        return self._llm
    
    def is_qdrant_connected(self) -> bool:
        """Check Qdrant connection."""
        try:
            self.qdrant.get_collections()
            return True
        except Exception:
            return False
    
    async def is_llm_loaded(self) -> bool:
        """Check if vLLM is ready."""
        try:
            client = self.llm
            await client.models.list()
            return True
        except Exception:
            return False
    
    def get_embedding(self, text: str) -> list:
        """Generate embedding for text."""
        # e5 models require prefix
        text = f"query: {text}"
        return self.embedder.encode(text).tolist()
    
    def retrieve(self, query: str, level: int, top_k: int = None) -> list:
        """Retrieve relevant chunks from Qdrant."""
        top_k = top_k or settings.top_k
        query_vector = self.get_embedding(query)
        
        # Build filter based on access level
        if level == 1:
            # niveau1: only access_level=1
            query_filter = Filter(
                must=[FieldCondition(key="access_level", match=MatchValue(value=1))]
            )
        else:
            # niveau2: access_level=1 OR access_level=2
            query_filter = Filter(
                should=[
                    FieldCondition(key="access_level", match=MatchValue(value=1)),
                    FieldCondition(key="access_level", match=MatchValue(value=2))
                ]
            )
        
        results = self.qdrant.search(
            collection_name=settings.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=top_k
        )
        
        return [
            {
                "text": hit.payload.get("text", ""),
                "source": hit.payload.get("source", ""),
                "page": hit.payload.get("page", 0),
                "score": hit.score
            }
            for hit in results
        ]
    
    def build_messages(self, query: str, contexts: list, level: int) -> list:
        """Build messages for chat completion."""
        context_text = "\n\n".join([
            f"[{i+1}] {ctx['text']}"
            for i, ctx in enumerate(contexts)
        ])
        
        if level == 1:
            system = """Tu es un assistant IG2I. Réponds de manière concise et claire.
Utilise le contexte fourni pour répondre à la question."""
        else:
            system = """Tu es un assistant IG2I pour la direction. 
Fournis des réponses détaillées avec des références aux sources [1], [2], etc.
Utilise le contexte fourni pour répondre à la question."""
            
        user_content = f"""Contexte:
{context_text}

Question: {query}"""
        
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content}
        ]
    
    async def stream_response(self, query: str, level: int) -> AsyncGenerator[str, None]:
        """Stream LLM response using vLLM OpenAI API."""
        # Retrieve context
        contexts = self.retrieve(query, level)
        
        # Build messages
        messages = self.build_messages(query, contexts, level)
        
        # Stream generation
        stream = await self.llm.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                yield json.dumps({"token": token, "done": False})
        
        # Send sources at the end
        sources = [
            {"source": ctx["source"], "page": ctx["page"], "score": ctx["score"]}
            for ctx in contexts
        ]
        yield json.dumps({"sources": sources, "done": True})
    
    async def get_response(self, query: str, level: int) -> dict:
        """Get complete response (non-streaming)."""
        contexts = self.retrieve(query, level)
        messages = self.build_messages(query, contexts, level)
        
        response = await self.llm.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
            stream=False
        )
        
        answer = response.choices[0].message.content
        sources = [
            {"source": ctx["source"], "page": ctx["page"], "score": ctx["score"]}
            for ctx in contexts
        ]
        
        return {"answer": answer, "sources": sources}
