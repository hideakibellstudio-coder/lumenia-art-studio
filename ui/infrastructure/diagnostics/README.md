# `ui/infrastructure/diagnostics/` — relatórios de queda (técnico)

**Responsabilidade:** o trabalho de arquivo e de rede dos relatórios de queda: montar, listar, mover e podar os pacotes `.zip` em `logs/crash-reports/`, e enviá-los ao Sentry (ou Sentry auto-hospedado / GlitchTip) por HTTP da biblioteca padrão. Não decide quando um relatório nasce nem se ele sai da máquina: isso é do `DiagnosticsService` (`ui/core/diagnostics/`), com o consentimento do usuário.

## Porta de entrada

`from ui.infrastructure.diagnostics import report_bundle, SentryEndpoint, upload_minidump, upload_event`

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Porta do pacote. |
| `report_bundle.py` | Pastas (`reports_dir`, `dumps_dir`), `write_bundle` (zip com `manifest.json`, textos e o minidump), `pending_bundles`, `mark_sent`, `discard`, `prune`, `tail` do log. |
| `sentry_uploader.py` | `SentryEndpoint.parse(dsn)`, `upload_minidump` (endpoint de minidump, simbolizado com o PDB do build) e `upload_event` (envelope com a mensagem e o final do log). Sem SDK. |

## Regras

- Os relatórios ficam em `logs/` (fora do repositório em desenvolvimento, pasta de dados do usuário quando instalado).
- Sem DSN configurado nada é enviado: o usuário recebe o `.zip` para anexar num e-mail.
- Nada aqui importa `ui/core`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
