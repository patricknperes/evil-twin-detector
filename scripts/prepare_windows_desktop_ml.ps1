param(
    [string]$Python = "python",
    [string]$InterimRoot = "data/interim/own/windows",
    [string]$PreparedRoot = "data/processed/desktop_candidate_v1"
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "powershell_compat.ps1")

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Assert-EvilTwinWindowsHost -Message "A preparação desktop Windows deve ser executada no Windows."
Set-Location $ProjectRoot

Write-Host ""
Write-Host "Desktop Candidate V1 - preparação científica"
Write-Host ""

Write-Host "[1/4] Importando sessões normais..."
& $Python -m desktop.windows.import_own_normal
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/4] Pré-flight científico..."
& $Python -m desktop.windows.scientific_preflight `
    --interim-root $InterimRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/4] Planejando split e referência congelada..."
& $Python -m desktop.windows.prepare_desktop_reference `
    --interim-root $InterimRoot `
    --output-root $PreparedRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[4/4] Gerando X/y/metadata e StandardScaler..."
& $Python -m desktop.windows.prepare_desktop_ml `
    --prepared-root $PreparedRoot

exit $LASTEXITCODE
