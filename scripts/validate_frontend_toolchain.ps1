param(
    [string]$Python = "python",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Args = @(
    "scripts/frontend_toolchain.py",
    "--project-root", $ProjectRoot,
    "--probe-registry",
    "--output", (Join-Path $ProjectRoot "reports/frontend/frontend_toolchain_step47.json")
)

if (-not $SkipInstall) {
    $Args += "--install"
}

& $Python @Args
exit $LASTEXITCODE
