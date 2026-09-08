# Pipeline de importação das coletas Windows

Fluxo:

```text
RAW SESSION
→ integridade
→ revalidação runtime
→ INTERIM OBSERVATIONS
→ frozen normal reference
→ desktop_candidate_v1 features
→ ML
```

A camada interim preserva `session_id` e hashes estáveis, mas não copia
identificadores em claro.

A unidade de split futuro continua sendo `session_id`.
