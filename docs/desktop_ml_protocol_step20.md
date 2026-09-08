# Protocolo ML do desktop_candidate_v1

## Pipeline congelado

```text
real Windows normal sessions
→ import
→ session-level split
→ frozen reference
→ desktop features
→ X/y/metadata
→ StandardScaler fit only model_train
→ OneClassSVM
→ P95 validation-normal threshold
→ test_normal
→ future controlled real Evil Twin test
```

## Separação de dados

A sessão de `reference` não é treino do OCSVM.

Ela existe apenas para construir o histórico contextual.

O OCSVM recebe apenas `model_train`.

A validação calibra apenas o threshold.

O `test_normal` mede falsos positivos fora da calibração.

Um futuro ataque real controlado será utilizado somente para avaliação final,
nunca para ajustar o threshold.

## Não reutilizar artefatos antigos

O desktop não reutiliza diretamente:

- modelo do `contextual_core_v2`;
- scaler do `contextual_core_v2`;
- threshold do Mendeley;
- resultados sintéticos como calibração.

A razão é mudança de domínio e de semântica das features produzidas pelo scanner
Windows.
