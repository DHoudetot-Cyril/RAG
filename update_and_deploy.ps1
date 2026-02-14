Write-Host "🚀 Début de la mise à jour et du déploiement..." -ForegroundColor Green

# 1. Pull des derniers changements
Write-Host "📥 Récupération des changements Git..." -ForegroundColor Cyan
git pull

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors du git pull." -ForegroundColor Red
    exit 1
}

# 2. Arrêt des conteneurs
Write-Host "🛑 Arrêt des conteneurs..." -ForegroundColor Yellow
docker compose down

# 3. Rebuild et redémarrage
Write-Host "🏗️ Reconstruction et démarrage des conteneurs..." -ForegroundColor Cyan
docker compose up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors du déploiement Docker." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Déploiement terminé avec succès !" -ForegroundColor Green
docker compose ps
