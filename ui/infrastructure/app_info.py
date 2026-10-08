"""Identidade do produto: nome e versão, fonte única para a interface.

Até 2026-09-25 a janela dizia "Lumenia Brush Engine 2.0", a splash "v2.0" e o
"Sobre" "2.5.0 (Build 2026.08)", enquanto o instalador e a EULA diziam 0.2.0.
A versão também precisa estar em `pyproject.toml`, `setup.py`, no instalador
(`scripts/lumenia_installer.iss`), no `README.md` e na EULA
(`TERMS_AND_LICENSE.txt`); `tests/test_app_version.py` falha se alguma dessas
cópias divergir daqui.
"""

from __future__ import annotations

APP_NAME = "Lumenia"
APP_VERSION = "0.2.0"
APP_STAGE = "Alpha"
APP_DISPLAY_VERSION = f"{APP_VERSION} {APP_STAGE}"

# Distribution (2026-10-08). Updates come from the GitHub Releases of a PUBLIC repository
# that holds only the installers and packages (the code repository is private, and a
# private feed would need a token inside the program). Crash reports go to Sentry when a
# DSN is set here or in LUMENIA_CRASH_DSN; empty = the user e-mails the report.
APP_UPDATE_REPOSITORY = "https://github.com/hideakibellstudio-coder/lumenia-releases"
CRASH_REPORT_DSN = ""
SUPPORT_EMAIL = "lumeniateam@protonmail.com"
