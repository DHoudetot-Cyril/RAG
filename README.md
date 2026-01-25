# 🧠 Assistant RAG IG2I

Système RAG (Retrieval-Augmented Generation) haute performance pour l'IG2I, conçu pour tourner sur une **Tesla V100 32GB** avec isolation des données par niveau d'accès.

![Architecture](_bmad-output/planning-artifacts/architecture.md)

## ✨ Fonctionnalités

*   **Architecture Multi-niveaux** :
    *   **Niveau 1 (Usagers)** : Accès restreint aux documents publics, interface simplifiée.
    *   **Niveau 2 (Direction)** : Accès global (public + confidentiel), interface enrichie avec sources et export.
*   **Performance SOTA** :
    *   Moteur d'inférence **vLLM** avec *PagedAttention* et *Continuous Batching*.
    *   Modèle LLM **Qwen2.5-7B-Instruct** (FP16) pour le meilleur ratio intelligence/vitesse.
    *   Cache de préfixe activé pour des réponses ultra-rapides.
*   **Ingestion Intelligente** :
    *   Parsing PDF/DOCX avancé avec **Docling**.
    *   Embedding multilingue avec **e5-large**.
    *   Base vectorielle **Qdrant** avec filtrage de métadonnées.
*   **Interface Moderne** :
    *   Streaming fluide (SSE).
    *   Thème sombre professionnel.
    *   Citations interactives des sources (Niveau 2).

## 🏗️ Architecture

Le projet utilise Docker Compose pour orchestrer 5 services :

1.  **vLLM** (`:8080`) : Serveur d'inférence LLM optimisé GPU.
2.  **Qdrant** (`:6333`) : Base de données vectorielle.
3.  **API RAG** (`:8000`) : Backend FastAPI (Logique métier, Auth, Ingestion).
4.  **Frontend Niveau 1** (`:5173`) : Interface Web Usagers.
5.  **Frontend Niveau 2** (`:5174`) : Interface Web Direction.

## 🚀 Démarrage Rapide

### Prérequis

*   Docker & Docker Compose
*   Drivers NVIDIA + NVIDIA Container Toolkit
*   Une carte GPU avec min 24GB VRAM (Tesla V100 32GB recommandée)

### Installation

1.  **Cloner le dépôt**
    ```bash
    git clone <votre-repo>
    cd RAG
    ```

2.  **Configuration Environnement**
    Copiez le fichier d'exemple et configurez votre token HuggingFace (requis pour certains modèles).
    ```bash
    cp .env.example .env
    # Éditez .env et ajoutez votre HF_TOKEN si nécessaire
    ```

3.  **Lancer les Services**
    ```bash
    docker compose up -d
    ```
    *Note : Le premier lancement télécharge les modèles (LLM + Embedding), cela peut prendre quelques minutes.*

4.  **Vérifier le Statut**
    Attendez que le service vLLM soit prêt (healthcheck healthy).
    ```bash
    docker compose logs -f vllm
    ```

### Ingestion des Documents

Placez vos documents dans les dossiers `donnees_IG2I/niveau1-usagers` et `donnees_IG2I/niveau2-direction`, puis lancez l'ingestion :

```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "X-API-Key: votre-cle-secrete"
```

## 🖥️ Utilisation

| Interface     | URL                                                      | Description                                  |
| ------------- | -------------------------------------------------------- | -------------------------------------------- |
| **Usagers**   | [http://localhost:5173](http://localhost:5173)           | Chat simple, accès niveau 1 uniquement.      |
| **Direction** | [http://localhost:5174](http://localhost:5174)           | Chat avancé, accès complet, sources, export. |
| **API Docs**  | [http://localhost:8000/docs](http://localhost:8000/docs) | Documentation Swagger de l'API.              |
| **vLLM**      | [http://localhost:8080](http://localhost:8080)           | Métriques et API OpenAI-compatible.          |

## 🛠️ Configuration Avancée

Vous pouvez modifier les modèles utilisés dans le fichier `.env` :

*   `LLM_MODEL` : Par défaut `Qwen/Qwen2.5-7B-Instruct`. Autres options : `mistralai/Mistral-Nemo-Instruct-2407`.
*   `EMBEDDING_MODEL` : Par défaut `intfloat/multilingual-e5-large`.

## 📦 Structure du Projet

```
RAG/
├── api/                # Backend FastAPI & Scripts Ingestion
├── frontend/           # Interfaces Web (Nginx)
│   ├── niveau1/        # Code source UI Usagers
│   └── niveau2/        # Code source UI Direction
├── donnees_IG2I/       # Dossiers de documents (bind mount)
│   ├── niveau1-usagers/
│   └── niveau2-direction/
├── docker-compose.yml  # Orchestration
└── .env.example        # Configuration
```

## 🔒 Sécurité

*   L'API RAG filtre strictement les résultats Qdrant en fonction du niveau demandé (`level` dans la requête).
*   L'ingestion est protégée par une API Key.
*   Les conteneurs frontend sont isolés et communiquent uniquement avec l'API.

---
**Auteur** : Cyrd6 avec Assistant BMad
**Date** : Janvier 2026
