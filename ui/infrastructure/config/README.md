# `ui/infrastructure/config/` — configurações do usuário

**Responsabilidade:** preferências persistidas num JSON único e versionado, com migração de versões antigas e escrita segura (cópia anterior validada).

## Porta de entrada

`from ui.infrastructure.config import ConfigManager` (`ConfigManager.instance()`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `ConfigManager`, `DEFAULT_CONFIG`, `get_default_config_path`. |
| `manager.py` | ConfigManager — Sistema Central de Configurações e Preferências (Lumenia V2 / ARCcC). |
| `schema.py` | Versioned configuration migration; canonical values survive UI translation. |
| `storage.py` | Durable JSON replacement with a validated previous generation. |

## Regras

Os testes apontam o arquivo para um perfil temporário (`LUMENIA_CONFIG_PATH`, em `tests/conftest.py`); nunca rode a janela de desenvolvimento gravando no perfil real sem querer.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
