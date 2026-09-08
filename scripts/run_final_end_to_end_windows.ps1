param(
    [string]$Python = "python",
    [switch]$SkipDependencyInstall,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "powershell_compat.ps1")

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $ProjectRoot "frontend"

Set-Location $ProjectRoot

Assert-EvilTwinWindowsHost -Message "A execução final deve ocorrer em Windows 10/11."


Write-Host ""
Write-Host "Evil Twin Detector - FINAL E2E"
Write-Host ""
Write-Host "Este script NÃO coleta redes nem cria um Evil Twin."
Write-Host "Ele exige que as sessões normais e a sessão defensiva/autorizada"
Write-Host "de ataque controlado já tenham sido coletadas."
Write-Host ""

Write-Host "[0/14] Integração determinística desktop"
& $Python -m desktop.integration.run_step48 --project-root $ProjectRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[1/14] Importar sessões normais"
& $Python -m desktop.windows.import_own_normal
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/14] Pré-flight científico"
& $Python -m desktop.windows.scientific_preflight
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/14] Freeze do split/referência"
& $Python -m desktop.windows.prepare_desktop_reference
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[4/14] ML-ready + StandardScaler + lineage"
& $Python -m desktop.windows.prepare_desktop_ml
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[5/14] OCSVM + threshold normal-only"
& $Python -m desktop.windows.train_desktop_ocsvm
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[6/14] Importar ataque controlado já coletado"
& $Python -m desktop.windows.import_controlled_attack
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[7/14] Features de ataque com referência congelada"
& $Python -m desktop.windows.prepare_controlled_attack_features
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[8/14] Avaliação final - artefatos fixos"
& $Python -m desktop.windows.evaluate_frozen_desktop_model
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[9/14] Gerar bundle final do TCC"
& $Python -m desktop.windows.generate_final_tcc_results
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[10/14] Testes Python"
& $Python -m pytest -q tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[11/14] Frontend dependency-resolved validation"
& (
    Join-Path $ProjectRoot "scripts\validate_frontend_toolchain.ps1"
) `
    -Python $Python `
    -SkipInstall:$SkipDependencyInstall

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[12/14] Renderer/Electron E2E"
& (
    Join-Path $ProjectRoot "scripts\validate_renderer_e2e.ps1"
) `
    -Python $Python `
    -SkipInstall:$SkipDependencyInstall

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Release preflight de inputs"
& $Python -m desktop.release_preflight `
    --project-root $ProjectRoot `
    --target inputs `
    --json-output (
        Join-Path $ProjectRoot `
            "reports\desktop\release_preflight_step51.json"
    )

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[13/14] Backend PyInstaller"
& (
    Join-Path $ProjectRoot "scripts\build_backend_windows.ps1"
) `
    -Python $Python `
    -SkipDependencyInstall:$SkipDependencyInstall

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipInstaller) {
    Write-Host "[14/14] Electron + NSIS"

    & (
        Join-Path $ProjectRoot "scripts\build_desktop_installer_windows.ps1"
    ) `
        -Python $Python `
        -SkipDependencyInstall:$SkipDependencyInstall `
        -SkipBackendBuild

    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
else {
    Write-Host "[14/14] NSIS pulado explicitamente."
}

Write-Host ""
Write-Host "Recalculando a matriz final..."
& $Python -m desktop.final_readiness `
    --project-root $ProjectRoot

exit $LASTEXITCODE
