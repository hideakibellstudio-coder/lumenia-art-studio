# `.github/` — configuração do GitHub

**Responsabilidade:** a integração contínua do repositório.

## Porta de entrada

`workflows/ci.yml`.

## Conteúdo

| Pasta | Responsabilidade |
|---|---|
| `workflows/` | Workflows do GitHub Actions. |

## Regras

- O CI é a fonte da verdade de "verde": commit que quebra o CI é corrigido antes de qualquer outra coisa.
