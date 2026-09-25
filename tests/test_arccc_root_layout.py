"""Raiz reservada aos pilares (ARCcC 15.4, regra 1), com a exceção declarada.

A raiz tem os três pilares, os arquivos de build/entrada do monorepo e, por
decisão do dono do projeto em 2026-09-25, as pastas que atravessam os pilares
(`tests/`, `docs/`, `assets/`, `scripts/`, `benchmarks/`). Até essa data os
plugins moravam em `plugins/`, na raiz; hoje estão em `ui/plugins/`.
Entrada nova aqui é decisão de arquitetura: entra nesta lista e no AGENTS.md.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

PILLARS = {"ui", "bridge", "engine"}
DECLARED_EXCEPTION = {"tests", "docs", "assets", "scripts", "benchmarks"}
BUILD_AND_ENTRY = {
    "main.py", "setup.py", "pyproject.toml", "requirements-dev.lock", "requirements-dev.txt",
    "Launch_Lumenia.bat", "Launch_Lumenia_Silent.vbs", "Send_Feedback.html", "TERMS_AND_LICENSE.txt",
    "README.md", "AGENTS.md", ".gitignore", ".gitattributes", ".github",
}


def _tracked_root_entries() -> set[str]:
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
                             encoding="utf-8", check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git indisponível: a raiz é conferida pelos arquivos versionados")
    return {line.split("/", 1)[0] for line in out.splitlines() if line}


def test_root_holds_only_pillars_build_files_and_the_declared_exception():
    unexpected = sorted(_tracked_root_entries() - PILLARS - DECLARED_EXCEPTION - BUILD_AND_ENTRY)
    assert unexpected == [], f"entrada nova na raiz (fora dos pilares e da exceção declarada): {unexpected}"


def test_plugins_live_inside_the_ui_pillar():
    assert not (ROOT / "plugins").exists() or not any((ROOT / "plugins").rglob("*.py"))
    assert (ROOT / "ui" / "plugins" / "builtin_registry.py").is_file()
