# Frontend scan page

Fluxo visual:

```text
preflight
  ↓
POST /scan
  ↓
loading sem percentual artificial
  ↓
resultado ou erro específico
  ↓
summary + filtros + busca
  ↓
detalhe técnico por rede
```

A tela usa o contrato científico já existente e não retreina/recalibra nenhum artefato.
