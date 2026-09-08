# Treino normal do One-Class SVM desktop

Pipeline:

```text
desktop_candidate_v1_scaled/model_train
→ fit OneClassSVM

desktop_candidate_v1_scaled/validation
→ anomaly scores
→ P95 threshold

desktop_candidate_v1_scaled/test_normal
→ FPR fora da calibração
```

Neste estágio não há recall/F1 de ataque.

Essas métricas só são válidas após um conjunto de ataque controlado separado.

O módulo preserva explicitamente essa separação para evitar que dados de ataque
influenciem scaler, modelo ou threshold.
