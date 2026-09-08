# Windows Native Wi-Fi — matriz de capacidade para o TCC

## Escopo

Este documento fecha a **Fase 4 — Passo 15**: mapear o `contextual_core_v2`
para sinais que a aplicação Windows consegue obter sem captura de pacotes.

Fontes primárias consultadas:

- Microsoft Learn — `WLAN_BSS_ENTRY`:
  https://learn.microsoft.com/windows/win32/api/wlanapi/ns-wlanapi-wlan_bss_entry
- Microsoft Learn — `WlanGetNetworkBssList`:
  https://learn.microsoft.com/windows/win32/api/wlanapi/nf-wlanapi-wlangetnetworkbsslist
- Microsoft Learn — `WLAN_AVAILABLE_NETWORK`:
  https://learn.microsoft.com/windows/win32/api/wlanapi/ns-wlanapi-wlan_available_network
- Microsoft Learn — alterações de acesso/localização para Wi-Fi:
  https://learn.microsoft.com/windows/win32/nativewifi/wi-fi-access-location-changes

## O que `WLAN_BSS_ENTRY` entrega

Por BSS/AP observado, a API expõe diretamente:

```text
SSID                   dot11Ssid
BSSID                  dot11Bssid
RSSI                   lRssi
qualidade               uLinkQuality
Beacon Interval         usBeaconPeriod
TSF/Timestamp           ullTimestamp
host receive timestamp  ullHostTimestamp
capability bits         usCapabilityInformation
frequência recebida     ulChCenterFrequency
IE blob                 ulIeOffset + ulIeSize
```

O `IE blob` é especialmente importante: ele contém os Information Elements do
último Beacon ou Probe Response que o driver manteve para o BSS. Portanto é
possível fazer parsing de RSN/WPA sem usar WinPcap/Npcap/monitor mode.

A própria documentação da Microsoft alerta que o blob é informação recebida do
AP e deve ser tratado como **não confiável**. O parser implementado neste passo
usa limites estritos e interrompe o parsing em IE truncado.

## Mapeamento do `contextual_core_v2`

| Feature do Core V2 | Desktop | Origem | Decisão |
|---|---|---|---|
| `ssid_bssid_count` | Sim | SSID + BSSID + histórico local | entra no candidato |
| `bssid_changed` | Sim | SSID + BSSID + histórico local | entra no candidato |
| `security_changed` | Sim, com parser | RSN/WPA IEs + capability privacy | entra no candidato |
| `security_strength_delta` | Sim, com parser | classificação de segurança por BSS | entra no candidato |
| `is_hidden` | Não equivalente diretamente | SSID vazio/não anunciado é observável, mas semântica não foi alinhada | fica fora do modelo v1 |

### Por que `is_hidden` não entra

O Windows permite observar um SSID de comprimento zero. Porém, no trabalho já
foi observado que **SSID ausente e `IsHidden` não são semanticamente
intercambiáveis** no Mendeley.

Por isso criamos apenas:

```text
ssid_not_broadcast
```

como metadado. Não renomeamos isso para `is_hidden` e não reaproveitamos o
modelo Core V2 como se fossem a mesma feature.

## Segurança por BSS

`WLAN_AVAILABLE_NETWORK` oferece segurança/default auth/cipher no nível da rede
visível, mas uma rede pode agrupar múltiplos BSSIDs. Para o caso Evil Twin, o
interesse é a observação **por BSSID**.

Por isso `desktop_candidate_v1` usa o IE blob de `WLAN_BSS_ENTRY`:

```text
RSN IE (48)               -> WPA2 ou WPA3-SAE
WPA vendor IE             -> WPA
Privacy bit sem RSN/WPA   -> LEGACY_PRIVACY
sem Privacy/RSN/WPA       -> OPEN
```

Ranking experimental:

```text
OPEN             0
LEGACY_PRIVACY   1
WPA              2
WPA2_OR_NEWER    3
WPA3_SAE         4
```

Esse ranking é propositalmente conservador. Ele não tenta implementar toda a
matriz de AKMs/ciphers do 802.11.

## `desktop_candidate_v1`

O contrato primário fica:

```text
ssid_bssid_count
bssid_changed
security_changed
security_strength_delta
```

Status:

```text
FEATURE CONTRACT READY
MODEL RETRAINING REQUIRED
```

O OCSVM treinado em `contextual_core_v2` **não pode ser copiado diretamente para
o desktop**, porque:

1. o Core V2 possui 5 features e o Desktop V1 possui 4;
2. a classificação de segurança agora nasce do parser Windows por BSS;
3. `is_hidden` foi removida por incompatibilidade semântica;
4. scaler e threshold precisam ser recalibrados com observações do scanner real.

## Outros sinais que o Windows já oferece

| Sinal | Disponibilidade | Uso atual |
|---|---|---|
| RSSI | direta (`lRssi`) | futuro Track D |
| Beacon Interval | direta (`usBeaconPeriod`) | candidata futura |
| TSF | direta (`ullTimestamp`) | tecnicamente possível, mas continua `ABLATION ONLY` |
| frequência recebida | direta (`ulChCenterFrequency`) | diagnóstico/canal observado |
| local-admin bit | derivado de BSSID | continua `ABLATION ONLY` |
| advertised channel | parcialmente via IEs | precisa parser band-aware e validação real |
| sequence number | não exposto diretamente em `WLAN_BSS_ENTRY` | fora |
| client count | não exposto | fora |
| frame length | não exposto diretamente | fora |

A disponibilidade direta de TSF muda apenas a conclusão de **observabilidade**:
o Windows consegue fornecer `ullTimestamp`. Ela não muda a conclusão científica
do Passo 11 — reboot legítimo também pode causar reset e a feature continua
separada do modelo principal.

## Permissão de localização no Windows

Em versões atuais do Windows, APIs Wi-Fi que expõem BSSID estão sujeitas ao
consentimento de localização precisa. Sem consentimento, chamadas como:

```text
WlanScan
WlanGetNetworkBssList
WlanGetAvailableNetworkList
```

podem retornar `ERROR_ACCESS_DENIED`.

A aplicação precisa ter um estado de UX explícito para:

```text
Wi-Fi permission unavailable / precise location access denied
```

e não transformar isso em "nenhuma rede encontrada".

O fluxo da futura aplicação deverá pedir acesso em resposta a uma ação clara do
usuário e oferecer acesso a:

```text
ms-settings:privacy-location
```

quando necessário.

## Próxima etapa

A próxima etapa deve ser feita **em um Windows real**:

```text
ctypes/wlanapi.dll
→ WlanOpenHandle
→ WlanEnumInterfaces
→ WlanScan
→ WlanGetNetworkBssList
→ converter WLAN_BSS_ENTRY para NativeWifiBssObservation
→ validar IEs e security parser em redes reais
→ coletar sessões normais próprias
→ retrain/calibrate desktop_candidate_v1
```
