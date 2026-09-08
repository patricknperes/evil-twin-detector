param(
    [string]$Python = "python",
    [string]$Output = "reports/desktop/windows_scan_diagnostic.json",
    [switch]$IncludeIdentifiers,
    [switch]$NoScan
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "powershell_compat.ps1")

$ProjectRoot = Split-Path -Parent $PSScriptRoot

Assert-EvilTwinWindowsHost -Message (
    "O diagnóstico Native Wi-Fi deve ser executado no Windows."
)

Set-Location $ProjectRoot

$OutputPath = $Output

if (-not [System.IO.Path]::IsPathRooted($OutputPath)) {
    $OutputPath = Join-Path $ProjectRoot $OutputPath
}

$Arguments = @(
    "-m",
    "desktop.windows.diagnostic",
    "--json",
    $OutputPath
)

# Privacy-safe default. Clear SSID/BSSID must be explicitly requested.
if (-not $IncludeIdentifiers) {
    $Arguments += "--redact-identifiers"
}

if ($NoScan) {
    $Arguments += "--no-scan"
}

Write-Host "Executando diagnóstico Native Wi-Fi..."
Write-Host "Identificadores em claro: $([bool]$IncludeIdentifiers)"

& $Python @Arguments
$ExitCode = $LASTEXITCODE

Write-Host "Exit code: $ExitCode"
Write-Host "Resultado: $OutputPath"

if ($ExitCode -eq 3) {
    Write-Host "Acesso de localização/Wi-Fi negado pelo Windows."
    Write-Host "Abra: ms-settings:privacy-location"
}

exit $ExitCode
