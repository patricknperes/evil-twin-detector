param(
    [string]$Python = "python",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot

Set-Location $ProjectRoot

Write-Host ""
Write-Host "Evil Twin Detector - renderer/Electron E2E"
Write-Host ""

$ToolchainArgs = @(
    (Join-Path $ProjectRoot "scripts\frontend_toolchain.py"),
    "--project-root",
    $ProjectRoot,
    "--output",
    (Join-Path $ProjectRoot "reports\frontend\frontend_toolchain_step47.json"),
    "--probe-registry"
)

if (-not $SkipInstall) {
    $ToolchainArgs += "--install"
}

& $Python @ToolchainArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Frontend dependency-resolved validation is not ready."
    exit $LASTEXITCODE
}

& $Python (
    Join-Path $ProjectRoot "scripts\renderer_e2e.py"
) `
    --project-root $ProjectRoot `
    --output (
        Join-Path $ProjectRoot `
            "reports\frontend\renderer_e2e_step49.json"
    ) `
    --run

exit $LASTEXITCODE
