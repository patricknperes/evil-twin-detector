# Fase 4 — Passo 50: geração dos resultados finais do TCC

Comando:

```powershell
.\scripts\generate_final_tcc_results.ps1
```

ou:

```bash
python -m desktop.windows.generate_final_tcc_results
```

A pipeline só executa quando existir:

```text
reports/desktop/final_evaluation_v1/
├── final_evaluation.json
├── test_normal_scores.csv.gz
├── attack_scores.csv.gz
├── recall_by_attack_type.csv
└── recall_by_attack_session.csv
```

e `final_evaluation.json` declarar:

```text
schema_version = desktop_final_evaluation_v2
status = executed_fixed_artifacts
evaluation_executed = true
artifacts_modified = false
```

## Verificação antes da geração

O Passo 50 recalcula:

```text
accuracy
precision
recall
F1
ROC-AUC
PR-AUC
FPR
FNR
matriz de confusão
test-normal FPR
attack recall
```

diretamente dos score files.

Esses valores precisam coincidir com `final_evaluation.json`.

Também são rechecados:

```text
SHA-256 da referência
SHA-256 do scaler
SHA-256 do OCSVM
SHA-256 do threshold
prediction = score > threshold
recall por attack_type
recall por session_id
```

Qualquer divergência bloqueia o bundle.

## Saída real

Somente quando o gate passar:

```text
reports/tcc/final_results_v1/
├── metrics_summary.csv
├── confusion_matrix.csv
├── roc_curve.csv
├── precision_recall_curve.csv
├── score_distribution.csv
├── recall_by_attack_type.csv
├── recall_by_attack_session.csv
├── timing_summary.csv
├── confusion_matrix.png
├── roc_curve.png
├── precision_recall_curve.png
├── score_distribution.png
├── final_results_summary.md
└── reproducibility_manifest.json
```

A pasta é create-only. Uma execução posterior não sobrescreve silenciosamente
um resultado final anterior.

## Privacidade

O bundle é agregado. `test_normal_scores.csv.gz` e `attack_scores.csv.gz` são
fontes de verificação, mas não são copiados para `reports/tcc/final_results_v1`.

Assim, o bundle final não inclui:

```text
SSID
BSSID
ssid_hash
bssid_hash
interface_guid
observações individuais
```

## Interpretação

As métricas medem o protocolo congelado do experimento. Uma detecção anômala
não é, isoladamente, confirmação de um Evil Twin em uma rede de produção.

Os tempos registrados pela avaliação são de inferência do modelo. A latência
end-to-end do Native Wi-Fi deve ser reportada separadamente.
