# 🎓 RAG École - MVP

Une application de **RAG (Retrieval-Augmented Generation)** conçue pour le milieu éducatif, offrant des interfaces distinctes pour les **Élèves** (Niveau 1) et le **Personnel/Direction** (Niveau 2), avec une stricte isolation des données.

## 🏗️ Architecture Technique

Le projet est entièrement conteneurisé avec Docker et se compose de 6 services interconnectés :

| Service            | Technologie       | Rôle                                                         | Port (Hôte) |
| :----------------- | :---------------- | :----------------------------------------------------------- | :---------- |
| **Backend**        | FastAPI (Python)  | API centrale, orchestration RAG, gestion des embeddings.     | `8080`      |
| **vLLM**           | vLLM (Qwen2.5-7B) | Moteur d'inférence LLM optimisé pour GPU NVIDIA.             | `8000`      |
| **Qdrant**         | Qdrant            | Base de données vectorielle pour le stockage des documents.  | `6333`      |
| **Ingestion UI**   | Streamlit         | Interface d'administration pour uploader et ingérer les PDF. | `8503`      |
| **Frontend Élève** | Streamlit         | Interface de chat pour les étudiants (accès restreint).      | `8501`      |
| **Frontend Prof**  | Streamlit         | Interface de chat pour les professeurs (accès complet).      | `8502`      |

## 🚀 Prérequis

*   **OS** : Linux (Recommandé) ou Windows (WSL2).
*   **Docker** : Docker Engine + Docker Compose.
*   **GPU** : NVIDIA GPU avec au moins **16GB de VRAM** (recommandé 24GB+ pour Qwen2.5-7B avec contexte long).
*   **Drivers** : NVIDIA Drivers & NVIDIA Container Toolkit installés.

## 📦 Installation & Déploiement

### 1. Cloner le projet
```bash
git clone https://github.com/DHoudetot-Cyril/RAG.git
cd RAG
# Basculer sur la branche de développement GPU
git checkout develop/gpu_nvidia
```

### 2. Configuration (.env)
Créez un fichier `.env` à la racine si nécessaire (déjà inclus dans le repo pour le MVP) :
```env
HF_TOKEN=votre_token_huggingface_ici
```

### 3. Déploiement Automatisé
Utilisez le script de déploiement pour pull, build et lancer les conteneurs :

**Linux / Bash :**
```bash
chmod +x update_and_deploy.sh
./update_and_deploy.sh
```

**Windows / PowerShell :**
```powershell
./update_and_deploy.ps1
```

Cela va :
1.  Récupérer la dernière version du code (`git pull`).
2.  Construire les images Docker.
3.  Lancer les conteneurs en mode détaché.
4.  Pruner les images inutilisées.

## 🛠️ Utilisation

### 1. Ingestion de Documents (Admin)
Accédez à **[http://localhost:8503](http://localhost:8503)** (ou IP du serveur :8503).
1.  Uploadez un fichier PDF (ex: Règlement Intérieur, Cours de Maths).
2.  Sélectionnez le **Niveau d'accès** :
    *   **Niveau 1** : Accessible aux Élèves et Profs.
    *   **Niveau 2** : Accessible UNIQUEMENT aux Profs/Direction.
3.  Cliquez sur "Ingérer".

### 2. Interface Élève
Accédez à **[http://localhost:8501](http://localhost:8501)**.
*   Posez des questions sur les documents de **Niveau 1**.
*   *Test de sécurité* : Essayez de demander des infos confidentielles (Niveau 2), le système ne devrait pas répondre.

### 3. Interface Professeur
Accédez à **[http://localhost:8502](http://localhost:8502)**.
*   Posez des questions sur **tous** les documents (Niveau 1 + Niveau 2).
*   Onglet "Documents" : Permet de visualiser les fichiers disponibles (fonctionnalité à venir).

## 🔧 Dépannage

**Erreur : `Vector dimension error: expected dim: 768, got 1024`**
*   Le modèle d'embedding (`intfloat/multilingual-e5-large`) génère des vecteurs de taille 1024.
*   **Solution** : Supprimez les collections Qdrant et relancez `db_init.py` (déjà corrigé dans la dernière version).

**Erreur : Docker Permission Denied**
*   Assurez-vous que votre utilisateur est dans le groupe `docker` ou utilisez `sudo`.

**VRAM Insuffisante (OOM)**
*   Ajustez `--gpu-memory-utilization` dans le `docker-compose.yml` (service `vllm`). Baissez-le à `0.80` ou `0.70` si besoin.

## 🤝 Crédits
Projet développé pour le POC RAG École.
