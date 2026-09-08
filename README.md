# Evil Twin Detector

Protótipo desktop de pesquisa para **detecção de anomalias em redes Wi-Fi**, com foco em identificar comportamentos potencialmente compatíveis com cenários de **Evil Twin**.

O projeto combina:

- coleta de redes Wi-Fi utilizando a API nativa do Windows;
- backend local em FastAPI;
- persistência SQLite;
- Machine Learning para detecção de anomalias;
- aplicação desktop com Electron;
- frontend React + TypeScript;
- pipeline científico reproduzível;
- testes automatizados;
- empacotamento e distribuição para Windows.

> **Importante:** o sistema identifica **anomalias e níveis de suspeita**. Uma observação acima do threshold não constitui, isoladamente, confirmação de um ataque Evil Twin.

---

## Sumário

- [Visão geral](#visão-geral)
- [Estado atual](#estado-atual)
- [Objetivo](#objetivo)
- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)
- [Fluxo de detecção](#fluxo-de-detecção)
- [Machine Learning](#machine-learning)
- [Artefatos científicos congelados](#artefatos-científicos-congelados)
- [Metodologia científica](#metodologia-científica)
- [Resultados e interpretação](#resultados-e-interpretação)
- [Datasets](#datasets)
- [Scanner Windows Native Wi-Fi](#scanner-windows-native-wi-fi)
- [Backend](#backend)
- [Frontend e Electron](#frontend-e-electron)
- [Telas da aplicação](#telas-da-aplicação)
- [Persistência](#persistência)
- [Privacidade e segurança](#privacidade-e-segurança)
- [Tecnologias](#tecnologias)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Instalação](#instalação)
- [Ambiente de desenvolvimento](#ambiente-de-desenvolvimento)
- [Testes e validação](#testes-e-validação)
- [Build e distribuição](#build-e-distribuição)
- [Reprodutibilidade](#reprodutibilidade)
- [Limitações](#limitações)
- [Trabalhos futuros](#trabalhos-futuros)
- [Release atual](#release-atual)

---

## Visão geral

O **Evil Twin Detector** é uma aplicação desktop desenvolvida para Windows que observa redes Wi-Fi disponíveis, extrai características contextuais e utiliza um modelo de detecção de anomalias para indicar situações que merecem atenção.

A aplicação foi desenvolvida como parte de um trabalho acadêmico de TCC e reúne componentes de:

- segurança de redes;
- análise de redes sem fio;
- engenharia de software;
- Machine Learning;
- desenvolvimento desktop;
- análise de dados;
- validação científica.

A arquitetura segue uma abordagem **local-first**.

Scanner, backend, inferência, banco de dados e interface são executados no computador do usuário.

Não existe dependência de um serviço externo para realizar a inferência do modelo.

---

## Estado atual

Versão atual:

```text
v1.3.0
```

Estado validado do projeto:

| Componente | Estado |
|---|---|
| Aplicação desktop Windows | Pronta |
| Frontend React | Pronto |
| Electron | Pronto |
| Backend FastAPI | Pronto |
| Scanner Native Wi-Fi | Implementado |
| Banco SQLite | Pronto |
| Migrations Alembic | Prontas |
| Modelo One-Class SVM | Pronto |
| Artefatos científicos | Congelados |
| Scan manual | Pronto |
| Scan automático | Pronto |
| Histórico | Pronto |
| Dashboard | Pronto |
| Diagnósticos | Pronto |
| Configurações | Prontas |
| Instalador Windows | Pronto |
| Testes Python | 235 passaram |
| Testes frontend | 32 passaram |
| E2E Electron | 6/6 passaram |
| TypeScript typecheck | Passou |
| Vite production build | Passou |
| Auditoria de dependências de produção | 0 vulnerabilidades |
| Final readiness | 17/17 READY |
| Aplicação instalada | Validada em Windows |

A versão `v1.3.0` foi:

- compilada;
- empacotada;
- instalada;
- executada;
- validada no Windows.

---

## Objetivo

O objetivo principal é investigar uma abordagem de **detecção de anomalias em redes Wi-Fi observáveis por um cliente Windows**.

O sistema busca identificar mudanças contextuais relacionadas a uma rede conhecida.

Entre elas:

- um mesmo SSID aparecendo com outro BSSID;
- mudança no padrão de segurança;
- redução da força relativa da configuração de segurança;
- aumento inesperado de BSSIDs associados ao mesmo SSID.

Esses sinais não são tratados individualmente como prova de ataque.

Eles são transformados em features utilizadas pelo detector de anomalias.

O objetivo da aplicação é indicar situações que apresentam comportamento diferente da referência normal conhecida e que, portanto, podem justificar investigação adicional.

---

## Funcionalidades

### Scan manual

Permite iniciar uma varredura Wi-Fi diretamente pela interface.

O fluxo inclui:

```text
scanner Windows
      ↓
normalização
      ↓
extração de features
      ↓
inferência
      ↓
persistência
      ↓
atualização da interface
```

---

### Scan automático

A aplicação possui um scheduler executado pelo processo principal do Electron.

O usuário pode configurar o comportamento do scan automático pela tela de configurações.

Após uma execução automática, o Electron notifica o frontend por IPC para atualizar as telas relevantes sem exigir recarregamento completo da aplicação.

---

### Dashboard

Apresenta uma visão consolidada do estado atual.

Inclui informações como:

- atividade recente;
- quantidade de redes observadas;
- níveis de suspeita;
- estado do backend;
- estado do scanner;
- estado do modelo;
- estado do scheduler.

---

### Redes

Permite visualizar as redes observadas.

A tela oferece:

- resumo das observações;
- filtros;
- detalhes;
- estado contextual;
- nível de suspeita;
- informações Wi-Fi disponíveis.

---

### Histórico

As varreduras são persistidas localmente.

A aplicação permite consultar scans anteriores sem depender apenas do estado atual do scanner.

---

### Modelo

Apresenta o estado dos quatro elementos científicos necessários para a inferência:

- referência normal;
- StandardScaler;
- modelo One-Class SVM;
- threshold.

A interface diferencia disponibilidade operacional de validade científica.

---

### Diagnósticos

A aplicação possui uma área dedicada a informações operacionais.

É possível gerar um bundle local de diagnóstico para suporte e troubleshooting.

O bundle padrão evita incluir identificadores Wi-Fi individuais desnecessários.

---

### Configurações

Permite ajustar parâmetros operacionais da aplicação, incluindo:

- atualização da interface;
- comportamento do scheduler;
- scan automático.

---

## Arquitetura

A arquitetura principal pode ser representada da seguinte forma:

```text
┌──────────────────────────────────────────────┐
│                Frontend React                │
│                                              │
│ Dashboard                                    │
│ Scan                                         │
│ Redes                                        │
│ Histórico                                    │
│ Modelo                                       │
│ Diagnósticos                                 │
│ Configurações                                │
└───────────────────────┬──────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────┐
│                   Electron                   │
│                                              │
│ main process                                 │
│ preload                                      │
│ IPC                                          │
│ backend manager                              │
│ auto-scan scheduler                          │
└───────────────────────┬──────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────┐
│                  FastAPI                     │
│               127.0.0.1:8765                │
│                                              │
│ scanner                                      │
│ inference                                    │
│ dashboard                                    │
│ history                                      │
│ settings                                     │
│ diagnostics                                  │
│ persistence                                  │
└───────────────┬───────────────────┬──────────┘
                │                   │
                ▼                   ▼
        Windows Native Wi-Fi      SQLite
             wlanapi.dll          Alembic
                │
                ▼
        contextual features
                │
                ▼
         StandardScaler
                │
                ▼
         One-Class SVM
                │
                ▼
            threshold
```

### Frontend

Responsável por:

- apresentação;
- navegação;
- filtros;
- visualização dos resultados;
- animações;
- feedback de status;
- interação com o usuário.

### Electron

Responsável por:

- ciclo de vida da aplicação desktop;
- preload;
- IPC;
- gerenciamento do backend local;
- scheduler de scan automático;
- integração com funções específicas do sistema operacional.

### Backend

Responsável por:

- scanner;
- inferência;
- persistência;
- dashboard;
- histórico;
- configurações;
- diagnósticos;
- estado dos artefatos científicos.

### Windows Native Wi-Fi

Responsável pela coleta das informações disponibilizadas pelo Windows sobre as redes observáveis.

### Machine Learning

Responsável por:

- cálculo das features;
- preprocessing;
- inferência;
- cálculo do anomaly score;
- comparação com o threshold.

---

## Fluxo de detecção

O fluxo principal é:

```text
Windows Native Wi-Fi
        ↓
scan das redes
        ↓
normalização
        ↓
referência normal
        ↓
extração das features
        ↓
StandardScaler
        ↓
One-Class SVM
        ↓
decision_function
        ↓
anomaly_score
        ↓
threshold
        ↓
nível de suspeita
        ↓
persistência
        ↓
frontend
```

A regra utilizada pelo runtime é:

```text
anomaly_score = -decision_function(X)

anomalia = anomaly_score > threshold
```

Uma observação marcada como anômala deve ser interpretada como um **indicador de suspeita**, não como confirmação automática de Evil Twin.

---

## Machine Learning

### Modelo utilizado no runtime

O modelo de produção desktop atual é:

```text
One-Class Support Vector Machine
One-Class SVM
OCSVM
```

O One-Class SVM é utilizado como detector de anomalias treinado sobre observações consideradas normais.

O objetivo é identificar observações que se afastem do comportamento representado pelo conjunto normal utilizado no treinamento.

---

### Features do modelo desktop

O contrato científico congelado contém exatamente quatro features:

```python
DESKTOP_FEATURES = [
    "ssid_bssid_count",
    "bssid_changed",
    "security_changed",
    "security_strength_delta",
]
```

| Feature | Significado |
|---|---|
| `ssid_bssid_count` | quantidade contextual de BSSIDs observados para o SSID |
| `bssid_changed` | indica mudança de BSSID em relação à referência |
| `security_changed` | indica mudança na configuração de segurança |
| `security_strength_delta` | diferença relativa de força da configuração de segurança |

---

### Preprocessing

As features passam pelo `StandardScaler` científico congelado antes da inferência.

```text
features
   ↓
StandardScaler
   ↓
One-Class SVM
   ↓
decision_function
   ↓
anomaly_score
   ↓
threshold
```

---

### Modelos presentes na pesquisa

O repositório também possui implementações e experimentos com:

- Isolation Forest;
- One-Class SVM;
- Autoencoder.

Esses modelos fazem parte da trilha científica de comparação e pesquisa.

O modelo utilizado pelo runtime desktop atual é o **One-Class SVM congelado**.

---

## Artefatos científicos congelados

A aplicação utiliza uma cadeia de artefatos científicos versionados.

### Referência normal

SHA-256:

```text
fddc8401cb65281ec2230aea127fde53c2c7bb1073c004ad2f822021da013b3f
```

---

### StandardScaler

SHA-256:

```text
e9560450fbf3413b17ddec72465488b7b0be8a94333d8df54d77a2d1aba1b263
```

---

### Modelo One-Class SVM

SHA-256:

```text
93cc7cc20e80213150e3167a93b5be5c7e353efbca6fe67ff63aa8aa4507aa3d
```

---

### Threshold

SHA-256:

```text
9dbeb3c66c43f01319b0bdf6453cab7fa29132a0a45a20fa2746cae0c6c5969f
```

Valor:

```text
3.2659592363870615e-08
```

---

### Split científico

Schema:

```text
desktop_session_split_plan_v2
```

Digest:

```text
a5e481a0067cf72ead32cf5b85c1a3eab5bee710f6e74f0856ddb0e62de88d15
```

Scientific freeze SHA-256:

```text
866df41f7daf8249287da770e0a67229247e413b11dc08a4b36101fa411f1010
```

---

### Política de freeze

Depois de congelados, os artefatos não devem sofrer:

- refit silencioso;
- recalibração silenciosa;
- alteração automática;
- substituição silenciosa da referência;
- mudança silenciosa do threshold;
- atualização por dados exploratórios.

Um novo treinamento deve produzir uma **nova versão científica**, preservando os artefatos utilizados nos resultados atuais.

---

## Metodologia científica

### Coleta própria normal

O pipeline científico utiliza sessões normais próprias coletadas em ambiente Windows.

Estado utilizado no freeze:

```text
9 sessões normais válidas
0 sessões inválidas
0 grupos de conteúdo duplicados
0 pares com sobreposição temporal
```

---

### Split independente

O split é realizado por sessões.

O conjunto normal independente possui:

```text
2 sessões
1395 observações brutas
1082 observações elegíveis
```

Isso evita tratar observações de uma mesma sessão como se fossem amostras completamente independentes em diferentes conjuntos.

---

### Referência normal

Uma referência contextual normal é construída a partir do conjunto definido no protocolo científico.

A referência é utilizada para determinar comportamentos como:

- mudança de BSSID;
- mudança de segurança;
- quantidade contextual de BSSIDs;
- diferença relativa de segurança.

---

### Treinamento

```text
dados normais
    ↓
features
    ↓
StandardScaler
    ↓
One-Class SVM
    ↓
validação
    ↓
threshold
    ↓
freeze
```

---

### Separação das evidências

A metodologia distingue explicitamente:

```text
dados normais de treino/referência
                ≠
teste normal independente
                ≠
sessão exploratória não verificada
                ≠
cenários hipotéticos
```

Dados exploratórios ou hipotéticos não podem modificar automaticamente os artefatos de produção congelados.

---

## Resultados e interpretação

### Teste normal independente

No conjunto normal independente congelado:

```text
False Positive Rate = 0.0
```

Foram avaliadas:

```text
2 sessões
1395 observações brutas
1082 observações elegíveis
```

Nenhuma observação elegível daquele conjunto ultrapassou o threshold congelado.

Isso mede o comportamento no **conjunto normal independente**.

Não mede capacidade de detectar um Evil Twin real.

---

### Sessão histórica em contexto de ataque

Existe uma sessão histórica coletada em contexto relacionado a ataque.

Ela possui:

```text
694 observações totais
560 observações elegíveis
```

Resultado:

```text
exploratory_threshold_exceedance_rate = 0.0
```

O papel científico dessa sessão é:

```text
exploratory_unverified_attack_context
```

A sessão **não possui ground truth confirmado de Evil Twin**.

Portanto, esse valor não deve ser descrito como:

- recall;
- false negative rate de ataque;
- accuracy;
- precision;
- F1.

---

### Cenários hipotéticos

O projeto também possui cenários hipotéticos construídos sobre o conjunto normal independente para analisar a sensibilidade do detector a perturbações controladas.

Resumo:

```text
5172 predições
4090 flags acima do threshold
```

Taxa global:

```text
0.7907965970610982
```

Controle:

```text
0.0
```

Resultados:

| Cenário | Predições | Flags | Threshold exceedance rate |
|---|---:|---:|---:|
| Controle hipotético | 1082 | 0 | 0.0 |
| Segurança mais fraca | 963 | 963 | 1.0 |
| Novo BSSID | 1082 | 1082 | 1.0 |
| Novo BSSID + mudança de segurança | 1082 | 1082 | 1.0 |
| Novo BSSID + downgrade | 963 | 963 | 1.0 |

Esses números representam **testes exploratórios de sensibilidade**.

Não representam:

- recall de ataque;
- precisão de ataque;
- F1 de ataque;
- acurácia de ataque;
- ROC-AUC;
- PR-AUC.

---

### Resumo das evidências

| Evidência | Ground truth de Evil Twin | Métrica válida | Interpretação |
|---|---|---|---|
| Teste normal independente | Não aplicável | FPR normal | comportamento do detector em dados normais independentes |
| Sessão histórica | Não confirmado | threshold exceedance rate | análise exploratória |
| Cenários hipotéticos | Não | threshold exceedance rate | stress test de sensibilidade |

---

## Datasets

O projeto possui pipelines para múltiplas fontes de dados utilizadas durante a pesquisa.

Entre elas:

- Mendeley Rogue AP;
- Wi-Fi V2I;
- Continuous Long-term Wi-Fi;
- Station / 802.11 Management Frames;
- coletas próprias realizadas em Windows.

Diretórios reservados:

```text
data/external/mendeley_rogue_ap/
data/external/zenodo_v2i/
data/external/zenodo_longterm/
data/external/zenodo_station/
```

Os datasets públicos são utilizados na trilha de:

- pesquisa;
- normalização;
- feature engineering;
- análise de representação;
- comparação;
- generalização.

Eles não são silenciosamente misturados ao modelo desktop congelado quando possuem contratos de observação incompatíveis.

A versão desktop atual utiliza sua própria coorte normal Windows conforme o protocolo científico congelado.

---

## Scanner Windows Native Wi-Fi

A coleta desktop utiliza a **Native Wi-Fi API** do Windows.

Principais componentes:

```text
desktop/windows/scanner.py
desktop/windows/wlanapi_ctypes.py
desktop/windows/native_wifi_contract.py
desktop/windows/ie_parser.py
desktop/windows/scan_serialization.py
```

A implementação utiliza:

```text
wlanapi.dll
```

Dependendo do Windows, driver e adaptador, podem estar disponíveis informações como:

- SSID;
- BSSID;
- intensidade ou qualidade de sinal;
- frequência;
- canal;
- autenticação;
- segurança;
- Information Elements.

A capacidade real de observação depende de:

- versão do Windows;
- adaptador Wi-Fi;
- driver;
- permissões;
- políticas de localização;
- serviços do sistema.

O projeto também possui tratamento para:

- scanner indisponível;
- funcionalidade não suportada;
- acesso negado;
- falhas temporárias;
- serialização consistente;
- integração com o pipeline de inferência.

---

## Backend

O backend é uma API local construída com **FastAPI**.

Endereço padrão:

```text
http://127.0.0.1:8765
```

Principais módulos:

```text
backend/app.py
backend/scanner_service.py
backend/inference.py
backend/model_status.py
backend/persistence.py
backend/history.py
backend/dashboard.py
backend/diagnostics.py
backend/settings.py
backend/runtime_store.py
backend/runtime_paths.py
backend/migrations_runner.py
```

Responsabilidades:

- executar scans;
- serializar resultados;
- executar inferência;
- validar artefatos científicos;
- persistir observações;
- servir histórico;
- fornecer dados do dashboard;
- armazenar configurações;
- gerar diagnósticos;
- executar migrations;
- resolver caminhos de runtime.

---

## Frontend e Electron

O frontend utiliza:

```text
React
TypeScript
Vite
Electron
Tailwind CSS
```

A versão `v1.3.0` recebeu um redesign completo da interface.

Também são utilizadas:

```text
Three.js
GSAP
Anime.js
Motion
Lucide React
Recharts
```

---

### Componentes visuais

Entre os componentes introduzidos no redesign estão:

```text
frontend/src/components/visual/AmbientNetworkScene.tsx
frontend/src/components/visual/NetworkBackdrop.tsx
frontend/src/components/visual/ScanRadarScene.tsx
frontend/src/components/visual/SignalPulseField.tsx
frontend/src/lib/animation.ts
```

---

### Electron

O Electron é responsável por:

- processo principal;
- preload;
- IPC;
- lifecycle do backend;
- scheduler de scans;
- integração Windows;
- inicialização do backend empacotado em produção.

Principais arquivos:

```text
frontend/electron/main.cjs
frontend/electron/preload.cjs
frontend/electron/backend-manager.cjs
frontend/electron/auto-scan-scheduler.cjs
```

---

## Telas da aplicação

### Dashboard

```text
frontend/src/pages/DashboardPage.tsx
```

Apresenta uma visão geral da aplicação e do estado operacional.

---

### Scan

```text
frontend/src/pages/ScanPage.tsx
```

Responsável pelo scan manual e pelos principais estados do scanner/modelo.

---

### Redes

```text
frontend/src/pages/NetworksPage.tsx
```

Apresenta redes observadas, filtros, estado contextual e detalhes.

---

### Histórico

```text
frontend/src/pages/HistoryPage.tsx
```

Permite consultar scans persistidos anteriormente.

---

### Modelo

```text
frontend/src/pages/ModelPage.tsx
```

Apresenta o estado dos artefatos científicos utilizados pelo runtime.

---

### Diagnósticos

```text
frontend/src/pages/DiagnosticsPage.tsx
```

Apresenta informações operacionais e permite gerar bundle local de suporte.

---

### Configurações

```text
frontend/src/pages/SettingsPage.tsx
```

Permite modificar parâmetros operacionais da aplicação.

---

## Persistência

A aplicação utiliza:

```text
SQLite
SQLAlchemy
Alembic
```

Local padrão do banco em produção:

```text
%LOCALAPPDATA%\EvilTwinDetector\evil_twin_detector.db
```

Migrations versionadas:

```text
backend/migrations/versions/0001_initial_schema.py
backend/migrations/versions/0002_runtime_artifacts.py
backend/migrations/versions/0003_application_settings.py
```

O banco é armazenado localmente.

---

## Privacidade e segurança

A aplicação foi projetada para processamento local.

Princípios:

- backend acessível somente pelo localhost;
- banco armazenado localmente;
- ausência de upload automático;
- diagnóstico sem identificadores Wi-Fi claros por padrão;
- dados brutos locais não são versionados pelo Git;
- artefatos científicos possuem hashes de integridade;
- eventos internos não precisam transportar SSID/BSSID em texto claro.

---

### Pseudonimização

Identificadores podem ser representados por SHA-256.

Isso deve ser interpretado como **pseudonimização**, e não como anonimização criptograficamente irreversível.

Nomes de SSID previsíveis podem continuar suscetíveis a ataques de dicionário ou comparação.

---

## Tecnologias

### Backend

| Tecnologia | Função |
|---|---|
| Python | backend e pipelines |
| FastAPI | API local |
| Uvicorn | servidor ASGI |
| Pydantic | validação |
| SQLAlchemy | ORM |
| Alembic | migrations |
| SQLite | persistência |

### Machine Learning

| Tecnologia | Função |
|---|---|
| NumPy | processamento numérico |
| pandas | manipulação de dados |
| scikit-learn | modelos e preprocessing |
| joblib | serialização |

### Frontend

| Tecnologia | Função |
|---|---|
| React | interface |
| TypeScript | tipagem |
| Vite | build |
| Tailwind CSS | estilização |
| Three.js | elementos visuais |
| GSAP | animações |
| Anime.js | animações |
| Motion | transições |
| Lucide React | ícones |
| Recharts | gráficos |

### Desktop e distribuição

| Tecnologia | Função |
|---|---|
| Electron | aplicação desktop |
| PyInstaller | empacotamento do backend |
| electron-builder | empacotamento Electron |
| NSIS | instalador Windows |

### Testes

| Tecnologia | Uso |
|---|---|
| Pytest | backend, ML e pipelines |
| Vitest | frontend |
| Playwright | E2E Electron |

---

## Estrutura do projeto

```text
evil-twin-detector/
│
├── backend/
│   ├── API
│   ├── scanner
│   ├── inference
│   ├── persistence
│   ├── history
│   ├── diagnostics
│   └── migrations
│
├── config/
│   └── configurações e contratos
│
├── data/
│   ├── app/
│   ├── external/
│   └── processed/
│
├── desktop/
│   ├── features/
│   ├── integration/
│   ├── packaging/
│   └── windows/
│
├── experiments/
│
├── frontend/
│   ├── electron/
│   ├── e2e/
│   ├── src/
│   └── tests/
│
├── ml/
│   ├── datasets/
│   ├── evaluation/
│   ├── features/
│   ├── models/
│   ├── preprocessing/
│   └── training/
│
├── scripts/
│
├── tests/
│
├── requirements-backend.txt
├── requirements-ml.txt
├── requirements-packaging.txt
└── README.md
```

---

## Instalação

### Usuário final

A forma recomendada de instalar a aplicação é utilizar o instalador disponibilizado na release do GitHub.

Versão:

```text
v1.3.0
```

Release:

```text
https://github.com/patricknperes/evil-twin-detector/releases/tag/v1.3.0
```

Sistema alvo:

```text
Windows 10/11 x64
```

O instalador ainda não possui assinatura digital de código.

Por esse motivo, o Windows SmartScreen pode apresentar um aviso durante a instalação.

---

## Ambiente de desenvolvimento

### Pré-requisitos

- Windows;
- Python;
- Node.js;
- npm;
- PowerShell;
- adaptador Wi-Fi para execução de scans reais.

---

### Criar ambiente Python

Na raiz:

```powershell
python -m venv .venv
```

Ativar:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

### Dependências Python

```powershell
python -m pip install -r requirements-backend.txt
python -m pip install -r requirements-ml.txt
python -m pip install -r requirements-packaging.txt
```

---

### Dependências frontend

```powershell
cd frontend
npm ci
```

---

### Executar a aplicação em desenvolvimento

Na raiz:

```powershell
.\scripts\run_desktop_dev.ps1
```

---

### Executar somente o backend

```powershell
.\scripts\run_backend.ps1
```

---

## Testes e validação

### Testes Python

```powershell
python -m pytest -q tests
```

Resultado validado na `v1.3.0` antes da limpeza documental:

```text
235 passed
2 skipped
1 warning
```

Existe um warning conhecido relacionado à compatibilidade/depreciação entre `httpx` e `starlette.testclient`.

---

### Testes frontend

```powershell
cd frontend
npm test
```

Resultado:

```text
13 test files passed
32 tests passed
```

---

### TypeScript

```powershell
npm run typecheck
```

Resultado:

```text
PASSED
```

---

### Build web

```powershell
npm run build:web
```

Resultado:

```text
PASSED
```

---

### Electron E2E

```powershell
npm run e2e
```

Resultado:

```text
6 passed
```

Os cenários E2E incluem situações como:

- modelo ainda não pronto;
- scanner indisponível;
- scan manual sem modelo pronto;
- atualização automática via IPC;
- perda e recuperação do backend;
- exportação de diagnóstico com proteção dos identificadores Wi-Fi.

---

### Validação integrada

Na raiz:

```powershell
.\scripts\validate_renderer_e2e.ps1
```

---

### Auditoria de dependências de produção

```powershell
cd frontend
npm audit --omit=dev
```

Resultado validado:

```text
found 0 vulnerabilities
```

---

### Readiness final

```powershell
python -m desktop.final_readiness
```

Estado validado antes da limpeza documental:

```text
overall_status: COMPLETE
final_pipeline_complete: true

ready_stage_count: 17
mandatory_stage_count: 17
```

> Alterações na árvore do repositório, inclusive mudanças documentais, podem alterar o snapshot de implementação. Após uma limpeza estrutural do repositório, os checks de freeze/readiness devem ser executados novamente antes de registrar o novo estado final.

---

## Build e distribuição

### Backend

```powershell
.\scripts\build_backend_windows.ps1
```

O backend é empacotado com PyInstaller.

---

### Instalador Windows

```powershell
.\scripts\build_desktop_installer_windows.ps1
```

O pipeline de build executa:

```text
validação frontend
        ↓
Vitest
        ↓
TypeScript
        ↓
Vite build
        ↓
Electron E2E
        ↓
PyInstaller backend
        ↓
release preflight
        ↓
electron-builder
        ↓
NSIS
        ↓
verificação do instalador
```

---

### Backend empacotado

Em produção, o executável do backend é incluído como recurso da aplicação Electron.

O processo principal gerencia:

- inicialização;
- disponibilidade;
- recuperação;
- encerramento.

---

### Symbolic links no Windows

Em alguns ambientes Windows, o `electron-builder` pode exigir permissão para criação de symbolic links ao preparar o pacote `winCodeSign`.

Alternativas possíveis:

- habilitar o Developer Mode do Windows;
- executar somente a etapa necessária com privilégio adequado.

O uso permanente de um terminal elevado não é um requisito arquitetural da aplicação.

---

## Reprodutibilidade

O projeto mantém mecanismos de rastreabilidade que relacionam:

- código;
- datasets;
- split;
- referência;
- scaler;
- modelo;
- threshold;
- execução;
- release.

Entre os artefatos utilizados estão:

```text
session_split_plan.json
scientific_freeze.json
preparation_manifest.json
desktop_normal_reference.json
threshold.json
implementation snapshot
release manifest
```

A aplicação não realiza treinamento ou recalibração silenciosa dos artefatos científicos durante o runtime.

---

### Bundle final de resultados

O gerador final do TCC produz artefatos como:

```text
metrics_summary.csv
score_distribution.csv
exploratory_session_summary.csv
hypothetical_scenarios.csv
timing_summary.csv
score_distribution.png
hypothetical_threshold_exceedance.png
final_results_summary.md
reproducibility_manifest.json
```

O manifesto final diferencia explicitamente:

- teste normal;
- sessão exploratória sem ground truth confirmado de ataque;
- cenários hipotéticos.

---

## Limitações

### Ausência de ground truth confirmado de Evil Twin real

Essa é a principal limitação científica do estado atual.

O projeto não possui um conjunto independente de teste com **ground truth confirmado de Evil Twin real** adequado para uma avaliação supervisionada final.

---

### Métricas de ataque

Por não existir ground truth confirmado, o projeto não apresenta como resultado final de ataque real:

- precision;
- recall;
- F1-score;
- accuracy;
- ROC-AUC;
- PR-AUC;
- confusion matrix.

---

### Variabilidade das features

No conjunto congelado utilizado durante o treinamento desktop, apenas:

```text
ssid_bssid_count
```

apresentou variância de treinamento relevante.

As outras três features apresentaram variância zero naquele conjunto:

```text
bssid_changed
security_changed
security_strength_delta
```

Isso limita o comportamento que o modelo conseguiu aprender no conjunto atual e deve ser considerado na interpretação da capacidade de generalização.

---

### Generalização

O modelo congelado foi construído a partir de uma coorte normal específica.

Uma avaliação mais forte exige:

- novos ambientes;
- diferentes redes;
- diferentes adaptadores;
- diferentes drivers;
- novas sessões independentes.

---

### Dependência do Windows

A capacidade de observação depende de:

- Windows;
- `wlanapi.dll`;
- adaptador Wi-Fi;
- driver;
- permissões;
- políticas de localização;
- serviços do sistema.

---

### Cenários hipotéticos

Cenários sintéticos são úteis como stress tests de sensibilidade.

Eles não substituem observações independentes com ground truth real.

---

### Assinatura digital

O instalador Windows ainda não utiliza certificado de assinatura digital.

---

### Bundle frontend

O build atual pode emitir aviso do Vite para chunks maiores que 500 kB.

Isso não impede o funcionamento da aplicação, mas representa uma oportunidade de otimização.

---

### Warning da suíte Python

Existe um warning conhecido relacionado à camada de testes HTTP/Starlette.

Ele não impede a aprovação atual da suíte, mas deve ser eliminado futuramente.

---

## Trabalhos futuros

### Coleta de dados

- aumentar o número de sessões normais;
- coletar em diferentes ambientes;
- aumentar diversidade de redes;
- utilizar diferentes adaptadores;
- utilizar diferentes drivers;
- testar diferentes versões do Windows;
- manter separação adequada entre treino, validação e teste.

---

### Ground truth

Obter, em trabalho futuro, dados com ground truth verificável utilizando um protocolo controlado, ético e metodologicamente adequado.

A execução de um ataque real não é necessária para o funcionamento atual da aplicação.

---

### Machine Learning

- comparar OCSVM, Isolation Forest e Autoencoder sob o mesmo protocolo;
- investigar novas features;
- melhorar a variabilidade das features;
- realizar novos estudos de ablação;
- avaliar sensibilidade do threshold;
- testar generalização entre ambientes;
- produzir novas versões do modelo sem alterar o freeze atual.

---

### Aplicação

- melhorar acessibilidade;
- realizar testes de usabilidade;
- implementar code splitting;
- reduzir tamanho do bundle frontend;
- adicionar assinatura digital;
- melhorar metadados e ícone do instalador;
- ampliar diagnósticos;
- testar uma matriz maior de versões do Windows.

---

### Pesquisa

- aumentar a quantidade de dados independentes;
- avaliar ambientes distintos;
- analisar mudanças reais de infraestrutura;
- investigar outras informações observáveis pelo cliente Wi-Fi;
- aprofundar o estudo das limitações de detectores baseados somente na visão do cliente.

---

## Release atual

### Evil Twin Detector v1.3.0

A versão `v1.3.0` introduziu um redesign completo do frontend.

Principais alterações:

- nova identidade visual;
- nova organização das telas;
- novos componentes visuais;
- integração com Three.js;
- integração com GSAP;
- integração com Anime.js;
- integração com Motion;
- atualização dos componentes;
- ajuste dos testes E2E;
- inclusão de `package-lock.json`;
- validação completa do instalador.

---

### Instalador

Arquivo utilizado no build:

```text
Evil Twin Detector-Setup-1.3.0-x64.exe
```

SHA-256:

```text
C81EE56EB4E055622174E1C2BC69306F1F51E00C0A1AA74B14724C79451A4DB3
```

O hash publicado na release do GitHub foi verificado contra o instalador local utilizado durante a validação.

Release:

```text
https://github.com/patricknperes/evil-twin-detector/releases/tag/v1.3.0
```

---

## Status científico da v1.3.0

Os artefatos científicos congelados utilizados na `v1.3.0` não foram:

- retreinados;
- recalibrados;
- substituídos;
- modificados durante o redesign.

A alteração da `v1.3.0` foi concentrada principalmente na interface e experiência da aplicação desktop.

---

## Sobre os nomes internos do projeto

Alguns arquivos de código, testes, scripts e configurações ainda possuem identificadores históricos internos em seus nomes.

Esses nomes podem ser mantidos quando fazem parte de:

- imports;
- contratos;
- testes;
- scripts;
- automações;
- rastreabilidade científica.

Eles **não representam etapas que o usuário precisa executar**.

A documentação oficial consolidada do estado atual do projeto é este `README.md`.

---

## Repositório

```text
https://github.com/patricknperes/evil-twin-detector
```

---

## Aviso

Este projeto possui finalidade **acadêmica e experimental**.

Resultados produzidos pelo detector devem ser interpretados como **indicadores de anomalia ou suspeita**, e não como confirmação automática da existência de um ataque Evil Twin.