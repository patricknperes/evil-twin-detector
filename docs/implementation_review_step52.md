# Passo 52 — Revisão geral da implementação antes da coleta Windows

## Resultado

**A implementação está pronta para iniciar a validação no computador Windows**, mas isso não significa que a coleta Windows já tenha sido validada.

```text
IMPLEMENTAÇÃO = REVISADA / SNAPSHOT READY
WINDOWS REAL  = NOT EXECUTED
DADOS REAIS   = NOT COLLECTED
MODELO E6 REAL = NOT TRAINED
```

Snapshot da implementação:

```text
schema = implementation_snapshot_step52_v1
files = 374
tree_sha256 = 23a8cc4a0d27307e0995cf11ec5f32ecf70663c7c34230612d40f0cd6a714720
```

Qualquer mudança posterior em backend, desktop, frontend, ML, scripts, testes, protocolos ou requisitos fará a verificação do snapshot falhar até um novo freeze explícito.

## O que foi revisado

A revisão cobriu:

```text
arquitetura científica
normalização e proveniência dos dados
Windows Native Wi-Fi / serialização
privacy/hash contracts
split e freeze
referência contextual desktop
StandardScaler / OCSVM / threshold
artifact lineage
ataque controlado
avaliação final
resultados do TCC
FastAPI / SQLite
React / Electron / Tailwind
scheduler e IPC
E2E determinístico
PowerShell operacional
PyInstaller / electron-builder / NSIS gates
```

## Problemas importantes encontrados e corrigidos

1. **Hash do SSID entre coleta e runtime.** A coleta recebia bytes IEEE 802.11 e o runtime trabalhava com texto decodificado. Para SSID com bytes UTF-8 inválidos, os hashes podiam divergir. Existe agora um único contrato canônico de decodificação com replacement + SHA-256 namespaced.
2. **Contrato de features do OCSVM no runtime.** O modelo é treinado com nomes das quatro features; depois do scaler o runtime entregava um ndarray sem nomes. O runtime volta a materializar um DataFrame com `desktop_candidate_v1` antes da inferência.
3. **Importação incremental.** Uma sessão já importada deixava uma execução posterior falhar por causa do create-only. Agora ela é revalidada por SHA-256 e marcada `already_imported_verified`.
4. **Freeze precoce com contexto ruim.** O pré-flight agora simula o split determinístico e exige coverage elegível >= 0.70 para `model_train`, `validation` e `test_normal` antes de tornar o split imutável.
5. **Mistura de ambientes no E6.** O E6 atual usa uma referência contextual. Por isso, sessões próprias de ambientes independentes não podem ser misturadas em uma única coorte normal/freeze.
6. **Ataque incompatível com a referência.** A avaliação controlada agora exige o mesmo ambiente da coorte normal e coverage >= 0.70; caso contrário, nenhum output de ataque é criado.
7. **Scripts Windows.** Coleta/import/preparo agora resolve a raiz do projeto, não depende do diretório de onde o `.ps1` foi chamado e não oferece identificadores em claro nos wrappers científicos.
8. **Validação acumulada antiga.** `final_readiness` agora verifica o digest do snapshot Step52; um relatório antigo não pode manter `implementation_validation=READY` depois de mudança no código.
9. **Diagnóstico Wi-Fi.** Redação de identificadores passou a ser o padrão.
10. **Alembic e testes.** O warning de configuração foi eliminado e a suíte acumulada terminou sem warnings.

## Decisão metodológica antes de coletar

Há dois trilhos diferentes e eles não devem ser misturados na redação do TCC:

### Trilha multi-source / generalização

Mendeley, V2I, Long-term e Station continuam sendo usados nos experimentos que investigam generalização, robustez, compatibilidade semântica de features e falsos positivos.

### E6 / protótipo desktop

O modelo que será executado pelo aplicativo Windows usa o contrato `desktop_candidate_v1`:

```text
ssid_bssid_count
bssid_changed
security_changed
security_strength_delta
```

Para esse E6, o normal real vem das sessões próprias Windows e o ataque controlado real é **somente avaliação**. O modelo público/Mendeley não é reutilizado silenciosamente como modelo de produção.

Isso é intencional: várias features das bases públicas não possuem a mesma semântica/observabilidade no scanner Windows.

## Plano recomendado de coleta normal

Mínimo técnico:

```text
5 sessões
1 reference
2 train
1 validation
1 test_normal
```

Recomendação antes do freeze:

```text
9 sessões normais independentes
30 scans por sessão
mesmo rótulo de ambiente/coorte
sem ataque ativo
sem SSID/BSSID em claro
```

Com 9 sessões, o split atual tende a ficar em torno de:

```text
1 reference
4 model_train
2 validation
2 test_normal
```

Use o mesmo nome de ambiente em todas, por exemplo `lab-principal`. Variações naturais de horário/dia dentro desse ambiente são desejáveis. Um segundo ambiente próprio deve ser tratado como uma nova coorte/protocolo, não adicionado silenciosamente depois do freeze.

## O que ainda não está validado

Os itens abaixo não impedem iniciar a coleta, mas **não podem ser declarados concluídos**:

- Native Wi-Fi, permissões de localização e fill-rate real das features no seu Windows;
- execução real dos scripts em Windows PowerShell 5.1 / PowerShell 7;
- Vitest, typecheck dependency-resolved e Vite build, porque este ambiente continua sem resolver `registry.npmjs.org`;
- Playwright/Electron E2E real;
- PyInstaller e NSIS;
- avaliação final e métricas finais, pois os dados reais ainda não existem.

Também permanecem dois débitos de UX não científicos: paginação das observações no detalhe de Histórico e o filtro `insufficient` aplicado no cliente sobre uma página de resultados. Eles não alteram a coleta nem o treinamento.

## Próxima ação no Windows

Na raiz do projeto:

```powershell
python -m pip install -r requirements-ml.txt -r requirements-backend.txt
.\scripts\check_windows_collection_readiness.ps1
```

Só iniciar a primeira sessão quando o resultado for:

```text
READY_FOR_NORMAL_COLLECTION
```

Depois, a primeira sessão normal:

```powershell
.\scripts\collect_windows_normal_session.ps1 `
    -Environment "lab-principal"
```

O procedimento completo está em `docs/windows_data_collection_runbook_step52.md`.
