#!/bin/bash

echo "🚀 Début de la mise à jour et du déploiement..."

# 1. Pull des derniers changements
echo "📥 Récupération des changements Git..."
git pull

if [ $? -ne 0 ]; then
    echo "❌ Erreur lors du git pull."
    exit 1
fi

# 2. Arrêt des conteneurs
echo "🛑 Arrêt des conteneurs..."
docker compose down

# 3. Rebuild et redémarrage
echo "🏗️ Reconstruction et démarrage des conteneurs..."
docker compose up -d --build

if [ $? -ne 0 ]; then
    echo "❌ Erreur lors du déploiement Docker."
    exit 1
fi

echo "✅ Déploiement terminé avec succès !"
docker compose ps
