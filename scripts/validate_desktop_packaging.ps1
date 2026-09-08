param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot

& $Python (
    Join-Path $ProjectRoot "desktop\packaging\preflight.py"
) `
    --project-root $ProjectRoot `
    --allow-missing-build-products

if ($LASTEXITCODE -ne 0) {
    throw "Desktop packaging structure is invalid."
}
