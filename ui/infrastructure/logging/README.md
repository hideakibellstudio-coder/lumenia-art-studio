# `ui/infrastructure/logging/` — logging

**Responsabilidade:** configuração do logging da aplicação (console colorido, arquivo, captura de exceções não tratadas e mensagens do Qt) e o decorador de medição de tempo.

## Porta de entrada

`from ui.infrastructure.logging import get_logger, setup_senior_logging, log_execution_time`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | ui.infrastructure.logging — Módulo Canônico de Logging e Telemetria (ARCcC). |
| `logger.py` | Senior Enterprise Logging Infrastructure (Lumenia V2) — ARCcC Infrastructure. |

## Regras

Log vai para o diretório de dados do usuário (`writable_data_dir`), nunca para dentro do repositório (política zero-dirt).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
<!-- /arccc:deps -->
