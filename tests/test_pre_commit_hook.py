"""A conferência antes do commit (`.githooks/pre-commit` → `scripts/pre_commit.py`).

Com o CI só à mão (2026-09-25), é ela que impede commit quebrado no Windows.
Aqui se confere que o gancho chama o script, que cada teste da lista rápida
existe e que o gancho é executável no git (o Git for Windows usa o bit do
índice, não o do sistema de arquivos).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import pre_commit

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".githooks" / "pre-commit"


def test_hook_calls_the_script():
    text = HOOK.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/sh\n")
    assert "scripts/pre_commit.py" in text


def test_every_fast_test_exists():
    missing = [name for name in pre_commit.FAST_TESTS if not (ROOT / name).is_file()]
    assert missing == []


def test_native_changes_are_detected():
    assert pre_commit.touches_native(["engine/core/raster/FloodFill.cpp"])
    assert pre_commit.touches_native(["setup.py"])
    assert not pre_commit.touches_native(["ui/core/tool_settings.py", "docs/README.md"])


def test_hook_is_executable_in_the_index():
    try:
        out = subprocess.run(["git", "ls-files", "-s", ".githooks/pre-commit"], cwd=ROOT, capture_output=True,
                             text=True, encoding="utf-8", check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git indisponível")
    if not out:
        pytest.skip("gancho ainda não versionado nesta cópia")
    assert out.split()[0] == "100755"
