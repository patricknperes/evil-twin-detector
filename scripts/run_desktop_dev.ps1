$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $ProjectRoot "frontend"

Write-Host "Evil Twin Detector - desktop development"
Write-Host ""
Write-Host "Electron will start the FastAPI backend automatically."
Write-Host "Backend URL: http://127.0.0.1:8765"
Write-Host ""

Set-Location $Frontend

npm run electron:dev
