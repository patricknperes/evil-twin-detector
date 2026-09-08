# Desktop backend lifecycle

## Development

Execute o frontend Electron normalmente:

```powershell
.\scripts\run_desktop_dev.ps1
```

O Electron verifica `http://127.0.0.1:8765/health`. Se necessário, inicia:

```text
python -m backend
```

É possível escolher outro Python com:

```text
EVIL_TWIN_PYTHON
```

## Production contract

O processo principal procura:

```text
<resources>/backend/evil-twin-backend.exe
```

A criação desse executável será realizada em um passo posterior com PyInstaller.

## Overrides de diagnóstico

```text
EVIL_TWIN_BACKEND_URL
EVIL_TWIN_BACKEND_EXECUTABLE
EVIL_TWIN_BACKEND_STARTUP_TIMEOUT_MS
EVIL_TWIN_PYTHON
```

Esses overrides pertencem ao ambiente/processo desktop; não são campos
editáveis pela API `/settings`.
