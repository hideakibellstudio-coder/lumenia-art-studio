"""A versão do produto tem uma fonte só: `ui/infrastructure/app_info.py`.

Até 2026-09-25 o app mostrava três versões inventadas ("Lumenia Brush Engine
2.0" no título, "v2.0" na splash, "2.5.0 (Build 2026.08)" no "Sobre") enquanto
instalador e EULA diziam 0.2.0. As cópias que ferramentas externas exigem
(pip, setuptools, README, EULA) são conferidas aqui.
"""
from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

from ui.infrastructure.app_info import APP_STAGE, APP_VERSION

ROOT = Path(__file__).resolve().parents[1]
# "Lumenia 2.0", "Engine 2.0", "v2.0", "Build 2026.08": versão escrita à mão.
HANDWRITTEN_VERSION = re.compile(r"(?:Lumenia|Engine|Build|\bv)\s?\d+\.\d+")


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def _setup_version() -> str:
    for node in ast.walk(ast.parse(_read("setup.py"))):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "setup":
            return next(k.value.value for k in node.keywords if k.arg == "version")
    raise AssertionError("setup.py sem setup(version=...)")


def test_version_is_semantic():
    assert re.fullmatch(r"\d+\.\d+\.\d+", APP_VERSION)


def test_packaging_copies_match_app_info():
    with (ROOT / "pyproject.toml").open("rb") as stream:
        assert tomllib.load(stream)["project"]["version"] == APP_VERSION
    assert _setup_version() == APP_VERSION
    # Since 2026-10-08 the installer is Velopack's: scripts/build_release.py packs with the
    # pyproject version, so there is no other copy to keep in step (the Inno Setup script left).


def test_readme_and_eula_show_the_same_version():
    badge = re.search(r"Versão-v([\d.]+)%20(\w+)", _read("README.md"))
    assert badge and badge.groups() == (APP_VERSION, APP_STAGE)
    eula = re.search(r"Version:\s*(\w+)\s+([\d.]+)", _read("TERMS_AND_LICENSE.txt"))
    assert eula and eula.groups() == (APP_STAGE, APP_VERSION)


def test_interface_has_no_handwritten_version():
    offenders = []
    for path in sorted((ROOT / "ui").rglob("*.py")):
        if path.name == "app_info.py":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if HANDWRITTEN_VERSION.search(line):
                offenders.append(f"{path.relative_to(ROOT).as_posix()}:{number}: {line.strip()}")
    assert offenders == [], "use ui.infrastructure.app_info:\n" + "\n".join(offenders)


def test_about_dialog_shows_the_product_version(qapp):
    from ui.core.screens.about_dialog import AboutDialog

    dialog = AboutDialog()
    try:
        assert dialog.lbl_ver.text().endswith(f"{APP_VERSION} {APP_STAGE}")
    finally:
        dialog.deleteLater()
