# API de histórico

A camada de histórico é somente leitura sobre o SQLite.

## Scans

```http
GET /history/scans?limit=25&offset=0
GET /history/scans/{scan_id}
GET /history/scans/{scan_id}/observations
```

## Detecções

```http
GET /history/detections
GET /history/detections/{detection_id}
```

Filtros opcionais: `is_anomaly`, `suspicion_level` e `model_version_id`.

## Modelos

```http
GET /history/models
GET /history/models/{model_version_id}
```

## Privacidade

A API de histórico nunca devolve SSID, BSSID ou GUID de interface em claro. Ela
expõe somente os hashes persistidos e dados técnicos necessários à auditoria.
