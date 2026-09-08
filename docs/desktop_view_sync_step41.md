# Sincronização após scan automático

Dashboard e Redes observadas escutam `desktop:auto-scan-completed` através do preload seguro do Electron.

Não usam `setInterval`, `location.reload` ou um segundo scanner no renderer. Cada tela consulta somente seus próprios endpoints após o evento.

O listener IPC é removido quando a rota é desmontada.
