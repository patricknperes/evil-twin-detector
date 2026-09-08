# Windows Native Wi-Fi scanner — referências de implementação

Este arquivo registra as decisões de API do Passo 16.

## Microsoft Native Wi-Fi

- `WlanOpenHandle`: abre a sessão e negocia a versão da API.
- `WlanEnumInterfaces`: retorna as interfaces WLAN habilitadas e aloca o buffer da lista.
- `WlanScan`: solicita uma varredura e retorna imediatamente.
- `WlanGetNetworkBssList`: retorna `WLAN_BSS_LIST` / `WLAN_BSS_ENTRY` e aloca o buffer.
- `WlanFreeMemory`: libera memória retornada pelas funções Native Wi-Fi.
- `WlanCloseHandle`: encerra a sessão.

## Observações de segurança

A documentação da Microsoft trata o conteúdo recebido do AP, especialmente os Information Elements, como não confiável. `ulIeOffset` e `ulIeSize` são validados contra os limites da lista antes da leitura.

`WLAN_BSS_ENTRY.ulIeSize` tem máximo documentado de 2.324 bytes.

## Scan

A documentação de `WlanScan` informa que a chamada retorna imediatamente. O fluxo recomendado é aguardar a notificação de scan completo ou aplicar timeout de quatro segundos antes de consultar a lista BSS. O Passo 16 usa timeout fixo de 4,2 segundos e registra a futura migração para `WlanRegisterNotification`.

## Importante

O scanner nativo não foi executado neste ambiente por não ser Windows. O código foi preparado para Windows 10/11 e precisa de validação na máquina de coleta antes de qualquer conclusão sobre comportamento de drivers reais.
