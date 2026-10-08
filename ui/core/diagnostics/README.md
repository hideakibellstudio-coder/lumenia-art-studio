# `ui/core/diagnostics/` — relatório de queda (regras)

**Responsabilidade:** o que é um relatório de queda (`CrashReport`), quando ele pode sair da máquina (`ReportConsent`) e o que é tirado do texto antes (`scrub`: pasta do usuário, nome de usuário, e-mails). O `DiagnosticsService` conduz o relatório do nascimento à resposta do usuário; o trabalho de arquivo e de rede é do `ui/infrastructure/diagnostics/`. Não tem relação com o painel de telemetria (F12), que mede o traço e nunca sai da máquina.

## Porta de entrada

`from ui.core.diagnostics import DiagnosticsService, AppFacts, CrashReport, ReportConsent, SendResult`

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Porta do pacote. |
| `crash_report.py` | `CrashKind` (queda nativa, exceção Python, relatório pedido) e `CrashReport` (o `manifest.json` do pacote). |
| `diagnostics_service.py` | `DiagnosticsService`: instala o minidump no motor, junta o que a sessão anterior deixou ao cair (`collect_previous_session`), transforma a primeira exceção Python não tratada em relatório (`PythonErrorHandler`), cria o relatório pedido pelo usuário, lista, envia (`SendResult`) e descarta. |
| `report_privacy.py` | `ReportConsent` (perguntar, sempre, nunca; padrão: perguntar) e `scrub`. |

## Regras

- Relatório sai da máquina só com consentimento (LGPD): o padrão é perguntar a cada relatório.
- A pintura nunca entra num relatório; o minidump guarda pilhas e a memória que elas apontam, não os tiles.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/engine`
- `ui/infrastructure/diagnostics`
<!-- /arccc:deps -->
