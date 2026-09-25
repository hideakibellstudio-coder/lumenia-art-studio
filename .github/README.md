# `.github/` — configuração do GitHub

**Responsabilidade:** a integração contínua do repositório.

## Porta de entrada

`workflows/ci.yml`.

## Conteúdo

| Pasta | Responsabilidade |
|---|---|
| `workflows/` | Workflows do GitHub Actions. |

## Regras

- O CI roda só à mão (decisão do dono do projeto, 2026-09-25). Cada commit é
  conferido antes pelo agente: suíte completa e, se tocou C++, o build para o
  alvo Windows (AGENTS.md, seção 5.1). Quando o CI é disparado e fica
  vermelho por erro do código, a correção vem antes de qualquer outra coisa.
