# `.github/workflows/` — workflows do GitHub Actions

**Responsabilidade:** compilar o motor a partir de um clone limpo no Windows e rodar a suíte em cada versão de Python suportada.

## Porta de entrada

`ci.yml` (em todo push e pull request).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `ci.yml` | Windows × Python 3.11–3.14 com o motor escalar, mais um job AVX2: instala o lock, compila o motor, mede a linha de base e roda a suíte com cobertura mínima de 80%. |

## Regras

- Passo novo de build ou teste entra aqui e no guia de build (`docs/03-guias/02-build-e-release.md`).
