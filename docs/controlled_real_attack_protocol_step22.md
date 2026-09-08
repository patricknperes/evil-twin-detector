# Protocolo defensivo para experimento Wi-Fi controlado

O projeto contém somente a parte de **observação e avaliação**.

A ferramenta não fornece funções para criar, clonar, configurar ou controlar
um ponto de acesso malicioso.

Quando um experimento autorizado já estiver ativo em laboratório:

```text
observer Windows
→ raw attack session
→ SHA-256
→ interim attack observations
→ frozen normal reference
→ desktop_candidate_v1 attack features
→ fixed scaler/model/threshold
→ metrics
```

A autorização é registrada no manifest para evitar misturar capturas casuais
com o conjunto de ataque controlado.

O conjunto de ataque é evaluation-only.
