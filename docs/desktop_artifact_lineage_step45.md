# Fase 4 — Passo 45: cadeia de integridade dos artefatos desktop

O objetivo deste passo é impedir que arquivos produzidos por freezes científicos
diferentes sejam combinados acidentalmente.

## Identidade científica

A cadeia usa:

```text
split_digest
scientific_freeze_sha256
reference_file_sha256
```

O `reference_file_sha256` não é armazenado dentro da própria referência, pois
isso criaria uma autorreferência impossível. Ele é calculado depois que
`desktop_normal_reference.json` é materializado e passa a ser carregado pelos
artefatos subsequentes.

## Scaler e matrizes

Depois do `StandardScaler.fit(model_train)`, o Passo 20 cria:

```text
data/processed/ml_ready/desktop_candidate_v1_scaled/
└── artifact_lineage.json
```

Esse arquivo registra:

```text
SHA-256 do scaler.joblib
SHA-256 do metadata JSON do scaler

model_train/
  X.csv.gz
  y.csv.gz
  metadata.csv.gz

validation/
  X.csv.gz
  y.csv.gz
  metadata.csv.gz

test_normal/
  X.csv.gz
  y.csv.gz
  metadata.csv.gz
```

O treinamento do OCSVM só inicia quando todos esses hashes são recalculados e
coincidem.

## Modelo e threshold

Após o OCSVM ser treinado, o SHA-256 do binário do modelo é calculado.

O threshold passa a usar:

```text
desktop_threshold_v2
```

e contém:

```text
split_digest
scientific_freeze_sha256
reference_file_sha256
scaler_file_sha256
model_file_sha256
artifact_lineage_file_sha256
```

Assim, `threshold.json` funciona como o elo de runtime entre os quatro arquivos
do produto.

Ele não armazena seu próprio SHA-256 dentro de si; o SHA do threshold é
calculado externamente quando necessário.

## Runtime

O contrato de runtime continua com exatamente quatro artefatos:

```text
desktop_normal_reference.json
desktop_candidate_v1_standard_scaler.joblib
one_class_svm_desktop_candidate_v1.joblib
threshold.json
```

Antes de carregar o scaler/modelo, o backend verifica:

```text
reference real SHA == threshold.reference_file_sha256
scaler real SHA    == threshold.scaler_file_sha256
model real SHA     == threshold.model_file_sha256

reference.split_digest == threshold.split_digest
reference.scientific_freeze_sha256 == threshold.scientific_freeze_sha256
```

Uma inconsistência faz o modelo ficar `not_ready`; inferência não ocorre.

## Avaliação final

A avaliação final verifica simultaneamente:

```text
artifact_lineage.json
reference
scaler
model
threshold
manifest das features de ataque
```

O manifest de ataque registra a referência usada para gerar as features. Se as
features de ataque foram derivadas de outra referência, a avaliação é
bloqueada.

Os hashes dos quatro artefatos congelados são calculados antes e depois da
avaliação para garantir que a avaliação não os modificou.
