param(
    [Parameter(Mandatory=$true)]
    [string]$Environment,

    [string]$Python = "python",

    [int]$Scans = 30,

    [double]$IntervalSeconds = 6.0,

    [double]$WaitSeconds = 4.2,

    [string]$InterfaceGuid = ""
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "powershell_compat.ps1")

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$OutputRoot = Join-Path $ProjectRoot "data\raw\own\windows"

Assert-EvilTwinWindowsHost -Message (
    "A coleta Native Wi-Fi deve ser executada no Windows 10/11."
)

Set-Location $ProjectRoot

$ArgsList = @(
    "-m",
    "desktop.windows.normal_collection",
    "--environment",
    $Environment,
    "--output-root",
    $OutputRoot,
    "--scans",
    $Scans,
    "--interval-seconds",
    $IntervalSeconds,
    "--wait-seconds",
    $WaitSeconds
)

if ($InterfaceGuid -ne "") {
    $ArgsList += @(
        "--interface-guid",
        $InterfaceGuid
    )
}

Write-Host ""
Write-Host "Coleta NORMAL - desktop_candidate_v1"
Write-Host "Ambiente/coorte: $Environment"
Write-Host "Scans: $Scans"
Write-Host "Identificadores Wi-Fi em claro: NÃO"
Write-Host ""
Write-Host "IMPORTANTE: mantenha o mesmo rótulo de ambiente nas sessões da mesma coorte."
Write-Host "Execute somente em condição NORMAL, sem anomalia/ataque controlado ativo."
Write-Host ""

& $Python @ArgsList
exit $LASTEXITCODE
