# `ui/core/licensing/` — licença, como a interface a lê

**Responsabilidade:** dar nome ao que o motor decide sobre a licença (`LicenseState`, `LicenseStatus`), responder se uma versão nova continua coberta por ela e conduzir a licença na sessão (`LicenseService`). Não verifica assinatura (isso é do motor, `engine/infrastructure/licensing/`) nem sabe onde o token fica em disco (`ui/infrastructure/licensing/`, injetado como `TokenStore`).

## Porta de entrada

`from ui.core.licensing import LicenseService, LicenseState, LicenseStatus`

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Porta do pacote. |
| `license_service.py` | `LicenseService`: `restore` na partida, `activate` grava só o que o motor aceitou, `deactivate`; sinal `statusChanged`. Recebe o motor (`RoleProvider[RuntimeServicesProtocol]`) e o `TokenStore` pelo construtor. |
| `license_status.py` | `LicenseState` (os nomes de `licenseStateName` do motor) e `LicenseStatus.from_engine`, `is_licensed`, `covers_release` (uma versão lançada depois de `updates_until` não aceita a licença). |

## Regras

- Os nomes dos estados são os do motor; estado desconhecido vira `UNSUPPORTED`, nunca `LICENSED`.
- Nenhuma regra de "o que o modo gratuito pode": a única restrição (marca d'água na exportação) é aplicada no motor.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/engine`
<!-- /arccc:deps -->
