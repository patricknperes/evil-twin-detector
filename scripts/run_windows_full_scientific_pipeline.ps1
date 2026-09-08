param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "powershell_compat.ps1")

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Assert-EvilTwinWindowsHost -Message "A pipeline científica Windows deve ser executada no Windows."
Set-Location $ProjectRoot

Write-Host ""
Write-Host "Desktop Candidate V1 - scientific pipeline pós-coleta"
Write-Host ""
Write-Host "Este script NÃO coleta dados. Ele processa sessões já coletadas."
Write-Host ""

Write-Host "[1/9] Import normal sessions"
& $Python -m desktop.windows.import_own_normal
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/9] Scientific preflight"
& $Python -m desktop.windows.scientific_preflight
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/9] Frozen split/reference/features"
& $Python -m desktop.windows.prepare_desktop_reference
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[4/9] ML matrices + train-only scaler"
& $Python -m desktop.windows.prepare_desktop_ml
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[5/9] OCSVM + validation P95"
& $Python -m desktop.windows.train_desktop_ocsvm
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[6/9] Import controlled attack sessions"
& $Python -m desktop.windows.import_controlled_attack
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[7/9] Attack features using frozen normal reference"
& $Python -m desktop.windows.prepare_controlled_attack_features
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[8/9] Fixed-artifact final evaluation"
& $Python -m desktop.windows.evaluate_frozen_desktop_model
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[9/9] Aggregate final TCC results"
& $Python -m desktop.windows.generate_final_tcc_results
exit $LASTEXITCODE
