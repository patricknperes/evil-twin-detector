# Instalador Windows

Validação estrutural:

```powershell
.\scripts\validate_desktop_packaging.ps1
```

Build unpacked:

```powershell
.\scripts\build_desktop_unpacked_windows.ps1
```

Build NSIS:

```powershell
.\scripts\build_desktop_installer_windows.ps1
```

Saída esperada:

```text
frontend/release/
```

O instalador final só será produzido quando os artefatos científicos e o
backend PyInstaller real estiverem disponíveis.
