# Evil Twin Detector — Frontend

Stack: React + TypeScript + Vite + Electron + Tailwind CSS v4.

Material UI não é utilizado.

API padrão: `http://127.0.0.1:8765`.

Comandos para quando formos executar tudo de uma vez:

```bash
npm install
npm run typecheck
npm run test
npm run build
npm run electron:dev
```


## Passo 32

A tela `/scan` possui pré-verificação, erros específicos da Native Wi-Fi API, botão seguro para abrir as configurações de localização do Windows dentro do Electron, filtros de suspeita, busca e detalhes técnicos expansíveis. Nenhuma varredura real foi executada nesta etapa.
