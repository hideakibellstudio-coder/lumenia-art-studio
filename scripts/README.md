# `scripts/` — automação de build, diagnóstico e release

**Responsabilidade:** os scripts oficiais que um desenvolvedor roda à mão: compilar o motor, gerar a distribuição e o instalador, e as baterias de sessão longa.

## Porta de entrada

Cada script roda sozinho (`python scripts/<nome>.py`); os de build estão em AGENTS.md, seção 6.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `build_native.py` | Compila a extensão `aladyn_engine_native` (objetos em `../build/temp_native`). |
| `check_windows_build.py` | Compila os `.cpp` do `setup.py` para o alvo Windows a partir do Linux (MinGW-w64, escalar e AVX2) com `-Wall -Wextra -Werror`: aviso novo reprova; o agente em Linux roda antes de commitar mudança em C++ (AGENTS.md, seção 5.1). |
| `build_portable.py` | Gera e verifica a distribuição portátil com Nuitka (`../build/portable`, `../dist`), com os avisos de terceiros (`assets/legal/`) e os textos de licença dos pacotes embutidos em `licenses/`. |
| `lumenia_installer.iss` | Script do Inno Setup do instalador oficial. |
| `generate_compile_commands.py` | Gera `compile_commands.json` capturando as chamadas reais do MSVC (para o ARCcC-Navigator). |
| `boot_smoke.py` | Fumaça do boot da casca, sem janela real. |
| `pre_commit.py` | Conferência rápida antes do commit (chamada por `.githooks/pre-commit`): catracas e testes de governança em segundos e, se o commit toca o motor, a compilação para Windows. |
| `run_soak_test.py` | Bateria rápida só do pincel nativo, sem widgets. |
| `soak_full_session.py` | Gate de sessão longa: MainWindow real com traço, camadas, salvar e MDI. |
| `monitor_session.ps1` | Amostra memória e handles do Lumenia durante uma sessão real de pintura. |
| `generate_github_dashboard.py` | Gera `github_project_dashboard.html` (ignorado pelo git) a partir de `dashboard_template.html` e do log do git. |

## Regras

- Script pontual de investigação não fica no repositório (AGENTS.md, seção 1): vira teste ou sai.

