# `.github/workflows/` — workflows do GitHub Actions

**Responsabilidade:** compilar o motor a partir de um clone limpo no Windows e rodar a suíte em cada versão de Python suportada.

## Porta de entrada

`ci.yml`, só à mão: aba Actions → Lumenia CI → Run workflow (`workflow_dispatch`). Push e pull request não disparam nada.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `ci.yml` | Windows × Python 3.11–3.14 com o motor escalar, mais um job AVX2: instala o lock, compila o motor, mede a linha de base e roda a suíte com cobertura mínima de 80%. |

## Regras

- Passo novo de build ou teste entra aqui e no guia de build (`docs/03-guias/02-build-e-release.md`).
- Até 2026-09-25 rodava em todo push: cada commit gastava 5 jobs Windows (o
  dobro, com a branch de trabalho), a cota do Actions do repositório privado
  acabou e todo commit ficava com X vermelho (jobs falhando em 2 s, sem
  runner). Desde então, por decisão do dono do projeto, roda só à mão; quem
  confere cada commit é o agente (AGENTS.md, seção 5.1). Útil rodar à mão antes
  de um release, com minutos disponíveis.
