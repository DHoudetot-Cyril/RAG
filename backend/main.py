from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import os
import httpx

app = FastAPI(title="RAG École API")

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
    
    # Placeholder for RAG logic
    return {"response": f"Student response for: {request.message}", "source": "Level 1 Doc"}

@app.post("/chat/prof")
async def chat_prof(request: ChatRequest):
    # Profs can access Level 1 and Level 2
    
    # Placeholder for RAG logic
    return {"response": f"Prof response for: {request.message}", "source": f"Level {request.level} Doc"}

@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...), level: str = Form(...)):
    if level not in ["level1", "level2"]:
        raise HTTPException(status_code=400, detail="Invalid level")
    
    # Placeholder for Ingestion logic
    return {"status": "success", "filename": file.filename, "level": level}
