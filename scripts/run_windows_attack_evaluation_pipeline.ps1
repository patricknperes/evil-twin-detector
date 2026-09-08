param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "powershell_compat.ps1")

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Assert-EvilTwinWindowsHost -Message (
    "A avaliação do experimento controlado deve ser executada no Windows."
)
Set-Location $ProjectRoot

Write-Host ""
Write-Host "Desktop Candidate V1 - avaliação do ataque controlado"
Write-Host ""
Write-Host "Pré-condição: reference/scaler/model/threshold já estão congelados."
Write-Host "Este script NÃO refaz fit nem recalibra threshold."
Write-Host ""

Write-Host "[1/4] Importar sessões de ataque controlado"
& $Python -m desktop.windows.import_controlled_attack
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/4] Derivar features com referência congelada"
& $Python -m desktop.windows.prepare_controlled_attack_features
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/4] Avaliação final com artefatos fixos"
& $Python -m desktop.windows.evaluate_frozen_desktop_model
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[4/4] Bundle agregado final do TCC"
& $Python -m desktop.windows.generate_final_tcc_results
exit $LASTEXITCODE
