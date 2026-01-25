"""Main FastAPI application."""
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from typing import Optional
import json

from config import settings
from rag import RAGEngine

app = FastAPI(
    title="RAG IG2I API",
    description="API RAG multi-niveaux pour IG2I",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RAG Engine (lazy loaded)
rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    """Get or create RAG engine."""
    global rag_engine
    if rag_engine is None:
        rag_engine = RAGEngine()
    return rag_engine


class ChatRequest(BaseModel):
    """Chat request model."""
    query: str
    level: int = 1  # 1 = usagers, 2 = direction
    stream: bool = True


class ChatResponse(BaseModel):
    """Chat response model."""
    answer: str
    sources: list


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    qdrant: str
    llm: str


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    engine = get_rag_engine()
    llm_status = "not loaded"
    try:
        if await engine.is_llm_loaded():
            llm_status = "loaded"
    except:
        pass
        
    return HealthResponse(
        status="healthy",
        qdrant="connected" if engine.is_qdrant_connected() else "disconnected",
        llm=llm_status
    )


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint with streaming support."""
    engine = get_rag_engine()
    
    if request.level not in [1, 2]:
        raise HTTPException(status_code=400, detail="Level must be 1 or 2")
    
    if request.stream:
        return EventSourceResponse(
            engine.stream_response(request.query, request.level),
            media_type="text/event-stream"
        )
    else:
        response = await engine.get_response(request.query, request.level)
        return ChatResponse(
            answer=response["answer"],
            sources=response["sources"]
        )


@app.post("/api/ingest")
async def ingest_documents(api_key: str = Header(None, alias="X-API-Key")):
    """Ingest documents (admin only)."""
    if settings.api_key and api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    from ingest import ingest_all_documents
    result = ingest_all_documents()
    return result


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
