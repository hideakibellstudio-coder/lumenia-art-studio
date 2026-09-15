"""Shared helpers for registering plugin classes from imported modules."""

from __future__ import annotations

import importlib
import logging
from collections.abc import Iterable

from ui.core.plugins.base import BasePlugin


def register_module_plugins(
    discovered_plugins: dict[str, type[BasePlugin]],
    module: object,
    plugin_dir: str,
    source: str,
    log: logging.Logger,
) -> None:
    """Register concrete ``BasePlugin`` subclasses exposed by *module*."""
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr is not BasePlugin:
            attr._plugin_dir = plugin_dir
            discovered_plugins[attr_name] = attr
            log.info("Plugin descoberto: %s (em %s)", attr_name, source)


def discover_compiled_plugins(
    module_names: Iterable[str],
    discovered_plugins: dict[str, type[BasePlugin]],
    log: logging.Logger,
) -> None:
    """Load the explicit catalog used when plugin sources are frozen."""
    for module_name in module_names:
        try:
            register_module_plugins(
                discovered_plugins,
                importlib.import_module(module_name),
                "",
                module_name,
                log,
            )
        except Exception as error:
            log.error("Erro ao carregar plugin compilado '%s': %s", module_name, error)
