# Application Settings API

## Leitura

```http
GET /settings
```

Retorna:

```text
values
constraints
model_status
missing_model_artifacts
scientific_policy
```

## Alteração

```http
PATCH /settings
```

Somente preferências do produto são aceitas.

## Reset

```http
POST /settings/reset
```

Restaura os defaults do projeto.

## Resolução de scan

```text
valor explícito no POST /scan
        ↓ se ausente
ApplicationSettings
        ↓
ScannerService
```

## Limites científicos

As configurações da aplicação não possuem nenhum campo que permita retreinar,
recalibrar ou trocar os caminhos da referência/scaler/model/threshold.
