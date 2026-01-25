#!/bin/bash

# Script de démarrage automatisé pour RAG IG2I (Linux/macOS)
# Auteur: Cyrd6

# Couleurs
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}🚀 Démarrage de l'assistant RAG IG2I...${NC}"

# 1. Vérification des prérequis
echo -e "\n${YELLOW}🔍 Vérification des fichiers...${NC}"

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️ Fichier .env manquant. Création à partir de .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ Fichier .env créé. Pensez à l'éditer avec vos clés API !${NC}"
fi

if [ ! -d "models" ]; then
    mkdir -p "models"
fi

# 2. Redémarrage propre de Docker
echo -e "\n${YELLOW}🐳 Redémarrage des services Docker...${NC}"
docker compose down
if [ $? -ne 0 ]; then
    echo -e "${RED}Erreur lors de l'arrêt des conteneurs.${NC}"
    exit 1
fi

echo "Construction et démarrage..."
docker compose up -d --build
if [ $? -ne 0 ]; then
    echo -e "${RED}Erreur lors du démarrage des conteneurs.${NC}"
    exit 1
fi

# 3. Attente de la santé de l'API et vLLM
echo -e "\n${CYAN}⏳ Attente de la disponibilité des services (cela peut prendre quelques minutes pour le chargement des modèles)...${NC}"

max_retries=60 # 5 minutes
retry_count=0
api_ready=false

while [ $retry_count -lt $max_retries ]; do
    if command -v curl &> /dev/null; then
        response=$(curl -s http://localhost:8000/api/health)
        # Vérifie si le status est healthy et llm loaded
        if echo "$response" | grep -q '"status":"healthy"' && echo "$response" | grep -q '"llm":"loaded"'; then
            api_ready=true
            break
        fi
    else
        echo -e "${RED}Erreur: curl n'est pas installé.${NC}"
        exit 1
    fi
    
    echo -n "."
    sleep 5
    ((retry_count++))
done

echo ""

if [ "$api_ready" = true ]; then
    echo -e "${GREEN}✅ Services API et vLLM opérationnels !${NC}"
else
    echo -e "${RED}❌ Délai d'attente dépassé. Les services ne sont pas prêts. Vérifiez les logs avec 'docker compose logs'.${NC}"
    exit 1
fi

# 4. Ingestion des documents
echo -e "\n${CYAN}📚 Lancement de l'ingestion des documents...${NC}"

# Récupérer la clé API du fichier .env
api_key=$(grep "^API_KEY=" .env | cut -d '=' -f2)

if [ -n "$api_key" ]; then
    ingest_response=$(curl -s -X POST http://localhost:8000/api/ingest -H "X-API-Key: $api_key")
else
    ingest_response=$(curl -s -X POST http://localhost:8000/api/ingest)
fi

echo -e "${GREEN}✅ Ingestion terminée avec succès !${NC}"
echo "   Réponse: $ingest_response"

echo -e "\n${GREEN}🎉 Tout est prêt !${NC}"
echo "   Frontend Usagers   : http://localhost:5173"
echo "   Frontend Direction : http://localhost:5174"
echo "   API Docs           : http://localhost:8000/docs"
