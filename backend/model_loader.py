from sentence_transformers import SentenceTransformer
import os

_EMBEDDING_MODEL = None

def get_embedding_model():
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        model_name = os.getenv("EMBEDDING_MODEL_NAME", "intfloat/multilingual-e5-large")
        print(f"Loading embedding model: {model_name}...")
        _EMBEDDING_MODEL = SentenceTransformer(model_name)
        print("Embedding model loaded.")
    return _EMBEDDING_MODEL
