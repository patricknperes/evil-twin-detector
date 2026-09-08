param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot

Set-Location $ProjectRoot

Write-Host ""
Write-Host "Evil Twin Detector - final execution readiness"
Write-Host ""

& $Python -m desktop.final_readiness `
    --project-root $ProjectRoot `
    --json-output (
        Join-Path $ProjectRoot `
            "reports\desktop\final_execution_readiness_step46.json"
    ) `
    --markdown-output (
        Join-Path $ProjectRoot `
            "reports\desktop\final_execution_readiness_step46.md"
    )

$Code = $LASTEXITCODE

Write-Host ""

if ($Code -eq 0) {
    Write-Host "Todos os gates obrigatórios estão concluídos."
    exit 0
}

if ($Code -eq 8) {
    Write-Host "Existem gates bloqueados. Consulte o relatório gerado."
    exit 8
}

Write-Host "Não há bloqueios estruturais, mas ainda existem etapas não executadas."
exit $Code
