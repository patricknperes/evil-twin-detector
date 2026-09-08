# Fase 4 — Passo 49: E2E do renderer/Electron

A suíte foi implementada com Playwright + Electron.

```text
frontend/playwright.config.ts
frontend/e2e/desktop.e2e.ts
frontend/e2e/support/fake-backend.ts
```

Execução:

```powershell
.\scripts\validate_renderer_e2e.ps1
```

ou, depois das dependências instaladas:

```bash
cd frontend
npm run e2e
```

## Cenários

```text
navegação por todas as telas
modelo não pronto
scanner indisponível
scan manual sem modelo
persistência refletida no Histórico
scan automático passando pelo Electron main
refresh do Dashboard via IPC
backend offline
backend recuperado sem reload
download local do diagnóstico
privacidade do bundle exportado
```

## Fixture E2E

A suíte usa um backend HTTP determinístico em `127.0.0.1:18765`.

Ele existe somente para validar o contrato de interface. Dados como
`E2E-Test-Network` não são dados científicos e nunca entram nos relatórios ou
métricas do TCC.

A execução E2E não chama Native Wi-Fi e não lê artefatos científicos reais.

## Segurança

O IPC `desktop:e2e-run-auto-scan` só é registrado quando:

```text
EVIL_TWIN_E2E=1
```

Em produção ele não existe.

O E2E também desabilita a criação de notificações reais do sistema operacional.

## Dependências

A execução requer `@playwright/test`, `playwright`, `electron`, Vite e as demais
dependências do frontend instaladas.

Enquanto o registry npm não estiver acessível e `node_modules` não existir, o
estado correto permanece `NOT EXECUTED`.
