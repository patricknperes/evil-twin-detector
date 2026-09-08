# Fase 4 — Passo 48: integração determinística do desktop

Comando:

```bash
python -m desktop.integration.run_step48
```

ou no Windows:

```powershell
.\scripts\run_desktop_integration_step48.ps1
```

O harness não usa Wi-Fi real, não carrega o bundle científico real e não cria
métricas finais. Ele testa contratos de integração que podem ser executados de
forma determinística em CI/desenvolvimento.

## Backend

Cenários:

```text
backend online + banco pronto + modelo not_ready
scanner unsupported -> HTTP 501
permissão de localização negada -> HTTP 403
scan manual bem-sucedido com modelo ausente
  -> analysis.status = not_available
  -> is_anomaly = null
  -> persistência SQLite
  -> /networks
  -> /history/scans
  -> /diagnostics/support-bundle
```

A ausência do modelo nunca é convertida em “normal”.

## Electron / scheduler

O teste Node usa um servidor HTTP local real e o `fetch` real do Node, sem
mockar a função de transporte.

Fluxo exercitado:

```text
backend offline
-> settings_error

backend sobe no mesmo endereço
-> recuperação
-> scan automático
-> evento de conclusão
-> nova alta suspeita gera 1 notificação lógica

mesma rede continua HIGH
-> não gera spam

POST /scan retorna 409 scan_in_progress
-> scheduler pula o ciclo sem falha fatal

backend cai novamente
-> settings_error
```

Nenhuma notificação real do sistema operacional é exibida nesse teste.

## O que continua pendente

```text
Native Wi-Fi real no Windows
bundle científico real
renderer E2E com dependências npm resolvidas
notificação real do Windows
PyInstaller
NSIS
```
