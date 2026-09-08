param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "Starting backend at http://127.0.0.1:8765"

& $Python -m backend `
    --host 127.0.0.1 `
    --port 8765

exit $LASTEXITCODE
