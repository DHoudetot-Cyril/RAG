# 📘 Guide d'Utilisation Détaillé - RAG IG2I

Ce document explique en détail comment configurer, lancer et utiliser le système RAG.

---

## 1. Préparation des Modèles (vLLM)

### ❓ Question fréquente : Faut-il télécharger le modèle avant ?

**Réponse courte : NON.**

Par défaut, **vLLM télécharge automatiquement** le modèle spécifié dans la variable d'environnement `LLM_MODEL` lors du premier démarrage du conteneur.

Cependant, vous pouvez télécharger les modèles manuellement si vous avez une connexion lente ou souhaitez éviter le retéléchargement.

### Option A : Téléchargement Automatique (Recommandé)
Il suffit de configurer votre clé Hugging Face (si le modèle est restreint) dans le fichier `.env`.

1. Copiez `.env.example` vers `.env`
2. Modifiez `.env` :
   ```bash
   HF_TOKEN=votre_token_huggingface_ici
   LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
   ```
   *(Le modèle Qwen2.5-7B est excellent et ne nécessite pas toujours de token, mais c'est mieux d'en avoir un).*

### Option B : Téléchargement Manuel (Offline)
Si vous préférez gérer les modèles vous-même :
1. Créez un dossier `models` à la racine.
2. Téléchargez les fichiers du modèle (format SafeTensors/Pytorch, PAS GGUF pour vLLM).
3. Modifiez `docker-compose.yml` pour monter votre dossier local vers `/root/.cache/huggingface`.

---

## 2. Configuration de vLLM

Le moteur d'inférence est configuré dans `docker-compose.yml` -> service `vllm`.

Les paramètres clés sont :
*   `--dtype float16` : Utilise la précision FP16 (standard pour V100).
*   `--gpu-memory-utilization 0.85` : Alloue 85% de la VRAM au modèle et au cache KV. Si vous avez des erreurs OOM (Out Of Memory), baissez ce chiffre à 0.80.
*   `--max-model-len 8192` : Taille du contexte. Vous pouvez augmenter à 16384 ou 32768 si la VRAM le permet.
*   `--enable-prefix-caching` : **CRITIQUE**. Permet de ne pas recalculer le prompt système à chaque requête.

---

## 3. Lancement du Système

### Méthode Automatique (Facile)

Utilisez le script fourni qui gère tout (nettoyage, lancement, attente, ingestion).

*   **Windows (PowerShell)** :
    ```powershell
    .\start_rag.ps1
    ```

*   **Linux / macOS** :
    ```bash
    chmod +x start_rag.sh
    ./start_rag.sh
    ```

### Méthode Manuelle (Expert)

1.  **Démarrer les conteneurs** :
    ```bash
    docker compose up -d --build
    ```

2.  **Suivre les logs de vLLM** (pour voir le téléchargement/chargement) :
    ```bash
    docker compose logs -f vllm
    ```
    *Attendez de voir : `Application startup complete`.*

---

## 4. Ingestion des Documents

### Comment ça marche ?
Le script d'ingestion (`api/ingest.py`) :
1. Scanne les dossiers `donnees_IG2I/niveau1-usagers` et `niveau2-direction`.
2. Utilise **Docling** pour lire les fichiers (PDF, DOCX, TXT...).
3. Découpe le texte en morceaux (chunks) de 512 tokens.
4. Calcule les embeddings avec le modèle `e5-large`.
5. Envoie tout dans **Qdrant** en taguant chaque morceau avec son niveau d'accès.

### Où mettre mes fichiers ?
Placez simplement vos documents ici :
*   `RAG/donnees_IG2I/niveau1-usagers/` : Documents publics pour tous.
*   `RAG/donnees_IG2I/niveau2-direction/` : Documents confidentiels (visibles uniquement par la direction + les docs usagers).

### Lancer l'ingestion
Si vous avez utilisé le script de démarrage, c'est déjà fait. Sinon :

```bash
# Commande via l'API
curl -X POST http://localhost:8000/api/ingest \
  -H "X-API-Key: votre-cle-secrete"
```

---

## 5. Dépannage

### "vLLM crashed" / "OOM error"
*   **Cause** : Le modèle est trop gros pour la VRAM ou `gpu-memory-utilization` est trop haut.
*   **Solution** : Dans `docker-compose.yml`, réduisez `--gpu-memory-utilization` à `0.8` ou `0.75`. Ou choisissez un modèle plus petit (ex: un modèle 7B au lieu de 14B).

### "Ingestion lente"
*   **Cause** : C'est normal. Docling fait de l'OCR et de l'analyse de layout profonde.
*   **Solution** : Patience. Pour 300 documents, cela peut prendre plusieurs minutes.

### "L'interface ne répond pas"
*   **Vérification** : Regardez si l'API est en vie : `http://localhost:8000/api/health`. Si `llm: not loaded`, c'est que vLLM n'a pas fini de démarrer.

---

Bonne utilisation ! 🚀
