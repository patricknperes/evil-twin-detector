# Frontend Dashboard — Passo 31

## Fonte de dados

O dashboard não calcula métricas científicas no React. Ele apenas apresenta os
agregados produzidos pelo backend:

```text
/dashboard/overview
/dashboard/trends
```

Isso mantém a lógica de contagem e decisão no backend auditável.

## Gráficos

Recharts é usado para:

- evolução por scan (`network_count` e `detection_count`);
- distribuição histórica de níveis de suspeita.

Os gráficos possuem estado vazio quando ainda não há dados persistidos.

## Terminologia

A interface usa "anomalia", "suspeita" e "histórico insuficiente". Não existe
uma indicação de "rede segura" nem de "Evil Twin confirmado".
