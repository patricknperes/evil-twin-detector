# Fase 4 — Passo 44: pré-flight científico e freeze de integridade

Antes de qualquer referência, scaler ou OCSVM desktop, as sessões reais
`own_windows` passam por um gate obrigatório.

## Sessão válida

Uma sessão precisa satisfazer:

```text
source_dataset = own_windows
label = 0
attack_present = false
attack_type = null
is_synthetic = false
runtime_ready = true
session_id da pasta = manifest = linhas
sem colunas SSID/BSSID em claro
hashes SSID/BSSID em SHA-256 quando presentes
BSSID hash coverage >= 0.99
desktop_candidate_v1 completeness >= 0.70
source_scans_sha256 válido
interim_observations_sha256 válido e rechecado
```

## Duplicidade

Existe um fingerprint canônico do conteúdo das observações, ignorando apenas
`session_id` e `environment`.

Duas pastas com o mesmo conteúdo capturado são bloqueadas, mesmo se possuírem
IDs diferentes.

## Temporalidade e ambientes

O relatório registra contagem de sessões por `environment`.

Sobreposição temporal entre sessões é `warning`, não bloqueio automático.

## Split

Mínimo:

```text
1 reference
2 model_train
1 validation
1 test_normal
```

A unidade é `session_id`. Não há split aleatório por observação.

## Freeze

Quando o plano chega a `ready`, são materializados:

```text
session_split_plan.json
scientific_freeze.json
desktop_normal_reference.json
preparation_manifest.json
```

O freeze registra:

```text
split_digest
SHA-256 do arquivo do split
source_scans_sha256 por sessão
observations_sha256 por sessão
content_fingerprint por sessão
```

Depois disso:

```text
alterar sessão congelada → BLOCK
alterar split congelado → BLOCK
remover sessão congelada → BLOCK
adicionar nova sessão → detectada, mas NÃO atribuída automaticamente
```

Uma mudança deliberada de protocolo exige nova versão/novo diretório, em vez
de sobrescrever o freeze anterior.

## Gate para ML

`prepare_desktop_ml` agora verifica a cadeia:

```text
split plan
→ scientific freeze
→ reference
→ preparation manifest
```

antes de ajustar `StandardScaler`.


## Hardening do Passo 52

Antes do primeiro freeze real foram adicionados dois gates adicionais:

```text
normal cohort environments = 1
candidate reference eligible rate >= 0.70
```

O segundo gate é calculado em dry-run usando exatamente o split determinístico
que seria congelado. `model_train`, `validation` e `test_normal` precisam manter
pelo menos 70% de linhas com contexto e as quatro features completas.

Isso evita descobrir somente depois do freeze que a sessão de referência não
cobre as redes observadas nas demais sessões.
