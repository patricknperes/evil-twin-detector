# Avaliação final do desktop_candidate_v1

O protocolo final segue:

```text
normal reference (frozen)
model_train -> scaler + OCSVM
validation normal -> threshold
test_normal -> independent normal evaluation
controlled real attack -> attack evaluation
```

A etapa final é exclusivamente leitura de artefatos congelados.

Isso permite reportar desempenho sem adaptar o modelo ao conjunto de ataque.

## Matriz de confusão

Convenção:

```text
label 0 = normal
label 1 = controlled attack

prediction 0 = normal
prediction 1 = anomaly
```

Logo:

- FP = normal classificado como anômalo;
- FN = ataque não detectado.

Para o contexto de detecção de possível Evil Twin, FN é especialmente
importante porque representa um ataque controlado que o sistema não sinalizou.
