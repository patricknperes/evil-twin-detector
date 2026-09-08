# Persistência local

```text
POST /scan
   ↓
ScanResponse
   ├── RuntimeStore: SSID/BSSID em claro, memória
   └── SQLite
       ├── scan_session
       └── network_observation: hashes + medições
```

Tabelas reservadas para o próximo passo:

- `network_features`
- `detection`
- `model_version`
