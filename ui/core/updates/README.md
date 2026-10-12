# `ui/core/updates/` — regras das atualizações

**Responsabilidade:** decidir quando procurar uma atualização (canal, verificação automática a cada 20 h) e como a versão encontrada é apresentada. Não baixa nem instala nada: isso é do `ui/infrastructure/updater/` (Velopack).

## Porta de entrada

`from ui.core.updates import UpdatePreferences, UpdateOffer`

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Porta do pacote. |
| `update_policy.py` | `UpdateChannel`, `UpdatePreferences` (seção `updates` do `config.json`), `UpdateOffer` (versão e notas; `readable_notes` tira comentários HTML, como o `<!-- released: AAAA-MM-DD -->` que as notas das versões feitas com licenciamento carregam). |

## Regras

- Toda versão encontrada é oferecida: o programa não tem licença nem período de atualizações (removidos em 2026-10-12; o código está na tag `archive/licensing-v1`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
<!-- /arccc:deps -->
