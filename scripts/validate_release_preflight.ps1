param(
    [string]$Python = "python",
    [ValidateSet("inputs", "installer", "verify")]
    [string]$Target = "inputs"
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "powershell_compat.ps1")

$ProjectRoot = Split-Path -Parent $PSScriptRoot

Assert-EvilTwinWindowsHost -Message (
    "O release preflight estrito deve ser executado no host Windows de release."
)

Set-Location $ProjectRoot

& $Python -m desktop.release_preflight `
    --project-root $ProjectRoot `
    --target $Target `
    --json-output (
        Join-Path $ProjectRoot `
            "reports\desktop\release_preflight_step51.json"
    ) `
    --release-manifest-output (
        Join-Path $ProjectRoot `
            "reports\release\release_manifest_step51.json"
    )

exit $LASTEXITCODE
