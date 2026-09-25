# `ui/` — pilar de interface (Python/PySide6)

**Responsabilidade:** raiz do pilar de interface: tudo que a pessoa vê e toca, sem nenhum código de pintura de pixels (isso é do motor C++ em `engine/`, alcançado só por `ui/infrastructure/bridge_client`).

## Porta de entrada

`main.py`, na raiz do repositório, chama `ui.boundary.orchestrator.app_runner.launch`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote; vazio. |

## Regras

- Subpastas (ARCcC multi-pilar, seção 15.3): `boundary/` (casca: janela
  principal e boot), `core/` (núcleo compartilhado por casca e plugins: estado,
  documento, contrato do motor, telas, widgets) e `infrastructure/` (serviços
  técnicos: cliente da ponte com o motor, configuração, idioma, tema, ícones,
  logging, caminhos). Não há `utils/`: nada aqui é genérico o bastante.
- `ui/` nunca importa `plugins/` (catraca `reverse_import` em
  `tests/arccc_coupling_metrics.py`). Plugins importam o núcleo, nunca o contrário.
- Até 2026-09-24 havia ainda `ui/engine_backends/` fora das quatro pastas e os
  atalhos `ui/main.py` e `ui/requirements.txt` (sem nenhum uso).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
