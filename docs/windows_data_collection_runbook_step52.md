# Passo 52 — Runbook de coleta Windows

Este é o procedimento operacional para iniciar os **dados reais** depois do
freeze da implementação.

## 1. O que esta coleta representa

A coleta própria Windows é o experimento **E6 / desktop_candidate_v1**.

Ela não substitui os experimentos multi-source com Mendeley, V2I, Long-term e
Station. Esses experimentos tratam a pergunta de generalização entre fontes.

O E6 mede o protótipo desktop em um contexto controlado e observável pelo
Windows.

## 2. Regra mais importante: uma coorte normal

As sessões normais que entrarão no freeze inicial precisam usar o **mesmo
rótulo de ambiente**.

Exemplo:

```text
lab-principal
```

Use exatamente `lab-principal` em todas as sessões normais dessa coorte e no
ataque controlado final.

Não use:

```text
lab-manha
lab-tarde
casa
faculdade
```

como se fossem quatro ambientes da mesma execução E6.

O modelo desktop usa uma referência contextual conhecida. Misturar ambientes
independentes antes do freeze pode fazer SSIDs/BSSIDs do treino/validação/teste
ficarem desconhecidos para a referência. O pré-flight agora bloqueia esse caso.

Se futuramente quisermos um segundo ambiente próprio, ele deverá ser tratado
como **outra coorte/protocolo**, não inserido silenciosamente no freeze E6.

## 3. Quantidade

Mínimo técnico:

```text
5 sessões normais
```

Distribuição mínima:

```text
1 reference
2 model_train
1 validation
1 test_normal
```

Recomendação para o TCC:

```text
9 sessões normais
```

Com o split atual, isso tende a produzir:

```text
1 reference
4 model_train
2 validation
2 test_normal
```

Cada sessão:

```text
30 scans
wait do WlanScan = 4.2 s
intervalo adicional = 6 s
```

Não é necessário fazer as 9 sessões seguidas. É melhor variar condições
naturais do mesmo ambiente, por exemplo em horários ou dias diferentes, sem
alterar deliberadamente a rede.

## 4. Preparar o computador Windows

Na raiz do projeto:

```powershell
python -m pip install -r requirements-ml.txt -r requirements-backend.txt
```

Depois:

```powershell
.\scripts\check_windows_collection_readiness.ps1
```

Esse comando verifica:

```text
snapshot da implementação
host Windows
módulos Python
espaço em disco
estado do freeze
Native Wi-Fi API
interface Wi-Fi
permissão de localização
```

O esperado antes da primeira coleta é:

```text
READY_FOR_NORMAL_COLLECTION
```

O probe não grava SSID/BSSID em claro e não entra no dataset científico.

## 5. Diagnóstico adicional, se necessário

O diagnóstico agora é redigido por padrão:

```powershell
.\scripts\run_windows_wifi_diagnostic.ps1
```

Só use `-IncludeIdentifiers` para troubleshooting local deliberado. Não use essa
opção nas coletas científicas.

## 6. Coletar uma sessão normal

Exemplo:

```powershell
.\scripts\collect_windows_normal_session.ps1 `
    -Environment "lab-principal"
```

Se houver mais de um adaptador Wi-Fi, pode fixar o GUID após o diagnóstico:

```powershell
.\scripts\collect_windows_normal_session.ps1 `
    -Environment "lab-principal" `
    -InterfaceGuid "{GUID-DO-ADAPTADOR}"
```

A saída fica em:

```text
data/raw/own/windows/<session_id>/
├── scans.jsonl
├── runtime_validation.json
└── manifest.json
```

O `manifest.json` deve indicar:

```text
label = 0
attack_present = false
identifiers_in_clear_text = false
```

E `runtime_validation.json` deve indicar:

```text
runtime_ready_for_own_normal_collection = true
```

## 7. Importação pode ser incremental

Depois de uma sessão, é seguro executar:

```powershell
python -m desktop.windows.import_own_normal
```

O importador agora é idempotente. Sessões já importadas são revalidadas por
hash e marcadas como:

```text
already_imported_verified
```

em vez de serem tratadas como erro.

Depois de coletar pelo menos 5 sessões:

```powershell
python -m desktop.windows.scientific_preflight
```

Antes de `READY`, ele verifica também:

```text
mesma coorte/ambiente
hashes e proveniência
conteúdo duplicado
BSSID coverage >= 0.99
completude >= 0.70
candidate reference coverage >= 0.70 em train/validation/test
```

## 8. Não congele cedo demais

Mesmo que 5 sessões já deem `READY`, **não execute o freeze se pretende coletar
mais sessões normais**.

Depois que `scientific_freeze.json` for criado, sessões novas ficam
explicitamente fora do split existente.

Portanto, se a meta for 9 sessões, primeiro colete as 9.

Só depois execute:

```powershell
.\scripts\run_windows_desktop_normal_pipeline.ps1
```

Esse comando cria referência, scaler, OCSVM e threshold usando somente normal.

## 9. Ataque controlado

A coleta de ataque é defensiva e exige um experimento autorizado já ativo. O
coletor não cria nem configura um rogue AP.

O `-Environment` precisa ser o mesmo da coorte normal:

```powershell
.\scripts\collect_windows_controlled_attack.ps1 `
    -Scenario "controlled_evil_twin" `
    -Environment "lab-principal" `
    -AuthorizationNote "Experimento autorizado no laboratório ..."
```

O preparador de features bloqueará:

```text
ambiente divergente
ataque sintético
source_dataset incorreto
coverage elegível < 0.70
```

## 10. Avaliação depois do modelo congelado

Se a pipeline normal já foi executada, use:

```powershell
.\scripts\run_windows_attack_evaluation_pipeline.ps1
```

Ela faz apenas:

```text
import do ataque
features usando referência congelada
avaliação fixed-artifact
bundle agregado do TCC
```

Ela não executa novo `fit` e não recalibra threshold.

## 11. Execução end-to-end única

`run_final_end_to_end_windows.ps1` é uma alternativa para uma execução limpa a
partir de raw data já coletado e sem os artefatos processados materializados.

Não misture os dois modos no mesmo diretório create-only.
