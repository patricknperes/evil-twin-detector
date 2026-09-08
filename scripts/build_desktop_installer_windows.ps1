param(
    [string]$Python = "python",
    [switch]$SkipDependencyInstall,
    [switch]$SkipBackendBuild
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "powershell_compat.ps1")

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $ProjectRoot "frontend"
$BackendExe = Join-Path $Frontend "resources\backend\evil-twin-backend.exe"

Assert-EvilTwinWindowsHost -Message "O instalador Windows deve ser gerado em um host Windows."

Write-Host "Evil Twin Detector - Windows desktop installer"
Write-Host ""


Write-Host "Validating dependency-resolved frontend toolchain..."

& (
    Join-Path $ProjectRoot "scripts\validate_frontend_toolchain.ps1"
) `
    -Python $Python `
    -SkipInstall:$SkipDependencyInstall

if ($LASTEXITCODE -ne 0) {
    throw "Frontend dependency-resolved validation failed."
}

Write-Host ""
Write-Host "Validating renderer/Electron E2E..."

& (
    Join-Path $ProjectRoot "scripts\validate_renderer_e2e.ps1"
) `
    -Python $Python `
    -SkipInstall:$SkipDependencyInstall

if ($LASTEXITCODE -ne 0) {
    throw "Renderer/Electron E2E validation failed."
}

if (-not $SkipBackendBuild) {
    & (
        Join-Path $ProjectRoot "scripts\build_backend_windows.ps1"
    ) `
        -Python $Python `
        -SkipDependencyInstall:$SkipDependencyInstall

    if ($LASTEXITCODE -ne 0) {
        throw "Backend build failed."
    }
}

if (-not (Test-Path $BackendExe)) {
    throw "Backend executable is missing: $BackendExe"
}

Write-Host ""
Write-Host "Running strict release preflight..."

& $Python -m desktop.release_preflight `
    --project-root $ProjectRoot `
    --target installer `
    --json-output (
        Join-Path $ProjectRoot `
            "reports\desktop\release_preflight_step51.json"
    )

if ($LASTEXITCODE -ne 0) {
    throw "Release preflight blocked the installer build."
}

Set-Location $Frontend

Write-Host ""
Write-Host "Building NSIS installer..."

npm run dist:win

if ($LASTEXITCODE -ne 0) {
    throw "electron-builder failed."
}

Set-Location $ProjectRoot

Write-Host ""
Write-Host "Verifying release artifact and creating release manifest..."

& $Python -m desktop.release_preflight `
    --project-root $ProjectRoot `
    --target verify `
    --json-output (
        Join-Path $ProjectRoot `
            "reports\desktop\release_preflight_step51.json"
    ) `
    --release-manifest-output (
        Join-Path $ProjectRoot `
            "reports\release\release_manifest_step51.json"
    )

if ($LASTEXITCODE -ne 0) {
    throw "Post-build release verification failed."
}

Write-Host ""
Write-Host "Installer build completed."
Write-Host "Output: $(Join-Path $Frontend 'release')"
