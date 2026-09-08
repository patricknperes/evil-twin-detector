param(
    [Parameter(Mandatory=$true)]
    [ValidateSet(
        "controlled_evil_twin",
        "controlled_security_downgrade",
        "controlled_bssid_change",
        "controlled_channel_change",
        "controlled_tsf_reset_observation",
        "other_authorized_wifi_anomaly"
    )]
    [string]$Scenario,

    [Parameter(Mandatory=$true)]
    [string]$Environment,

    [Parameter(Mandatory=$true)]
    [string]$AuthorizationNote,

    [string]$Python = "python",

    [int]$Scans = 30,

    [double]$IntervalSeconds = 6.0,

    [double]$WaitSeconds = 4.2,

    [string]$InterfaceGuid = ""
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "powershell_compat.ps1")

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$OutputRoot = Join-Path $ProjectRoot "data\raw\own\windows_attack"

Assert-EvilTwinWindowsHost -Message (
    "A observação do experimento controlado deve ser executada no Windows."
)

Set-Location $ProjectRoot

$Arguments = @(
    "-m",
    "desktop.windows.controlled_attack_collection",
    "--scenario",
    $Scenario,
    "--environment",
    $Environment,
    "--authorization-note",
    $AuthorizationNote,
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
    $Arguments += @(
        "--interface-guid",
        $InterfaceGuid
    )
}

Write-Host ""
Write-Host "Controlled Wi-Fi experiment observer"
Write-Host "Ambiente/coorte: $Environment"
Write-Host "Identificadores Wi-Fi em claro: NÃO"
Write-Host "Este script somente coleta observações."
Write-Host "Ele não cria nem configura um rogue AP."
Write-Host ""

& $Python @Arguments
exit $LASTEXITCODE
