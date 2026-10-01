"""The bridge contract has a version, and a binary that does not match is refused loudly (S0.2, D17).

Until 2026-10-01 the interface imported `aladyn_engine_native` inside a
`try/except Exception` that logged at INFO and carried on in "shell mode": a
missing binary, one from another version, or one missing a DLL all ended in an
empty canvas with no explanation. The module exposed no version, so a stale
binary (AGENTS.md records one found in 2026-09-22) passed in silence and failed
later, one call at a time.

Now the module exposes `CONTRACT_VERSION`; the backend compares it with
`EXPECTED_CONTRACT_VERSION` when it loads; any failure is kept as `load_error`
and the app tells the user at startup. A fifth guard keeps the version honest:
the `.pyi` is pinned, so changing the contract without bumping the version fails.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import types

import pytest

from ui.infrastructure.bridge_client.contract_version import EXPECTED_CONTRACT_VERSION

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "bridge" / "boundary" / "contracts"
PIN = pathlib.Path(__file__).parent / "golden" / "bridge_contract.json"


def _pyi_digest() -> str:
    sha = hashlib.sha256()
    for name in sorted(path.name for path in CONTRACTS.glob("*.pyi")):
        sha.update(name.encode("utf-8"))
        sha.update((CONTRACTS / name).read_bytes().replace(b"\r\n", b"\n"))
    return sha.hexdigest()


def _backend_with(monkeypatch, module):
    """An AladynBackend built while `import aladyn_engine_native` yields `module`."""
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    monkeypatch.setitem(sys.modules, "aladyn_engine_native", module)
    return AladynBackend()


# -- the handshake -----------------------------------------------------------

def test_the_binary_and_the_interface_agree_on_the_version():
    native = pytest.importorskip("aladyn_engine_native", reason="native module not built here")
    assert native.CONTRACT_VERSION == EXPECTED_CONTRACT_VERSION, (
        "the compiled engine is from another contract version: rebuild it "
        "(python scripts/build_native.py)"
    )


def test_a_binary_of_another_version_is_refused_with_both_versions_in_the_message(monkeypatch):
    stale = types.ModuleType("aladyn_engine_native")
    stale.CONTRACT_VERSION = EXPECTED_CONTRACT_VERSION + 1
    backend = _backend_with(monkeypatch, stale)
    assert not backend.available
    assert str(EXPECTED_CONTRACT_VERSION) in backend.load_error
    assert str(EXPECTED_CONTRACT_VERSION + 1) in backend.load_error


def test_a_binary_without_a_version_is_refused_as_too_old(monkeypatch):
    backend = _backend_with(monkeypatch, types.ModuleType("aladyn_engine_native"))
    assert not backend.available
    assert "build_native" in backend.load_error


def test_a_binary_that_cannot_be_imported_keeps_the_cause(monkeypatch):
    backend = _backend_with(monkeypatch, None)  # `import` raises ImportError
    assert not backend.available
    assert backend.load_error, "the import error vanished"


def test_a_good_binary_has_no_load_error():
    pytest.importorskip("aladyn_engine_native", reason="native module not built here")
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    backend = AladynBackend()
    assert backend.available and backend.load_error == ""


# -- the registry and the startup notice ------------------------------------------

def test_the_registry_keeps_why_no_engine_loaded(monkeypatch):
    from ui.core.engine.registry import EngineRegistry

    stale = types.ModuleType("aladyn_engine_native")
    stale.CONTRACT_VERSION = EXPECTED_CONTRACT_VERSION + 7
    backend = _backend_with(monkeypatch, stale)
    registry = EngineRegistry.instance()
    previous = registry.get_backend()
    try:
        assert registry.setup([backend]) is None
        assert str(EXPECTED_CONTRACT_VERSION + 7) in registry.load_error
    finally:
        registry.set_backend(previous)


def test_the_user_is_told_at_startup_when_there_is_no_engine(qapp, monkeypatch):
    from PySide6 import QtWidgets

    from ui.boundary.orchestrator.engine_failure import report_engine_failure
    from ui.core.engine.registry import EngineRegistry

    stale = types.ModuleType("aladyn_engine_native")
    stale.CONTRACT_VERSION = EXPECTED_CONTRACT_VERSION + 7
    registry = EngineRegistry.instance()
    previous = registry.get_backend()
    shown = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", lambda *args: shown.append(args[2]))
    try:
        registry.setup([_backend_with(monkeypatch, stale)])
        assert report_engine_failure(None) is True
    finally:
        registry.set_backend(previous)
    assert shown and str(EXPECTED_CONTRACT_VERSION + 7) in shown[0]


def test_nothing_is_shown_when_the_engine_is_there(qapp, monkeypatch):
    pytest.importorskip("aladyn_engine_native", reason="native module not built here")
    from PySide6 import QtWidgets

    from ui.boundary.orchestrator.engine_failure import report_engine_failure
    from ui.core.engine.registry import EngineRegistry
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    registry = EngineRegistry.instance()
    previous = registry.get_backend()
    shown = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", lambda *args: shown.append(args))
    try:
        registry.set_backend(AladynBackend())
        assert report_engine_failure(None) is False
    finally:
        registry.set_backend(previous)
    assert shown == []


# -- the version stays honest -----------------------------------------------------

def test_the_contract_is_pinned_to_its_version():
    """Changing the `.pyi` without bumping the version leaves a stale binary looking compatible."""
    pin = json.loads(PIN.read_text(encoding="utf-8"))
    assert pin["contract_version"] == EXPECTED_CONTRACT_VERSION, (
        "tests/golden/bridge_contract.json and EXPECTED_CONTRACT_VERSION disagree"
    )
    assert pin["pyi_sha256"] == _pyi_digest(), (
        "the bridge contract (.pyi) changed. Bump the version in "
        "bridge/infrastructure/ContractVersion.hpp and "
        "ui/infrastructure/bridge_client/contract_version.py, rebuild the engine, and set "
        "both fields of tests/golden/bridge_contract.json (pyi_sha256: "
        f"{_pyi_digest()})."
    )
