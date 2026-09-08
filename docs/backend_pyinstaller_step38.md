# Backend PyInstaller

Validação estrutural:

```powershell
.\scripts\validate_backend_packaging.ps1
```

Build final no Windows, depois de existirem os quatro artefatos reais:

```powershell
.\scripts\build_backend_windows.ps1
```

O build valida os inputs, executa PyInstaller, copia o executável para os
recursos do Electron e calcula SHA-256.

A instalação não grava SQLite em `Program Files`.
