param(
    [string]$Python = "python",
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "powershell_compat.ps1")

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $ProjectRoot "frontend"

Assert-EvilTwinWindowsHost -Message (
    "O build desktop Windows deve ser executado em um host Windows."
)

Set-Location $ProjectRoot

& (
    Join-Path $ProjectRoot "scripts\validate_frontend_toolchain.ps1"
) `
    -Python $Python `
    -SkipInstall:$SkipDependencyInstall

if ($LASTEXITCODE -ne 0) {
    throw "Frontend dependency-resolved validation failed."
}

& (
    Join-Path $ProjectRoot "scripts\validate_renderer_e2e.ps1"
) `
    -Python $Python `
    -SkipInstall:$SkipDependencyInstall

if ($LASTEXITCODE -ne 0) {
    throw "Renderer/Electron E2E validation failed."
}

& (
    Join-Path $ProjectRoot "scripts\build_backend_windows.ps1"
) `
    -Python $Python `
    -SkipDependencyInstall:$SkipDependencyInstall

if ($LASTEXITCODE -ne 0) {
    throw "Backend build failed."
}

& $Python -m desktop.release_preflight `
    --project-root $ProjectRoot `
    --target installer `
    --json-output (
        Join-Path $ProjectRoot `
            "reports\desktop\release_preflight_step51.json"
    )

if ($LASTEXITCODE -ne 0) {
    throw "Release preflight blocked the unpacked desktop build."
}

Set-Location $Frontend

npm run dist:win:dir

if ($LASTEXITCODE -ne 0) {
    throw "electron-builder unpacked build failed."
}
