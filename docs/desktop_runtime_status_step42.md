# Estado global de runtime

Provider: `frontend/src/contexts/RuntimeStatusContext.tsx`.

Fontes:
```text
GET /health
GET /settings
IPC getAutoScanSchedulerStatus()
```

A atualização do serviço local é centralizada. Dashboard e Redes continuam orientados por evento de scan e não ganham polling próprio.
