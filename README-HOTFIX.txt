PASSO 53 - Compatibilidade com Windows PowerShell 5.1

Substitua APENAS:
1. scripts\powershell_compat.ps1
2. reports\implementation\implementation_snapshot_step52.json

Depois rode:
python -m desktop.implementation_freeze `
    --project-root . `
    --snapshot reports/implementation/implementation_snapshot_step52.json

Em seguida, se retornar ready=true:
.\scripts\check_windows_collection_readiness.ps1
