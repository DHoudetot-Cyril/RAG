.PHONY: help setup up down logs ps ingest-examples eval test lint format

help:  ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup:  ## Crée le fichier .env à partir de l'exemple
	@test -f .env || (cp .env.example .env && echo ".env créé : pensez à changer les clés d'API.")

up: setup  ## Construit et démarre la stack
	docker compose up -d --build

down:  ## Arrête la stack
	docker compose down

logs:  ## Suit les logs de l'API
	docker compose logs -f backend

ps:  ## État des conteneurs
	docker compose ps

ingest-examples:  ## Ingère les documents d'exemple fictifs
	docker compose cp examples/documents backend:/tmp/examples
	docker compose exec backend sh -c 'python scripts/ingest_folder.py /tmp/examples --key "$$ADMIN_API_KEY"'

eval:  ## Évalue la recherche sur le jeu de questions d'exemple
	set -a && . ./.env && set +a && python eval/evaluate.py

test:  ## Lance les tests du backend
	cd backend && python -m pytest

lint:  ## Vérifie le style (ruff)
	cd backend && ruff check . && ruff format --check . && ruff check ../frontend ../eval

format:  ## Formate le code
	cd backend && ruff format . ../frontend ../eval && ruff check --fix . ../frontend ../eval
