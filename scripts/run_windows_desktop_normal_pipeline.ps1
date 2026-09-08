param(
    [string]$Python = "python",
    [string]$InterimRoot = "data/interim/own/windows",
    [string]$PreparedRoot = "data/processed/desktop_candidate_v1",
    [string]$ScaledRoot = "data/processed/ml_ready/desktop_candidate_v1_scaled"
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "powershell_compat.ps1")

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Assert-EvilTwinWindowsHost -Message "A pipeline Windows deve ser executada no Windows."
Set-Location $ProjectRoot

Write-Host ""
Write-Host "Desktop Candidate V1 - pipeline normal"
Write-Host ""

Write-Host "[1/5] Importando sessões..."
& $Python -m desktop.windows.import_own_normal
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/5] Pré-flight científico..."
& $Python -m desktop.windows.scientific_preflight `
    --interim-root $InterimRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/5] Criando split/referência/features..."
& $Python -m desktop.windows.prepare_desktop_reference `
    --interim-root $InterimRoot `
    --output-root $PreparedRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[4/5] Criando X/y/metadata + scaler..."
& $Python -m desktop.windows.prepare_desktop_ml `
    --prepared-root $PreparedRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[5/5] Treinando OCSVM + calibrando P95..."
& $Python -m desktop.windows.train_desktop_ocsvm `
    --scaled-root $ScaledRoot

exit $LASTEXITCODE
