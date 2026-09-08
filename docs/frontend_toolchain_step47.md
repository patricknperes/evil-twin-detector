# Fase 4 — Passo 47: validação real da toolchain frontend

Comando recomendado:

```powershell
.\scripts\validate_frontend_toolchain.ps1
```

O gate exige, nesta ordem:

```text
Node + npm
→ dependências reais em node_modules
→ Vitest
→ TypeScript build-mode typecheck
→ Vite production build
→ frontend/dist/index.html
```

O `typecheck` usa `tsc -b --force --pretty false`, porque o `tsconfig.json`
raiz é um projeto de referências e `tsc --noEmit` isolado no arquivo raiz não
verifica os projetos referenciados.

`tsconfig.node.json` usa `noEmit: true`, impedindo que o typecheck deixe um
`vite.config.js` transitório no repositório.

## Ambiente atual

A tentativa de acessar `registry.npmjs.org` retornou erro de resolução DNS
`EAI_AGAIN`. Portanto, a validação dependency-resolved de Vitest/Vite não pode
ser declarada como executada neste ambiente.

Como verificação auxiliar, o compilador TypeScript real foi executado com
stubs temporários de dependências que não entram no projeto. Isso encontrou e
permitiu corrigir inconsistências locais de tipos/contratos, mas não substitui
`npm install` + os tipos reais das bibliotecas.
