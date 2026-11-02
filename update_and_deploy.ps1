# Met à jour le code et redéploie la stack (utilise le fichier .env).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "🚀 Mise à jour et déploiement de RAG École" -ForegroundColor Green

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "⚠️  .env créé à partir de .env.example : modifiez les clés d'API puis relancez." -ForegroundColor Yellow
    exit 1
}

Write-Host "📥 Récupération du code..." -ForegroundColor Cyan
git pull --ff-only
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Échec du git pull." -ForegroundColor Red; exit 1 }

Write-Host "🏗️  Construction et démarrage des conteneurs..." -ForegroundColor Cyan
docker compose up -d --build --remove-orphans
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Échec du déploiement Docker." -ForegroundColor Red; exit 1 }

docker image prune -f | Out-Null
Write-Host "✅ Déploiement terminé." -ForegroundColor Green
docker compose ps
Write-Host "`n  Élève      : http://localhost:8501`n  Direction  : http://localhost:8502`n  Admin      : http://localhost:8503`n  API (docs) : http://localhost:8080/docs"
