param(
    [string]$Python = "python",
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "powershell_compat.ps1")

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Spec = Join-Path $ProjectRoot "backend\packaging\evil-twin-backend.spec"
$Manifest = Join-Path $ProjectRoot "backend\packaging\runtime_manifest.py"
$Dist = Join-Path $ProjectRoot "build\backend\dist"
$Work = Join-Path $ProjectRoot "build\backend\work"
$ElectronBackend = Join-Path $ProjectRoot "frontend\resources\backend"

Assert-EvilTwinWindowsHost -Message "O build de produção do backend deve ser executado no Windows."

Write-Host "Evil Twin Detector - backend production build"
Write-Host ""


if (-not $SkipDependencyInstall) {
    & $Python -m pip install -r (
        Join-Path $ProjectRoot "requirements-packaging.txt"
    )
}

Write-Host "Validating packaging inputs..."

& $Python $Manifest `
    --project-root $ProjectRoot

if ($LASTEXITCODE -ne 0) {
    throw "Production build requires all four real scientific artifacts."
}

New-Item -ItemType Directory -Force -Path $Dist | Out-Null
New-Item -ItemType Directory -Force -Path $Work | Out-Null
New-Item -ItemType Directory -Force -Path $ElectronBackend | Out-Null

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --distpath $Dist `
    --workpath $Work `
    $Spec

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

$Exe = Join-Path $Dist "evil-twin-backend.exe"

if (-not (Test-Path $Exe)) {
    throw "Expected executable not found: $Exe"
}

$Target = Join-Path $ElectronBackend "evil-twin-backend.exe"

Copy-Item -Force $Exe $Target

$Hash = Get-FileHash `
    -Algorithm SHA256 `
    $Target

Write-Host ""
Write-Host "Backend packaged successfully."
Write-Host "Electron resource: $Target"
Write-Host "SHA256: $($Hash.Hash)"
