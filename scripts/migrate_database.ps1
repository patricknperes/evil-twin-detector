param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "Applying local database migrations..."
& $Python -m alembic upgrade head
exit $LASTEXITCODE
