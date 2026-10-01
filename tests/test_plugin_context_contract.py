"""What a plugin receives from the shell is small and does not include the engine (R9).

`PluginContext` carried `backend` (the whole `EngineBackend`, for every plugin, third-party ones
included: the package installer accepts them) and `get_logger`. Measured on 2026-10-01, no plugin read
either: the 21 uses of the context under ui/plugins/ are `service_registry` (20) and `main_window` (1,
the workspace core placing its central widget). They were removed, and this test pins the surface so
that a plugin gets the engine only through a service the shell installs for the contract it needs.
"""
import ast
from pathlib import Path

from ui.core.plugins.context import PluginContext

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"attach_main_window", "main_window", "service_registry"}


def test_the_context_offers_only_what_plugins_use():
    public = {name for name in dir(PluginContext) if not name.startswith("_")}
    assert public == ALLOWED, (
        "PluginContext changed its public surface. A plugin that needs the engine takes a service "
        "installed in the ServiceRegistry, not a handle on the whole EngineBackend; if you must widen "
        "the context, say who uses the new member and update this test."
    )


def test_no_plugin_reaches_the_engine_or_the_loggers_through_the_context():
    used = set()
    for path in (ROOT / "ui" / "plugins").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute) and node.value.attr == "context":
                used.add(node.attr)
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in {"context", "ctx"}:
                used.add(node.attr)
    assert used <= ALLOWED, f"plugins read context members outside the contract: {sorted(used - ALLOWED)}"
