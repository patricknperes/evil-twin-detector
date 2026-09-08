# Fase 4 — Passo 17: runtime Windows e coleta própria normal

## Primeiro teste

```powershell
python -m desktop.windows.normal_collection `
  --environment teste-runtime `
  --scans 10 `
  --interval-seconds 3
```

ou:

```powershell
.\scripts\collect_windows_normal_session.ps1 `
  -Environment teste-runtime `
  -Scans 10 `
  -IntervalSeconds 3
```

O resultado fica em:

```text
data/raw/own/windows/<session_id>/
├── scans.jsonl
├── manifest.json
└── runtime_validation.json
```

`scans.jsonl` é bruto e imutável.

## O validator mede

- estabilidade de SSID/BSSID por hash;
- segurança por BSS;
- RSSI;
- Beacon Interval;
- TSF e sua continuidade por BSSID;
- host timestamp;
- frequência central;
- Information Elements;
- truncamento;
- DS Parameter Set.

O campo principal é:

```text
runtime_ready_for_own_normal_collection
```

## Coleta normal

Depois do teste curto:

```text
30 scans por sessão
6 s entre scans
>= 5 sessões por ambiente quando viável
```

Cada execução deve gerar novo `session_id`.

O split científico será sempre agrupado por `session_id`.

Não execute Evil Twin durante sessões `label=0`.

## Privacidade

Por padrão:

```text
SSID/BSSID em claro = NÃO
hash SHA-256 estável = SIM
coordenadas = NÃO
```

## Próximo treino

Somente depois da coleta real validada construiremos:

```text
desktop_candidate_v1

ssid_bssid_count
bssid_changed
security_changed
security_strength_delta
```

e treinaremos/calibraremos um novo OCSVM. O modelo/scaler/threshold do
`contextual_core_v2` não será reutilizado.
