# `ui/infrastructure/licensing/` — licença em disco

**Responsabilidade:** guardar e ler o token da licença (`license.lic` na pasta de dados do usuário), com gravação atômica. Não sabe o que o token significa: quem julga é o motor (`engine/infrastructure/licensing/`) e quem conduz a sessão é o `LicenseService` (`ui/core/licensing/`).

## Porta de entrada

`from ui.infrastructure.licensing import LicenseStore`

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Porta do pacote. |
| `license_store.py` | `LicenseStore`: `read`, `write` (arquivo temporário + `os.replace`), `clear`. |

## Regras

- Nada aqui importa `ui/core` (infraestrutura não conhece o domínio).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
