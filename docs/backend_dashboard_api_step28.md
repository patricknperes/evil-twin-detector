# Dashboard API

## Overview

```http
GET /dashboard/overview
```

Parâmetros opcionais:

```text
recent_scans=5
recent_detections=5
```

O frontend poderá montar cards de KPI, status do sistema, atividade recente e
distribuição de suspeita a partir de uma única requisição.

## Trends

```http
GET /dashboard/trends?limit=30
```

Retorna série temporal por scan, já ordenada do mais antigo para o mais novo
dentro da janela solicitada.

## Interpretação

`high` significa uma observação acima do threshold de anomalia. Não significa
"Evil Twin confirmado".

`unavailable` inclui principalmente contexto normal insuficiente e deve ser
visualizado separadamente de normal/anômalo.
