param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "powershell_compat.ps1")

$ProjectRoot = Split-Path -Parent $PSScriptRoot

Assert-EvilTwinWindowsHost -Message (
    "A checagem de coleta precisa ser executada no computador Windows que fará a coleta."
)

Set-Location $ProjectRoot

& $Python -m desktop.windows.collection_readiness `
    --project-root $ProjectRoot `
    --probe-native-wifi `
    --output (
        Join-Path $ProjectRoot `
            "reports\desktop\windows_collection_readiness_step52.json"
    )

exit $LASTEXITCODE
