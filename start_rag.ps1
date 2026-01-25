# Script de démarrage automatisé pour RAG IG2I
# Auteur: Cyrd6

Write-Host "🚀 Démarrage de l'assistant RAG IG2I..." -ForegroundColor Cyan

# 1. Vérification des prérequis
Write-Host "`n🔍 Vérification des fichiers..." -ForegroundColor Yellow

if (-not (Test-Path ".env")) {
    Write-Host "⚠️ Fichier .env manquant. Création à partir de .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✅ Fichier .env créé. Pensez à l'éditer avec vos clés API !" -ForegroundColor Green
}

if (-not (Test-Path "models")) {
    New-Item -ItemType Directory -Force -Path "models" | Out-Null
}

$modelCount = (Get-ChildItem "models" -Filter "*.gguf").Count
if ($modelCount -eq 0 -and $env:LLM_MODEL -notmatch "Qwen") {
    Write-Host "⚠️ Aucun modèle GGUF trouvé dans /models. Assurez-vous d'avoir téléchargé les modèles si vous n'utilisez pas vLLM." -ForegroundColor Yellow
}

# 2. Redémarrage propre de Docker
Write-Host "`n🐳 Redémarrage des services Docker..." -ForegroundColor Yellow
docker compose down
if ($LASTEXITCODE -ne 0) {
    Write-Error "Erreur lors de l'arrêt des conteneurs."
    exit 1
}

Write-Host "Construction et démarrage..."
docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Error "Erreur lors du démarrage des conteneurs."
    exit 1
}

# 3. Attente de la santé de l'API et vLLM
Write-Host "`n⏳ Attente de la disponibilité des services (cela peut prendre quelques minutes pour le chargement des modèles)..." -ForegroundColor Cyan

$maxRetries = 60 # 60 * 5s = 5 minutes max
$retryCount = 0
$apiReady = $false

while ($retryCount -lt $maxRetries) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method Get -ErrorAction Stop
        if ($response.status -eq "healthy" -and $response.llm -eq "loaded") {
            $apiReady = $true
            break
        }
        Write-Host "." -NoNewline
    }
    catch {
        Write-Host "." -NoNewline
    }
    Start-Sleep -Seconds 5
    $retryCount++
}

Write-Host "" # Newline

if ($apiReady) {
    Write-Host "✅ Services API et vLLM opérationnels !" -ForegroundColor Green
} else {
    Write-Error "❌ Délai d'attente dépassé. Les services ne sont pas prêts. Vérifiez les logs avec 'docker compose logs'."
    exit 1
}

# 4. Ingestion des documents
Write-Host "`n📚 Lancement de l'ingestion des documents..." -ForegroundColor Cyan

# Récupérer la clé API du fichier .env
$apiKey = ""
foreach ($line in Get-Content ".env") {
    if ($line -match "^API_KEY=(.*)") {
        $apiKey = $matches[1]
    }
}

try {
    $headers = @{}
    if ($apiKey) {
        $headers["X-API-Key"] = $apiKey
    }

    $ingestResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/ingest" -Method Post -Headers $headers
    Write-Host "✅ Ingestion terminée avec succès !" -ForegroundColor Green
    Write-Host "   Documents traités : $($ingestResponse.documents_processed)"
    Write-Host "   Chunks créés      : $($ingestResponse.chunks_created)"
}
catch {
    Write-Error "❌ Erreur lors de l'ingestion : $_"
}

Write-Host "`n🎉 Tout est prêt !" -ForegroundColor Green
Write-Host "   Frontend Usagers   : http://localhost:5173"
Write-Host "   Frontend Direction : http://localhost:5174"
Write-Host "   API Docs           : http://localhost:8000/docs"
