# Evil Twin Detector — TCC II

Versão acumulada até a **Fase 2 — Passo 7**.

## Normalizadores implementados

1. **Mendeley Rogue AP**
2. **Wi-Fi V2I**
3. **Continuous Long-term Wi-Fi**
4. **802.11 Management Frames from a Public Location (Station)**

Todos produzem o mesmo schema canônico.

## Dependências

```bash
pip install -r requirements-ml.txt
```

---

## Mendeley

```bash
python -m ml.preprocessing.normalize_mendeley --input data/external/mendeley_rogue_ap --output data/interim/mendeley
```

Saídas:

```text
mendeley_normal.parquet
mendeley_attack.parquet
```

---

## V2I

```bash
python -m ml.preprocessing.normalize_v2i --input data/external/zenodo_v2i/wifi-exp-log-summary.csv --output data/interim/v2i
```

Saídas:

```text
v2i_all_normal.parquet
v2i_beacon_profile.parquet
v2i_desktop_aux.parquet
v2i_80211ad_aux.parquet
```

---

## Continuous Long-term Wi-Fi

```bash
python -m ml.preprocessing.normalize_longterm --input data/external/zenodo_longterm/UM_DSI_DB_v1.0.0_lite.zip --output data/interim/longterm
```

Também aceita o ZIP externo do Zenodo e pasta já extraída.

Saídas:

```text
longterm_all_normal.parquet
longterm_summary.json
```

---

## Station — 802.11 Management Frames

O normalizador aceita:

- pasta `datasets/` já extraída;
- `datasets.zip`;
- ZIP externo do Zenodo contendo `datasets.zip`.

Exemplo:

```bash
python -m ml.preprocessing.normalize_station --input data/external/zenodo_station/8003772.zip --output data/interim/station
```

Ou:

```bash
python -m ml.preprocessing.normalize_station --input data/external/zenodo_station/datasets.zip --output data/interim/station
```

Saídas:

```text
station_all_normal.parquet
station_beacons.parquet
station_ap_frames.parquet
station_summary.json
```

### Perfis

`station_all_normal.parquet`

Contém todos os frames:

```text
Beacon
Probe Request
Probe Response
```

`station_beacons.parquet`

Contém apenas Beacon frames.

`station_ap_frames.parquet`

Contém:

```text
Beacon
+
Probe Response
```

São os frames nos quais podemos associar um BSSID/AP com mais segurança.

### Dados preservados

- timestamp;
- tempo relativo da captura;
- RSSI;
- SSID anonimizado;
- BSSID anonimizado quando semanticamente seguro;
- endereço transmissor;
- endereço receptor;
- `MAC_timestamp` bruto;
- tipo do frame;
- sessão/captura;
- flags indicando anonimização.

Não inferimos canal, segurança ou beacon interval, pois essas informações não estão disponíveis no CSV fornecido.

Também não atribuímos BSSID a Probe Requests.

---

## Testes

```bash
pytest
```

---

## Regra de dados

```text
data/external/
    dados originais

data/interim/
    dados no schema canônico

data/processed/
    features prontas para ML
```

Os arquivos originais nunca são alterados.

## Próximo passo

Validar os **quatro normalizadores sobre os datasets reais**, gerar relatório de qualidade e definir quais perfis entram na etapa seguinte de Machine Learning.


---

# Fase 2 — Passo 8: validação e qualidade

Foi adicionado:

```text
ml/evaluation/dataset_quality_report.py
```

O script inspeciona os quatro datasets originais e gera:

```text
reports/
├── data_quality_report.json
└── data_quality_report.md
```

Exemplo:

```bash
python -m ml.evaluation.dataset_quality_report \
  --mendeley "data/external/mendeley_rogue_ap.zip" \
  --v2i "data/external/zenodo_v2i/6884095.zip" \
  --longterm "data/external/zenodo_longterm/6646008.zip" \
  --station "data/external/zenodo_station/8003772.zip" \
  --output reports
```

## Decisão resultante

Treino normal principal:

```text
Mendeley legítimo
+
V2I 802.11n beacon profile
+
dados próprios futuramente
```

Robustez/generalização:

```text
Long-term
+
Station
```

Ataques:

```text
Mendeley Rogue sintético (teste auxiliar)
+
Evil Twin próprio/controlado futuramente
```

Durante a validação também foi corrigido o mapeamento do V2I:

```text
802.11ad / 60.480 MHz -> canal 2
```

O 802.11ad continua separado do modelo desktop inicial.

## Próximo passo

Encerrar a Fase 2 criando o manifesto definitivo dos datasets e, em seguida,
iniciar a Fase 3 com EDA e definição dos perfis de features para os experimentos.


---

# Fase 2 — concluída

O manifesto definitivo está em:

```text
config/dataset_manifest.json
docs/dataset_manifest.md
```

Validação:

```bash
python -m ml.preprocessing.validate_dataset_manifest
```

A seleção oficial ficou:

```text
TREINO NORMAL
Mendeley legítimo
+ V2I 802.11n Beacon Profile
+ dados próprios (futuramente)

ROBUSTEZ
Long-term
+ Station

ATAQUES
Mendeley Rogue sintético (auxiliar)
+ Evil Twin próprio/controlado (principal)
```

A próxima fase é a **Fase 3 — EDA e análise individual dos datasets**.


---

# Fase 3 — Passo 1

Foi realizada a análise exploratória individual dos quatro datasets.

Resultados:

```text
reports/eda/
├── eda_summary.json
├── eda_summary.md
└── plots/
```

Validação:

```bash
python -m ml.evaluation.eda_step1
```

Principais conclusões:

- Mendeley permanece como a base principal ligada a Evil Twin.
- BeaconInterval do Mendeley possui baixa variabilidade nos dados normais.
- V2I 802.11n é o melhor perfil Beacon complementar.
- Long-term será usado com amostragem/agrupamento por sessão.
- Station será usado principalmente para robustez e falsos positivos.

Próximo passo: comparação das distribuições entre fontes e definição final
da compatibilidade de features.


---

# Fase 3 — Passo 2

Foi realizada a comparação semântica entre as features dos quatro datasets.

Relatórios:

```text
reports/eda/
├── cross_dataset_comparison.json
└── cross_dataset_comparison.md
```

Principais decisões:

```text
RSSI bruto
    ↓
não concatenar
    ↓
agregar por AP/janela
    ↓
rssi_mean / std / min / max / delta
```

e:

```text
Mendeley BeaconInterval configurado
!=
V2I meanInterBeaconTime observado
```

Portanto, para o perfil Beacon será derivada a feature comum:

```text
observed_inter_beacon_ms
```

O próximo passo é implementar esse feature engineering e criar os primeiros
arquivos em `data/processed/`.


---

# Fase 3 — Passo 3

Feature engineering inicial implementado.

```text
ml/features/
├── schema.py
├── io.py
├── beacon_profiles.py
└── build_profiles.py
```

Profiles:

```text
PROFILE_BEACON_1S
PROFILE_RSSI_TEMPORAL_5S
```

Os primeiros datasets preparados para ML estão em:

```text
data/processed/
```

O próximo passo define filtros de qualidade, balanceamento entre fontes e
splits por sessão/rede sem leakage.


---

# Fase 3 — Passo 4

Foram adicionados filtros de qualidade e splits sem leakage.

```text
ml/datasets/
├── quality.py
├── splits.py
└── validate_step4.py
```

Arquivos:

```text
data/processed/splits/profile_rssi_temporal_5s/
```

Regras principais:

```text
- sem remoção automática por IQR/z-score/P99;
- RSSI fisicamente plausível;
- TEMPORAL_RICH exige window_count >= 2;
- Mendeley dividido por identidade de AP;
- V2I dividido por trace;
- ataques nunca entram no treino;
- balanceamento somente no treino.
```

Próximo passo: criar as matrizes X e congelar conjuntos de features para o baseline.


---

# Fase 3 — Passo 5

Foram criadas as matrizes finais de entrada para o primeiro baseline.

Conjuntos congelados:

```text
conservative_v1
    rssi_std_db
    rssi_delta_db
    window_count
```

e:

```text
complete_v1
    rssi_mean_dbm
    rssi_std_db
    rssi_min_dbm
    rssi_max_dbm
    rssi_delta_db
    window_count
```

Os arquivos ficam em:

```text
data/processed/ml_ready/profile_rssi_temporal_5s/
```

Cada split contém:

```text
X.csv.gz
y.csv.gz
metadata.csv.gz
```

IDs, fonte, sessão e label não entram em X.

Próximo passo: teste de source leakage/domain shift antes dos modelos de anomalia.


---

# Fase 3 — Passo 6

Foi executado um diagnóstico explícito de source leakage.

Um classificador logístico tentou distinguir:

```text
Mendeley
vs.
V2I
```

usando apenas dados normais.

Resultado:

```text
conservative_v1
    forte source leakage

complete_v1
    source leakage ainda maior

conservative_v2
    rssi_std_db + rssi_delta_db
    muito mais próximo do acaso
```

Por isso:

```text
conservative_v2
```

passa a ser o baseline principal para o primeiro modelo de anomalia.

O próximo passo prepara o pipeline de anomaly detection e calibração de threshold.


---

# Fase 3 — Passo 7

O protocolo comum de anomaly detection foi congelado.

```text
feature_set:
conservative_v2

features:
rssi_std_db
rssi_delta_db
```

O `StandardScaler` é ajustado apenas em `train_balanced`.

Convenção:

```text
anomaly_score maior = mais anômalo
```

Threshold inicial:

```text
percentil 95 do validation normal
= target FPR de 5%
```

Ataques não participam da calibração do threshold.

Arquivos principais:

```text
config/anomaly_evaluation_protocol.json

ml/training/anomaly_pipeline.py
ml/evaluation/anomaly_protocol.py

ml/models/preprocessing/
└── conservative_v2_standard_scaler.joblib

data/processed/ml_ready/profile_rssi_temporal_5s/
└── conservative_v2_scaled/
```

O próximo passo inicia a Fase 4 com Isolation Forest.


---

# Fase 4 — Passo 1

Primeiro baseline real treinado:

```text
Isolation Forest
```

Features:

```text
rssi_std_db
rssi_delta_db
```

Treino:

```text
train_balanced
normal only
```

Threshold:

```text
validation normal P95
target FPR = 5%
```

Threshold congelado obtido neste experimento:

```text
0.04639529
```

Artefatos:

```text
ml/models/isolation_forest/
reports/models/isolation_forest/
```

Próximo passo: One-Class SVM usando o mesmo protocolo.


---

# Fase 4 — Passo 2

Segundo baseline real:

```text
One-Class SVM
```

Configuração principal:

```text
kernel = rbf
gamma = scale
nu = 0.05
```

Mesmo protocolo do Isolation Forest:

```text
conservative_v2
train_balanced normal only
validation normal P95
target FPR = 5%
```

Threshold obtido:

```text
0.00032858
```

Relatórios:

```text
reports/models/one_class_svm/
```

Próximo passo: Autoencoder.


---

# Fase 4 — Passo 3

Terceiro baseline:

```text
Autoencoder
PyTorch
2 -> 4 -> 1 -> 4 -> 2
```

Treinado somente com `train_balanced` normal.

A validação não foi usada para early stopping.

Score:

```text
mean squared reconstruction error
```

Threshold:

```text
validation normal P95
= 0.60188825
```

Agora temos:

```text
Isolation Forest
One-Class SVM
Autoencoder
```

sob o mesmo protocolo.

Próximo passo: comparação formal dos três e diagnóstico do feature set.


---

# Fase 4 — Passo 4

Foi concluída a primeira comparação formal entre:

```text
Isolation Forest
One-Class SVM
Autoencoder
```

usando `conservative_v2`.

Conclusão:

```text
o gargalo atual é a representação das features,
não apenas a escolha do algoritmo.
```

A partir daqui o trabalho é dividido em três tracks:

```text
TRACK_G_GENERALIZATION
    conservative_v2
    Mendeley + V2I

TRACK_E_EVIL_TWIN_CONTEXT
    evil_twin_contextual_v1
    Mendeley + futuras coletas próprias

TRACK_D_DESKTOP
    somente features confirmadas pelo scanner Windows
```

O próximo passo implementa `evil_twin_contextual_v1` sem usar flags sintéticas
prontas ou identificadores crus como features.


---

# Fase 4 — Passo 5

Foi implementado:

```text
evil_twin_contextual_v1
```

O profile é específico para redes com histórico conhecido.

Divisão dos normais do Mendeley:

```text
40% reference
30% model_train
15% validation
15% test_normal
```

O `reference` constrói somente o contexto histórico e não é usado como conjunto
de treino do anomaly model.

Features:

```text
ssid_bssid_count
bssid_changed
channel_changed
security_changed
security_strength_delta
is_hidden
configured_beacon_interval_ms
```

SSID/BSSID crus não são armazenados nos arquivos processados; apenas hashes
SHA-256 de correlação.

O próximo passo cria matrizes ML, analisa variância/redundância e ajusta o scaler
somente em `model_train_normal`.

### Integridade do Passo 5

Os artefatos do `evil_twin_contextual_v1` foram regenerados com o schema
canônico atualizado carregado explicitamente. Isso garante que
`configured_beacon_interval_ms` esteja presente nos arquivos processados e que
a cobertura reportada corresponda aos dados reais.


---

# Fase 4 — Passo 6

O Track E está pronto para Machine Learning.

Feature set principal:

```text
contextual_full_v1

ssid_bssid_count
bssid_changed
channel_changed
security_changed
security_strength_delta
is_hidden
```

`configured_beacon_interval_ms` foi removida porque é globalmente constante.

Features de evento constantes no normal foram preservadas de propósito.

Foram criados `X / y / metadata`, o scaler foi ajustado somente no
`model_train_normal` e o protocolo de avaliação contextual foi congelado.

Próximo passo: Isolation Forest no Track E.


---

# Fase 4 — Passo 7

Isolation Forest treinado no Track E com:

```text
contextual_full_v1
```

Threshold calibrado em `validation_normal`:

```text
0.22951226
```

A avaliação separa:

```text
cobertura contextual
```

de:

```text
recall entre amostras elegíveis
```

A inspeção das árvores também confirma quais features foram efetivamente usadas.
Features constantes no normal não geram splits no Isolation Forest.

Próximo passo: One-Class SVM no Track E.


---

# Fase 4 — Passo 8

One-Class SVM treinado no Track E usando:

```text
contextual_full_v1
```

Configuração:

```text
kernel = rbf
gamma = scale
nu = 0.05
```

Threshold validation P95:

```text
0.00060341
```

O relatório separa cobertura contextual de recall elegível e inclui um
diagnóstico explicativo de sensibilidade às features de evento que são
constantes no treino normal.

Próximo passo: Autoencoder no Track E.


---

# Fase 4 — Passo 9

Autoencoder treinado no Track E com:

```text
contextual_full_v1
6 -> 8 -> 3 -> 8 -> 6
```

Treino normal-only e validation reservada para threshold P95.

Threshold:

```text
0.00001332
```

Agora existem três modelos diretamente comparáveis no Track E:

```text
Isolation Forest
One-Class SVM
Autoencoder
```

Próximo passo: comparação formal e ablation com `contextual_variable_only_v1`.


---

# Fase 4 — Passo 10

Foi executada uma ablation controlada no Track E.

Controle:

```text
contextual_variable_only_v1

ssid_bssid_count
channel_changed
```

Foram removidas apenas:

```text
bssid_changed
security_changed
security_strength_delta
is_hidden
```

Isolation Forest, One-Class SVM e Autoencoder foram retreinados com o mesmo
protocolo para quantificar a contribuição dessas features de evento.

O candidato operacional atual do Track E é:

```text
One-Class SVM + contextual_full_v1
```

Essa escolha é provisória e precisa ser reavaliada com Evil Twin real.

Próximo passo: estudar features específicas de protocolo, começando por TSF.


---

# Fase 4 — Passo 11

Foi executada uma ablation específica de TSF.

Feature estudada:

```text
tsf_reference_monotonic_violation
```

Ela compara o `BeaconTimestamp` atual com o maior TSF observado no histórico
normal congelado para o mesmo BSSID dentro da mesma sessão.

O cenário sintético `tsf_reset` foi auditado e foi confirmado que ele altera
diretamente `BeaconTimestamp` em 5.398/5.398 linhas e `SequenceNumber` em
5.397/5.398.

Por isso a feature permanece:

```text
ABLATION ONLY
```

e não foi promovida para `contextual_full_v1` nem para o profile desktop.

Próximo passo: ablation isolada de `bssid_local_admin_flag`.


---

# Fase 4 — Passo 12

Ablation isolada de `bssid_local_admin_flag`.

A feature foi derivada diretamente do bit U/L do BSSID; a coluna pronta
`BSSID_LocalAdmin` do dataset sintético não foi usada como feature.

BSSIDs legítimos também apresentam U/L=1, e o cenário sintético foi criado
explicitamente em torno dessa propriedade. Por isso a feature permanece
`ABLATION ONLY`.

Próximo passo: investigar `observed_channel_vs_advertised_mismatch`.


---

# Fase 4 — Passo 13

Foi concluída a revisão de semântica de canal.

Descoberta principal:

```text
contextual_full_v1.channel_changed
usa raw Channel
e não DSChannel/advertised_channel
```

O cenário sintético `channel_shift` altera `Channel` em 100% das linhas, mas
não altera `DSChannel`.

Além disso, `Channel != DSChannel` ocorre em aproximadamente 49,18% do normal
quando `DSChannel=0` é incluído e em aproximadamente 40,95% dos pares normais
com `DSChannel` válido.

Decisões:

```text
capture_advertised_mismatch -> REJECTED
capture-based channel_changed -> DEPRECATED
advertised_channel_changed -> REAL-WORLD CANDIDATE, ainda não validada
contextual_full_v1 -> preservado, mas superseded pending v2
```

Próximo profile candidato:

```text
contextual_core_v2

ssid_bssid_count
bssid_changed
security_changed
security_strength_delta
is_hidden
```

Próximo passo: avaliação formal IF × OCSVM × Autoencoder no `contextual_core_v2`.


---

# Fase 4 — Passo 14

Foi formalizado o novo profile principal do Track E:

```text
contextual_core_v2

ssid_bssid_count
bssid_changed
security_changed
security_strength_delta
is_hidden
```

`channel_changed` baseado no raw `Channel` foi removido após a revisão metodológica do Passo 13.

Os três modelos foram retreinados e avaliados no mesmo protocolo. O candidato operacional atual é `One-Class SVM + contextual_core_v2`, ainda pendente de validação real.

Próximo passo: `desktop_candidate_v1`, limitado às features realmente observáveis pelo scanner Windows.


---

# Fase 4 — Passo 15

Foi formalizado o `desktop_candidate_v1` para Windows Native Wi-Fi API.

Features primárias:

```text
ssid_bssid_count
bssid_changed
security_changed
security_strength_delta
```

`is_hidden` não foi transportada automaticamente: o Windows fornece uma
condição observável de SSID não anunciado/vazio, registrada como
`ssid_not_broadcast`, mas ela permanece metadata até validação semântica e
retreinamento.

A Native Wi-Fi API também expõe RSSI, Beacon Interval, TSF, frequência recebida
e Information Elements por BSS, sem exigir packet capture. TSF permanece
`ABLATION ONLY`.

O OCSVM/scaler do `contextual_core_v2` não será reutilizado diretamente; o
`desktop_candidate_v1` precisa de validação em Windows e novo treino/calibração.

Próximo passo: implementar `wlanapi.dll` via ctypes e executar o primeiro scan
real em Windows.


---

# Fase 4 — Passo 16

Implementado o primeiro scanner Windows Native Wi-Fi com `ctypes`:

```text
WlanOpenHandle
WlanEnumInterfaces
WlanScan
WlanGetNetworkBssList
WlanFreeMemory
WlanCloseHandle
```

A camada nativa converte cada `WLAN_BSS_ENTRY` para `NativeWifiBssObservation`, mantendo as features separadas do adapter Win32.

Também foram adicionados:

```text
desktop/windows/wlanapi_ctypes.py
desktop/windows/scanner.py
desktop/windows/diagnostic.py
scripts/run_windows_wifi_diagnostic.ps1
```

O IE blob recebe bounds-check antes da leitura, e `ERROR_ACCESS_DENIED` é tratado como estado de permissão/localização em vez de lista vazia.

Status:

```text
CTYPES SCANNER READY
WINDOWS RUNTIME VALIDATION PENDING
```

Nenhum scan real foi executado neste ambiente porque ele não é Windows.

Próximo passo: executar o diagnóstico no Windows e validar os dados reais do driver antes da coleta própria normal.


---

# Fase 4 — Passo 17

Implementado o protocolo de coleta própria normal no Windows:

```text
Native Wi-Fi
→ scans repetidos
→ scans.jsonl
→ manifest.json
→ runtime_validation.json
```

Identificadores em claro ficam desabilitados por padrão e o split futuro será
agrupado por `session_id`.

Nenhum modelo desktop foi treinado.


---

# Fase 4 — Passo 18

Implementado o pipeline:

```text
data/raw/own/windows
→ validação de integridade/runtime
→ data/interim/own/windows
```

Nenhuma sessão Windows real foi importada e nenhum modelo foi treinado.


---

# Fase 4 — Passo 19

Foi congelada a metodologia de referência normal do `desktop_candidate_v1`.

Split mínimo, sempre por `session_id`:

```text
reference   = 1 sessão
model_train = 2 sessões
validation  = 1 sessão
test_normal = 1 sessão
```

Somente o split `reference` constrói o histórico normal.

As quatro features desktop já possuem transformador próprio:

```text
ssid_bssid_count
bssid_changed
security_changed
security_strength_delta
```

Não há sessões reais suficientes ainda, portanto nenhum modelo foi treinado.


---

# Fase 4 — Passo 20

Foi congelado o protocolo ML do `desktop_candidate_v1`.

Quando existirem cinco sessões Windows normais runtime-ready, o pipeline poderá
gerar automaticamente:

```text
X / y / metadata
StandardScaler fit apenas no model_train
```

O One-Class SVM e o threshold ainda não são criados neste passo.

No estado atual:

```text
real runtime-ready sessions = 0
ML matrices = blocked
scaler = blocked
model = not trained
```


---

# Fase 4 — Passo 21

Implementado o módulo de treino/calibração do OCSVM desktop:

```text
model_train -> fit OCSVM
validation -> P95 threshold
test_normal -> independent FPR
```

O projeto real continua bloqueado porque as sessões Windows ainda não foram
coletadas.

Fixtures sintéticas existem somente nos testes de software e não são tratadas
como resultado científico.


---

# Fase 4 — Passo 22

Implementado o pipeline separado para **observação defensiva** de um experimento
Wi-Fi controlado e autorizado.

A ferramenta não cria/configura o ataque.

```text
data/raw/own/windows_attack
→ integrity/import
→ frozen normal reference
→ attack features
→ future fixed-model evaluation
```

Dados de ataque permanecem proibidos em reference/scaler/model/threshold.


---

# Fase 4 — Passo 23

Implementado o avaliador final do `desktop_candidate_v1` usando exclusivamente
artefatos congelados.

```text
frozen scaler + frozen OCSVM + frozen threshold
+ test_normal + controlled real attack
→ final metrics
```

A avaliação rejeita ataques sintéticos e não permite refit/recalibração.

Nenhuma métrica real foi produzida porque os artefatos/dados reais ainda não
existem.


---

# Fase 4 — Passo 24

Backend local FastAPI implementado:

```text
GET  /health
POST /scan
GET  /networks
GET  /model
```

O scanner nativo é inicializado somente no primeiro `/scan`.

Instalação/execução:

```bash
pip install -r requirements-backend.txt
python -m backend
```


---

# Fase 4 — Passo 25

Persistência local adicionada com SQLite + SQLAlchemy + Alembic.

`POST /scan` grava sessões e observações sem persistir SSID/BSSID em claro.

Novo endpoint:

```text
GET /database
```


---

# Fase 4 — Passo 26

Runtime do `desktop_candidate_v1` integrado ao backend:

```text
scan
→ frozen reference
→ features
→ scaler.transform
→ OCSVM decision_function
→ frozen threshold
→ analysis
→ SQLite
```

Quando os artefatos reais ainda não existem, `/scan` continua funcionando com:

```text
analysis.status = not_available
```

Redes sem histórico suficiente usam:

```text
analysis.status = insufficient_history
```

e não são classificadas automaticamente como ataque.


---

# Fase 4 — Passo 27

APIs de histórico/auditoria implementadas:

```text
/history/scans
/history/scans/{scan_id}
/history/scans/{scan_id}/observations
/history/detections
/history/detections/{detection_id}
/history/models
/history/models/{model_version_id}
```

O histórico não retorna SSID/BSSID/GUID em claro; somente identificadores hash persistidos.


---

# Fase 4 — Passo 28

Endpoints agregados para o futuro dashboard:

```text
GET /dashboard/overview
GET /dashboard/trends
```

O overview reúne status, KPIs, distribuição de suspeita, scans recentes,
detecções recentes e versão ativa do modelo.

Os dados históricos do dashboard permanecem anonimizados.


---

# Fase 4 — Passo 29

Configurações persistentes da aplicação:

```text
GET   /settings
PATCH /settings
POST  /settings/reset
```

Preferências de scan, paginação, dashboard e futura atualização automática
ficam no SQLite.

As configurações não podem alterar referência, scaler, OCSVM ou threshold.


---

# Fase 4 — Passo 30

Frontend desktop iniciado com React + TypeScript + Vite + Electron + Tailwind CSS v4. Material UI não é utilizado.


---

# Fase 4 — Passo 31

Dashboard React/Tailwind completo com Recharts, consumindo:

```text
GET /dashboard/overview
GET /dashboard/trends
```

A tela possui KPIs, status do sistema, gráficos, atividade recente e estado do
modelo. `npm install`/build continuam adiados até a conclusão das etapas.


---

# Fase 4 — Passo 32

Tela de scan detalhada com Tailwind CSS: pré-verificação, loading, tratamento de permissão de localização/Win32, filtros, busca e detalhe técnico por rede. O Electron expõe apenas um IPC fixo para abrir `ms-settings:privacy-location`.


---

# Fase 4 — Passo 33

Tela `/networks` concluída com Tailwind CSS:

```text
busca
filtros
ordenação
contadores
detalhes técnicos expansíveis
features desktop_candidate_v1
```

A tela usa a última varredura em memória e não tenta reconstruir
SSID/BSSID a partir do histórico anonimizado.


---

# Fase 4 — Passo 34

Tela `/history` concluída com Tailwind CSS.

Fluxo de auditoria:

```text
scan → observação anonimizada → detecção → versão do modelo
```

A tela possui paginação e filtros e nunca tenta reconstruir SSID/BSSID em
claro a partir do SQLite.


---

# Fase 4 — Passo 35

Tela `/model` concluída com status dos quatro artefatos científicos, contrato
das features, versões persistidas e auditoria por SHA-256.

A UI é somente leitura e não permite retreino ou recalibração.


---

# Fase 4 — Passo 36

Tela `/settings` concluída com leitura, edição persistente e reset.

A política científica permanece somente leitura.


---

# Fase 4 — Passo 37

O Electron agora controla o ciclo de vida do backend local:

```text
health check
→ inicia Python se necessário
→ espera /health
→ abre a janela
→ encerra o backend pertencente ao Electron no quit
```

Em desenvolvimento utiliza `python -m backend`.

O contrato de produção já espera `resources/backend/evil-twin-backend.exe`,
que será criado em uma etapa posterior.


---

# Fase 4 — Passo 38

Backend preparado para PyInstaller e para o recurso
`frontend/resources/backend/evil-twin-backend.exe`.

O SQLite usa uma pasta gravável do usuário e as migrations são executadas
antes do Uvicorn.


---

# Fase 4 — Passo 39

Empacotamento desktop Windows preparado com electron-builder + NSIS.

A versão instalada usa Vite com `base: "./"` e `createHashRouter`.

O backend é incluído via `extraResources` como
`<resources>/backend/evil-twin-backend.exe`.

O instalador final permanece bloqueado até os builds reais.


---

# Fase 4 — Passo 40

O Electron possui scheduler de scans automáticos conectado às preferências
persistidas. O backend serializa `POST /scan` e devolve
`409 scan_in_progress` para uma segunda varredura concorrente.

Notificações são emitidas apenas para novas transições de redes para alta
suspeita e não exibem SSID/BSSID nem confirmam Evil Twin.


---

# Fase 4 — Passo 41

Dashboard e Redes observadas são sincronizados pelo evento `desktop:auto-scan-completed`, sem polling e sem reload completo do renderer.


---

# Fase 4 — Passo 42

Estado operacional centralizado no React para Backend, Scanner Native Wi-Fi, Modelo e Scheduler. A aplicação detecta perda e recuperação do backend sem recarregar o renderer.


---

# Fase 4 — Passo 43

Histórico e Modelo atualizam após scans automáticos/recuperação do backend. A rota `/diagnostics` exporta `support_bundle_v1` sem observações individuais, SSID/BSSID em claro, variáveis de ambiente ou caminhos absolutos.


---

# Fase 4 — Passo 44

A pipeline desktop agora possui um pré-flight científico obrigatório antes do
freeze de split/referência.

Sessões reais são validadas por proveniência, rótulo, SHA-256, cobertura,
completude e ausência de identificadores Wi-Fi em claro. Conteúdo duplicado
entre session_ids bloqueia o processo.

Quando 5 sessões válidas existirem, `session_split_plan.json` e
`scientific_freeze.json` tornam os assignments e hashes das fontes imutáveis.
Novas sessões posteriores são detectadas, mas não entram silenciosamente no
split congelado.

No estado atual: `blocked_no_real_sessions`.


---

# Fase 4 — Passo 45

A cadeia de artefatos de `desktop_candidate_v1` agora é ligada por SHA-256 e
pela mesma identidade de freeze científico.

`artifact_lineage.json` congela scaler e matrizes escaladas; o
`desktop_threshold_v2` liga referência, scaler e OCSVM. Runtime e avaliação
final bloqueiam qualquer mistura entre freezes diferentes.

No estado atual os artefatos desktop reais continuam ausentes e nada foi
treinado artificialmente.


---

# Fase 4 — Passo 46

A aplicação possui agora uma matriz única de readiness para a execução final:

```text
python -m desktop.final_readiness
```

Ela lista todos os gates entre a coleta Windows real e o instalador NSIS,
distinguindo `READY`, `BLOCKED`, `NOT_EXECUTED` e `OPTIONAL`.

Nenhuma etapa científica é marcadaada como executada apenas porque o código
correspondente existe.


---

# Fase 4 — Passo 47

A validação dependency-resolved do frontend foi preparada com `scripts/frontend_toolchain.py` e `scripts/validate_frontend_toolchain.ps1`.

O ambiente atual não resolve `registry.npmjs.org` (`EAI_AGAIN`), portanto Vitest e Vite build permanecem `NOT EXECUTED`. Um typecheck auxiliar com o compilador TypeScript real e stubs temporários encontrou e permitiu corrigir contratos locais; esses stubs não são incluídos no projeto.


---

# Fase 4 — Passo 48

Harness de integração determinístico para backend + Electron scheduler, sem Wi-Fi real ou artefatos científicos reais.


---

# Fase 4 — Passo 49

Foi adicionada uma suíte Playwright/Electron para validar o renderer completo
contra um backend HTTP determinístico de E2E.

A suíte cobre navegação, modelo não pronto, erros de scanner, scan manual,
Histórico, scan automático/IPC, perda/recuperação do backend e exportação
privada de diagnóstico.

A execução real de `npm run e2e` permanece condicionada às dependências npm.


---

# Fase 4 — Passo 50

Foi implementada a pipeline de geração do bundle final do TCC.

Ela só gera tabelas, curvas, matriz de confusão e manifesto quando a avaliação
final real estiver em `executed_fixed_artifacts`. Antes disso, o estado
permanece bloqueado e nenhuma métrica final é fabricada.


---

# Fase 4 — Passo 51

O release Windows agora possui um preflight estrito antes do electron-builder.

Os scripts deixaram de depender de `$IsWindows`, melhorando a compatibilidade
entre Windows PowerShell 5.1 e PowerShell 7+.

O NSIS só pode ser iniciado depois que gates científicos, resultados finais,
frontend dependency-resolved e Playwright/Electron E2E estiverem READY.

---

# Fase 4 — Passo 52

A implementação foi submetida a uma revisão geral antes da coleta Windows e
passa a possuir um snapshot SHA-256 verificável.

Foram endurecidos, entre outros pontos, o contrato de hash do SSID entre coleta
e runtime, importações incrementais/idempotentes, cobertura contextual antes do
freeze, coorte normal de um único ambiente para o E6, compatibilidade do ataque
controlado com a referência e scripts PowerShell operacionais independentes do
diretório de execução.

A coleta Windows deve começar somente após:

```powershell
.\scripts\check_windows_collection_readiness.ps1
```

retornar `READY_FOR_NORMAL_COLLECTION` no computador Windows. Para o E6 atual,
a recomendação operacional é coletar 9 sessões normais independentes da mesma
coorte/ambiente antes de congelar o split.

Os experimentos multi-source com Mendeley, V2I, Long-term e Station continuam
separados do modelo desktop E6 e sustentam a análise de generalização; o modelo
de produção desktop não reutiliza silenciosamente um modelo treinado nessas
bases públicas.
