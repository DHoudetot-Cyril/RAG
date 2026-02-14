from qdrant_client import QdrantClient
from model_loader import get_embedding_model
import httpx
import os

# Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = os.getenv("QDRANT_PORT", 6333)
VLLM_HOST = os.getenv("VLLM_HOST", "localhost")
VLLM_PORT = os.getenv("VLLM_PORT", 8000)

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

async def search_and_generate(query: str, level: str):
    # 1. Embed Query
    model = get_embedding_model()
    # e5 models require "query: " prefix for queries
    query_embedding = model.encode([f"query: {query}"], normalize_embeddings=True)[0]
    
    # 2. Search Qdrant
    collections_to_search = ["level1_usagers"]
    if level == "level2":
        collections_to_search.append("level2_direction")
    
    hits = []
    for col in collections_to_search:
        results = client.query_points(
            collection_name=col,
            query=query_embedding.tolist(),
            limit=3
        ).points
        for res in results:
            hits.append(res)
            
    # Sort combined results by score and take top 3
    hits.sort(key=lambda x: x.score, reverse=True)
    top_hits = hits[:3]
    
    if not top_hits:
        return {"response": "Je n'ai trouvé aucune information pertinente dans les documents.", "source": "Aucune"}

    # Construct Context
    context_text = "\n\n".join([h.payload["text"] for h in top_hits])
    sources = list(set([h.payload["source"] for h in top_hits]))
    source_str = ", ".join(sources)

    # 3. Call vLLM
    prompt = f"""<|im_start|>system
Vous êtes "RAG Administration", un assistant administratif précis et formel pour l'école.
Votre mission est de répondre aux questions administratives (règlements, stages, procédures, dates) en vous basant UNIQUEMENT sur les documents officiels fournis ci-dessous.
Si la réponse n'est pas dans le contexte, dites "Je ne trouve pas cette information dans les règlements officiels, veuillez contacter le secrétariat."
Soyez courtois mais direct. Ne jamais inventer de règles ou de dates.
Ne mentionnez pas "le contexte" explicitement dans votre réponse.
Citez vos sources si possible.
Citez vos sources si possible.

Contexte:
{context_text}
<|im_end|>
<|im_start|>user
{query}
<|im_end|>
<|im_start|>assistant
"""

    async with httpx.AsyncClient() as http_client:
        try:
            response = await http_client.post(
                f"http://{VLLM_HOST}:{VLLM_PORT}/v1/completions",
                json={
                    "model": "Qwen/Qwen2.5-7B-Instruct",
                    "prompt": prompt,
                    "max_tokens": 512,
                    "temperature": 0.3,
                    "stop": ["<|im_end|>"]
                },
                timeout=60.0
            ) 
            if response.status_code == 200:
                generated_text = response.json()["choices"][0]["text"]
                return {"response": generated_text, "source": source_str}
            else:
                return {"response": f"Erreur de génération ({response.status_code}).", "source": "Système"}
        except Exception as e:
             return {"response": f"Erreur vLLM: {e}", "source": "Système"}
