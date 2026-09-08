# Tela Histórico

Fonte de dados:

```http
GET /history/scans
GET /history/scans/{scan_id}
GET /history/detections
GET /history/detections/{detection_id}
GET /history/models
GET /history/models/{model_version_id}
```

O histórico é somente leitura.

A interface usa hashes persistidos para auditoria e nunca apresenta SSID,
BSSID ou GUID da interface em claro.

A navegação de auditoria permite seguir uma decisão até o bundle científico
que a produziu.
