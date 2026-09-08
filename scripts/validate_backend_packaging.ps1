param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot

& $Python (
    Join-Path $ProjectRoot "backend\packaging\runtime_manifest.py"
) `
    --project-root $ProjectRoot `
    --allow-missing-scientific-artifacts

if ($LASTEXITCODE -ne 0) {
    throw "Backend packaging structure is invalid."
}
