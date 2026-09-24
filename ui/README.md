# `ui/` — pilar de interface (Python/PySide6)

**Responsabilidade:** raiz do pilar de interface: tudo que a pessoa vê e toca, sem nenhum código de pintura de pixels (isso é do motor C++ em `engine/`, alcançado só por `ui/engine_backends`).

## Porta de entrada

`ui.main` (atalho antigo) delega para `ui.boundary.orchestrator.app_runner.launch`. O ponto de entrada real do programa é `main.py`, na raiz do repositório.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote; vazio. |
| `main.py` | Atalho de compatibilidade: chama `app_runner` do orquestrador. |

## Regras

- Subpastas: `boundary/` (casca: janela principal e boot), `core/` (núcleo
  compartilhado por casca e plugins), `engine_backends/` (único lugar que fala
  com o motor nativo), `infrastructure/` (logging e a fachada antiga do motor),
  `utils/` (funções puras).
- `ui/` nunca importa `plugins/` (catraca `reverse_import` em
  `tests/arccc_coupling_metrics.py`). Plugins importam o núcleo, nunca o contrário.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/boundary/orchestrator`
<!-- /arccc:deps -->
