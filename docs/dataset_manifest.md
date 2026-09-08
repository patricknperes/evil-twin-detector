# Manifesto definitivo dos datasets

**Fase 2 — Passo 9**

Este documento fecha a seleção e a classificação das bases usadas no TCC II.

## Bases aprovadas

| Fonte | Perfil | Volume validado | Papel |
|---|---|---:|---|
| Mendeley | `mendeley_legitimate_real` | 29,990 | Treino normal principal |
| Mendeley | `mendeley_synthetic_rogue` | 37,786 | Teste auxiliar de ataque |
| V2I | `v2i_beacon_profile` | 14,812 | Treino normal complementar |
| V2I | `v2i_desktop_aux` | 31,044 | Experimentos auxiliares |
| Long-term | `longterm_temporal_rssi_channel` | 13,471,554 observações AP | Robustez temporal |
| Station | `station_public_environment` | 97,290 frames | Falsos positivos / ambiente não visto |
| Coleta própria | planejada | — | Treino próprio + Evil Twin controlado |

## Regra principal

Não existe um único dataset final obtido simplesmente concatenando todas as bases.

Cada fonte participa apenas dos experimentos para os quais possui features semanticamente compatíveis.

## Treino normal principal

```text
Mendeley legítimo real
        +
V2I 802.11n Beacon Profile
        +
Coletas próprias
```

## Robustez

```text
Long-term
        +
Station
```

## Ataques

```text
Mendeley Rogue sintético
        +
Evil Twin próprio/controlado
```

O Mendeley Rogue sintético é avaliação auxiliar. O teste controlado próprio deverá ser a principal evidência sobre ataques Evil Twin reais no trabalho.

## Perfis experimentais

### PROFILE_CORE

Features candidatas:

```text
rssi_dbm
channel
frequency_mhz
```

Objetivo: permitir experimentos entre fontes com pequena interseção de características.

### PROFILE_BEACON

```text
rssi_dbm
beacon_interval_ms
channel
frequency_mhz
```

Principalmente:

```text
Mendeley
+
V2I 802.11n
```

### PROFILE_SECURITY

```text
rssi_dbm
channel
advertised_channel
beacon_interval_ms
security_type
is_hidden
```

Principalmente:

```text
Mendeley
+
coletas próprias
```

### PROFILE_DESKTOP

Perfil candidato para a aplicação final:

```text
rssi_dbm
channel
frequency_mhz
security_type
beacon_interval_ms

rssi_mean
rssi_std
rssi_delta

ssid_bssid_count
bssid_changed
channel_changed
security_changed
```

Este perfil ainda será validado quando o scanner Windows estiver implementado.

## Experimentos planejados

| ID | Treino | Teste | Objetivo |
|---|---|---|---|
| E1 | dados próprios | sessões próprias não vistas | baseline |
| E2 | próprios + Mendeley | sessões próprias não vistas | ganho ao adicionar base pública |
| E3 | próprios + Mendeley + V2I | ambiente normal não visto | generalização |
| E4 | normal diversificado | Long-term + Station | falsos positivos |
| E5 | normal diversificado | Rogue sintético | anomalias sintéticas |
| E6 | features desktop | Evil Twin controlado próprio | avaliação final do protótipo |

## Status

**Fase 2 concluída.**

O próximo trabalho passa para a **Fase 3 — Análise Exploratória de Dados (EDA)**.


## Correção da Fase 3 — Passo 2

A comparação semântica mostrou que `BeaconInterval` do Mendeley e
`meanInterBeaconTime` do V2I **não devem ser considerados a mesma feature**.

- Mendeley: intervalo configurado pelo AP, em TU.
- V2I: intervalo médio observado entre Beacons.

Para experimentos multi-source, será criada:

```text
observed_inter_beacon_ms
```

No Mendeley ela será derivada dos timestamps de Beacons por sessão/BSSID.

O valor configurado será preservado separadamente como:

```text
configured_beacon_interval_ms
```

Além disso, RSSI bruto não será concatenado diretamente entre fontes.
Serão usadas estatísticas harmonizadas por janela/AP.
