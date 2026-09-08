# Fase 4 — Passo 46: matriz final de execução

Comando principal:

```powershell
.\scripts\check_final_execution_readiness.ps1
```

ou:

```bash
python -m desktop.final_readiness
```

A saída é materializada em:

```text
reports/desktop/final_execution_readiness_step46.json
reports/desktop/final_execution_readiness_step46.md
```

## Estados

```text
READY
```

O gate já possui o dado/artefato esperado e a validação correspondente passou.

```text
BLOCKED
```

O gate não pode prosseguir porque falta um pré-requisito ou dado real.

```text
NOT_EXECUTED
```

O código e os pré-requisitos estão disponíveis, porém o passo ainda não foi
executado.

```text
OPTIONAL
```

Não bloqueia a validação científica.

## Sequência

```text
código validado
→ integração determinística desktop
→ host Windows
→ 5+ sessões normais reais
→ scientific preflight
→ split/reference freeze
→ ML-ready + scaler + artifact_lineage
→ OCSVM + threshold
→ ataque controlado real/autorizado
→ attack features
→ final fixed-artifact evaluation
→ bundle agregado de resultados do TCC
→ frontend test/typecheck/build
→ Playwright/Electron E2E
→ backend PyInstaller
→ Electron/NSIS
```

Code signing continua opcional para o TCC e nunca é simulado.

## Execução final

Quando os dados reais estiverem disponíveis, existe um orquestrador:

```powershell
.\scripts\run_final_end_to_end_windows.ps1
```

Ele **não coleta redes** e **não cria um Evil Twin**. Ele só executa as etapas
de importação, preparação, treinamento, avaliação e build sobre dados que já
foram coletados de forma autorizada.

O script encerra imediatamente quando qualquer gate falha.


## Passo 48

Antes do host Windows, a matriz exige `desktop_integration_scenarios = READY`, gerado por `python -m desktop.integration.run_step48`. Esse gate não usa Wi-Fi real nem artefatos científicos reais.
