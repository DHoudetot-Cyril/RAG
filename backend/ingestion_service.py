import fitz  # PyMuPDF
from qdrant_client import QdrantClient
from qdrant_client.http import models
from model_loader import get_embedding_model
import uuid
import os

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = os.getenv("QDRANT_PORT", 6333)

class IngestionService:
    def __init__(self):
        self.qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        
    def process_pdf(self, file_path: str, level: str, original_filename: str):
        # 1. Extract Text
        doc = fitz.open(file_path)
        chunks = []
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            # Simple chunking by paragraph or fixed size (MVP: Page level or 500 chars intersection)
            # For this MVP, let's chunk by semantic paragraphs roughly
            
            # Very naive chunking for robust demo: 1000 chars with 200 overlap
            chunk_size = 1000
            overlap = 200
            
            for i in range(0, len(text), chunk_size - overlap):
                chunk_text = text[i:i + chunk_size].strip()
                if len(chunk_text) > 50: # Ignore tiny chunks
                    chunks.append({
                        "text": chunk_text,
                        "page": page_num + 1,
                        "source": original_filename
                    })
                    
        if not chunks:
            return {"status": "warning", "message": "No text extracted from PDF"}

        # 2. Generate Embeddings
        model = get_embedding_model()
        texts = [c["text"] for c in chunks]
        # e5 models require "passage: " prefix for documents
        texts_for_embedding = [f"passage: {t}" for t in texts]
        
        embeddings = model.encode(texts_for_embedding, normalize_embeddings=True)
        
        # 3. Upsert to Qdrant
        points = []
        collection_name = "level1_usagers" if level == "level1" else "level2_direction"
        
        for i, chunk in enumerate(chunks):
            points.append(models.PointStruct(
                id=str(uuid.uuid4()),
                vector=embeddings[i].tolist(),
                payload=chunk
            ))
            
        self.qdrant_client.upsert(
            collection_name=collection_name,
            points=points
        )
        
        return {"status": "success", "chunks_count": len(chunks)}
