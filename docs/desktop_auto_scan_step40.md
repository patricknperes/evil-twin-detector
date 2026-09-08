# Scheduler automático do desktop

Preferências utilizadas:

```text
auto_scan_enabled
auto_scan_interval_seconds
high_anomaly_notifications
```

O JavaScript não implementa scanner ou inferência próprios. O Electron chama
o FastAPI local e recebe a decisão científica já produzida pelo bundle
congelado.

## IPC do renderer

O preload expõe apenas:

```text
getAutoScanSchedulerStatus()
refreshAutoScanScheduler()
onAutoScanCompleted(callback)
```

Não expõe spawn, Notification ou shell arbitrário.

## Privacidade

As notificações só mostram a quantidade de novas redes de alta suspeita.

Clicar na notificação apenas restaura e focaliza a janela do aplicativo.
