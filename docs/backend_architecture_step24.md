# Backend local

Arquitetura inicial:

```text
Future Electron
    ↓ localhost HTTP
FastAPI :8765
    ↓
ScannerService
    ↓
NativeWifiScanner
    ↓
wlanapi.dll
```

O carregamento da API nativa é lazy.

Neste passo a última varredura fica apenas em memória. A persistência entra no
passo seguinte.
