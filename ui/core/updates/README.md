# `ui/core/updates/` — regras das atualizações

**Responsabilidade:** decidir quando procurar uma atualização (canal, verificação automática a cada 20 h) e se a versão encontrada pode ser oferecida, conforme a licença. Não baixa nem instala nada: isso é do `ui/infrastructure/updater/` (Velopack).

## Porta de entrada

`from ui.core.updates import UpdatePreferences, UpdateOffer, UpdateDecision, decide`

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Porta do pacote. |
| `update_policy.py` | `UpdateChannel`, `UpdatePreferences` (seção `updates` do `config.json`), `UpdateOffer` (versão e notas; a data de lançamento vem do comentário `<!-- released: AAAA-MM-DD -->` que o `scripts/build_release.py` escreve) e `decide`. |

## Regras

- Uma versão que a licença não cobre (`updates_until` anterior à data de lançamento) **nunca** é instalada: instalar transformaria quem pagou em usuário do modo gratuito. A interface só avisa.
- Sem data de lançamento nas notas e com licença com prazo: `UNKNOWN_COVERAGE`, a interface pergunta em vez de instalar.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/licensing`
<!-- /arccc:deps -->
