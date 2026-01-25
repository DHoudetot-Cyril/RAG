"""Document ingestion script."""
import os
from pathlib import Path
from typing import List, Dict
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer
from docling.document_converter import DocumentConverter

from config import settings


def get_files_from_directory(directory: str, extensions: List[str] = None) -> List[Path]:
    """Get all files from directory with given extensions."""
    extensions = extensions or [".pdf", ".docx", ".doc", ".txt", ".md"]
    files = []
    dir_path = Path(directory)
    
    if dir_path.exists():
        for ext in extensions:
            files.extend(dir_path.rglob(f"*{ext}"))
    
    return files


def parse_document(file_path: Path) -> List[Dict]:
    """Parse document using Docling."""
    converter = DocumentConverter()
    
    try:
        result = converter.convert(str(file_path))
        doc = result.document
        
        # Extract text content
        text = doc.export_to_markdown()
        
        return [{
            "text": text,
            "source": file_path.name,
            "page": 1  # Docling gives full document
        }]
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        # Fallback to simple text extraction
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            return [{
                "text": text,
                "source": file_path.name,
                "page": 1
            }]
        except:
            return []


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    
    return chunks


def ingest_all_documents():
    """Ingest all documents from data directories."""
    # Initialize clients
    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    embedder = SentenceTransformer(settings.embedding_model)
    
    # Create collection if not exists
    try:
        qdrant.get_collection(settings.collection_name)
        print(f"Collection {settings.collection_name} exists, deleting...")
        qdrant.delete_collection(settings.collection_name)
    except:
        pass
    
    # Create new collection
    qdrant.create_collection(
        collection_name=settings.collection_name,
        vectors_config=VectorParams(
            size=1024,  # e5-large dimension
            distance=Distance.COSINE
        )
    )
    
    all_points = []
    point_id = 0
    
    # Process niveau1-usagers
    niveau1_dir = "/data/niveau1-usagers"
    niveau1_files = get_files_from_directory(niveau1_dir)
    print(f"Found {len(niveau1_files)} files in niveau1-usagers")
    
    for file_path in niveau1_files:
        docs = parse_document(file_path)
        for doc in docs:
            chunks = chunk_text(doc["text"], settings.chunk_size, settings.chunk_overlap)
            for chunk in chunks:
                # Generate embedding
                embedding = embedder.encode(f"passage: {chunk}").tolist()
                
                all_points.append(PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": chunk,
                        "source": doc["source"],
                        "page": doc["page"],
                        "access_level": 1  # niveau1
                    }
                ))
                point_id += 1
    
    # Process niveau2-direction
    niveau2_dir = "/data/niveau2-direction"
    niveau2_files = get_files_from_directory(niveau2_dir)
    print(f"Found {len(niveau2_files)} files in niveau2-direction")
    
    for file_path in niveau2_files:
        docs = parse_document(file_path)
        for doc in docs:
            chunks = chunk_text(doc["text"], settings.chunk_size, settings.chunk_overlap)
            for chunk in chunks:
                embedding = embedder.encode(f"passage: {chunk}").tolist()
                
                all_points.append(PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": chunk,
                        "source": doc["source"],
                        "page": doc["page"],
                        "access_level": 2  # niveau2
                    }
                ))
                point_id += 1
    
    # Batch upsert
    if all_points:
        batch_size = 100
        for i in range(0, len(all_points), batch_size):
            batch = all_points[i:i + batch_size]
            qdrant.upsert(
                collection_name=settings.collection_name,
                points=batch
            )
    
    result = {
        "status": "success",
        "documents_processed": len(niveau1_files) + len(niveau2_files),
        "chunks_created": len(all_points),
        "niveau1_files": len(niveau1_files),
        "niveau2_files": len(niveau2_files)
    }
    
    print(f"Ingestion complete: {result}")
    return result


if __name__ == "__main__":
    ingest_all_documents()
