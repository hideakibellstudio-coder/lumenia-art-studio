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
