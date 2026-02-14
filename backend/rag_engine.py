from qdrant_client import QdrantClient
import httpx
import os

# Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = os.getenv("QDRANT_PORT", 6333)
VLLM_HOST = os.getenv("VLLM_HOST", "localhost")
VLLM_PORT = os.getenv("VLLM_PORT", 8000)

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

async def search_and_generate(query: str, level: str):
    # 1. Select Collections based on Level
    collections_to_search = ["level1_usagers"]
    if level == "level2":
        collections_to_search.append("level2_direction")
    
    # 2. Search Qdrant (Placeholder for actual embedding + search)
    # We need an embedding function here. For MVP, we might assume the query is already embedded
    # or use a lightweight local model.
    # For now, let's mock the search result.
    
    context = "Ceci est un contexte simulé provenant de la base de données."
    source = "doc_simule.pdf"

    # 3. Call vLLM
    prompt = f"""Vous êtes un assistant pédagogique. Utilisez le contexte suivant pour répondre à la question.
    
Contexte: {context}

Question: {query}

Réponse:"""

    async with httpx.AsyncClient() as http_client:
        try:
            response = await http_client.post(
                f"http://{VLLM_HOST}:{VLLM_PORT}/v1/completions",
                json={
                    "model": "Qwen/Qwen2.5-7B-Instruct",
                    "prompt": prompt,
                    "max_tokens": 512,
                    "temperature": 0.3
                },
                timeout=30.0
            ) 
            if response.status_code == 200:
                generated_text = response.json()["choices"][0]["text"]
                return {"response": generated_text, "source": source}
            else:
                return {"response": "Erreur lors de la génération.", "source": "Système"}
        except Exception as e:
             return {"response": f"Erreur vLLM: {e}", "source": "Système"}
