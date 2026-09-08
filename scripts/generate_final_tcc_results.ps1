param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot

Set-Location $ProjectRoot

Write-Host ""
Write-Host "Evil Twin Detector - resultados finais do TCC"
Write-Host ""

& $Python -m desktop.windows.generate_final_tcc_results `
    --project-root $ProjectRoot `
    --evaluation-dir (
        Join-Path $ProjectRoot `
            "reports\desktop\final_evaluation_v1"
    ) `
    --output-dir (
        Join-Path $ProjectRoot `
            "reports\tcc\final_results_v1"
    ) `
    --status-output (
        Join-Path $ProjectRoot `
            "reports\desktop\final_results_step50.json"
    )

exit $LASTEXITCODE
