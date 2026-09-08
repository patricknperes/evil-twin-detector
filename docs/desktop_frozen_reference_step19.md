# Referência normal congelada — desktop_candidate_v1

Fluxo metodológico:

```text
sessões importadas
→ split por session_id
→ reference sessions
→ referência congelada
→ model_train / validation / test consultam a referência
→ features desktop
```

A unidade de split nunca é uma linha individual.

## Por que separar reference de model_train?

O `desktop_candidate_v1` é contextual: suas features dependem de saber o que era
normal para uma rede conhecida.

Se o próprio `model_train`, `validation` ou `test` atualizassem o histórico,
eventos que deveriam ser inéditos poderiam ser absorvidos pela referência.

Por isso `reference` é um conjunto separado e congelado.

## Contexto desconhecido

Uma SSID/BSSID que não pode ser ligada ao histórico normal produz:

```text
context_available = false
feature_complete = false
```

e não:

```text
attack = true
```

Na futura aplicação esse estado deverá ser apresentado como algo equivalente a
"histórico insuficiente", não como confirmação de ameaça.
