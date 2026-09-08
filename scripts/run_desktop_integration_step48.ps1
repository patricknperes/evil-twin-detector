param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot

Set-Location $ProjectRoot

& $Python -m desktop.integration.run_step48 `
    --project-root $ProjectRoot `
    --output (
        Join-Path $ProjectRoot `
            "reports\desktop\desktop_integration_step48.json"
    )

exit $LASTEXITCODE
