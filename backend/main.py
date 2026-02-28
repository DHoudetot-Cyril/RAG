from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import os
import httpx
from rag_engine import search_and_generate
from ingestion_service import IngestionService
import shutil

app = FastAPI(title="RAG École API")
ingestion_service = IngestionService()

# Environment Variables
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = os.getenv("QDRANT_PORT", 6333)
VLLM_HOST = os.getenv("VLLM_HOST", "localhost")
VLLM_PORT = os.getenv("VLLM_PORT", 8000)

class ChatRequest(BaseModel):
    message: str
    level: str  # "level1" or "level2"

@app.get("/health")
async def health_check():
    return {"status": "ok", "components": {"vllm": VLLM_HOST, "qdrant": QDRANT_HOST}}

@app.post("/chat/student")
async def chat_student(request: ChatRequest):
    if request.level != "level1":
        raise HTTPException(status_code=403, detail="Students can only access Level 1.")
    
    result = await search_and_generate(request.message, "level1")
    return result

@app.post("/chat/prof")
async def chat_prof(request: ChatRequest):
    # Profs can access Level 1 and Level 2
    result = await search_and_generate(request.message, request.level)
    return result

@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...), level: str = Form(...)):
    if level not in ["level1", "level2"]:
        raise HTTPException(status_code=400, detail="Invalid level")
    
    # Save temp file
    temp_filename = f"temp_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        result = ingestion_service.process_pdf(temp_filename, level, file.filename)
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            
    return result

@app.get("/documents")
async def list_documents():
    """Retourne la liste des documents ingérés par collection."""
    from qdrant_client import QdrantClient
    client = QdrantClient(host=QDRANT_HOST, port=int(QDRANT_PORT))
    
    collections = {
        "level1": "level1_usagers",
        "level2": "level2_direction"
    }
    
    result = {}
    for level, col_name in collections.items():
        try:
            # Scroll through all points to get unique sources
            seen_sources = {}
            offset = None
            while True:
                scroll_result = client.scroll(
                    collection_name=col_name,
                    limit=100,
                    offset=offset,
                    with_payload=["source"],
                    with_vectors=False
                )
                points, next_offset = scroll_result
                for point in points:
                    source = point.payload.get("source", "Inconnu")
                    if source not in seen_sources:
                        seen_sources[source] = 0
                    seen_sources[source] += 1
                if next_offset is None:
                    break
                offset = next_offset
            
            result[level] = [{"source": src, "chunks": count} for src, count in seen_sources.items()]
        except Exception as e:
            result[level] = []
    
    return result
