# `.github/workflows/` — workflows do GitHub Actions

**Responsabilidade:** compilar o motor a partir de um clone limpo no Windows e rodar a suíte em cada versão de Python suportada.

## Porta de entrada

`ci.yml`: em push na `main`, em pull request e à mão (`workflow_dispatch`). Push novo cancela o run anterior do mesmo ref.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `ci.yml` | Windows × Python 3.11–3.14 com o motor escalar, mais um job AVX2: instala o lock, compila o motor, mede a linha de base e roda a suíte com cobertura mínima de 80%. |

## Regras

- Passo novo de build ou teste entra aqui e no guia de build (`docs/03-guias/02-build-e-release.md`).
- Até 2026-09-25 rodava em todo push: o mesmo commit na branch de trabalho e na
  `main` gastava o dobro de minutos, e a cota do Actions acabou (jobs
  falhando em 2 s, sem runner). Branch sem PR roda à mão pela aba Actions.
