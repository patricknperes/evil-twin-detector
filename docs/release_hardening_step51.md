# Fase 4 — Passo 51: hardening de release

## PowerShell

Os scripts Windows não dependem mais de `$IsWindows`.

Esse identificador é uma variável automática do PowerShell moderno e não
existe da mesma forma no Windows PowerShell 5.1.

O contrato compartilhado agora é:

```powershell
. (Join-Path $PSScriptRoot "powershell_compat.ps1")
Assert-EvilTwinWindowsHost
```

A detecção usa:

```text
System.Environment.OSVersion.Platform == Win32NT
```

e funciona tanto no Windows PowerShell 5.1 quanto no PowerShell 7+.

A execução real nesses dois shells não foi realizada neste ambiente Linux;
a compatibilidade foi endurecida e coberta por testes de contrato de fonte.

## Release preflight

Comando:

```powershell
.\scripts\validate_release_preflight.ps1 -Target inputs
```

Targets:

```text
inputs
installer
verify
```

### inputs

Exige que estejam READY:

```text
código acumulado
integração determinística
host Windows
sessões normais reais
scientific preflight
freeze/referência
ML-ready/scaler/lineage
OCSVM/threshold
ataque controlado real
features do ataque
avaliação final fixa
bundle final agregado do TCC
contrato estrutural frontend
Vitest/typecheck/Vite real
Playwright/Electron E2E real
```

### installer

Além de todos os itens acima exige:

```text
frontend/dist/index.html
frontend/resources/backend/evil-twin-backend.exe
contrato electron-builder/NSIS íntegro
```

O `npm run dist:win` só é chamado depois desse gate.

### verify

Depois do electron-builder, exige o instalador da versão atual e valida o
estado pós-build.

Quando estiver READY, gera:

```text
reports/release/release_manifest_step51.json
```

com SHA-256 do instalador, backend empacotado, `dist/index.html`, artefatos
científicos e manifesto dos resultados finais.

Code signing continua opcional para a execução científica do TCC e não é
simulado.
