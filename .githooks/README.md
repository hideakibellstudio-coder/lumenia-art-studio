# `.githooks/` — ganchos do git versionados

**Responsabilidade:** a conferência que roda antes de cada commit. Com o CI só
à mão (decisão do dono do projeto, 2026-09-25), ela é a barreira que impede
commit quebrado no Windows.

## Porta de entrada

Ativar uma vez por clone (Windows, Linux ou macOS):

```
git config core.hooksPath .githooks
```

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `pre-commit` | Chama `scripts/pre_commit.py` com o Python do sistema (no Windows, pelo sh do Git for Windows). |

## Regras

- O gancho só chama o script; a lógica mora em `scripts/pre_commit.py`, que
  também pode ser rodado à mão.
- Pular numa emergência: `git commit --no-verify`. A suíte completa continua
  obrigatória antes de enviar (`python -m pytest`).
