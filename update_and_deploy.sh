#!/usr/bin/env bash
# Met à jour le code et redéploie la stack (utilise le fichier .env).
set -euo pipefail
cd "$(dirname "$0")"

echo "🚀 Mise à jour et déploiement de RAG École"

if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  .env créé à partir de .env.example : modifiez les clés d'API puis relancez."
    exit 1
fi

echo "📥 Récupération du code..."
git pull --ff-only

echo "🏗️  Construction et démarrage des conteneurs..."
docker compose up -d --build --remove-orphans

echo "🧹 Nettoyage des anciennes images..."
docker image prune -f >/dev/null

echo "✅ Déploiement terminé."
docker compose ps
echo
echo "  Élève      : http://localhost:8501"
echo "  Direction  : http://localhost:8502"
echo "  Admin      : http://localhost:8503"
echo "  API (docs) : http://localhost:8080/docs"
