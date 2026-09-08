# Runtime inference — desktop_candidate_v1

O runtime é estritamente read-only em relação aos artefatos científicos.

Operações permitidas:

```text
reference lookup
scaler.transform
model.decision_function
threshold comparison
```

Operações proibidas:

```text
reference update
scaler.fit
scaler.partial_fit
model.fit
threshold recalibration
```

## Fluxo de persistência

```text
ScanSession
└── NetworkObservation
    ├── NetworkFeatures
    └── Detection
        └── ModelVersion
```

O `ModelVersion` registra hashes do conjunto de artefatos congelados.

## Falta de histórico

Uma rede sem contexto suficiente recebe um registro auditável de
`insufficient_history`, mas sem score e sem decisão binária de ataque.

Isso é diferente de um falso positivo e deve permanecer separado nas métricas
e na UX.
